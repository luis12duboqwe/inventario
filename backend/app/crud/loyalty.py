"""Operaciones CRUD para el módulo de Fidelización (Loyalty)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from .. import models, schemas
from ..core.transactions import flush_session, transactional_session
from ..utils.decimal_helpers import (
    quantize_currency,
    quantize_points,
    quantize_rate,
    to_decimal,
)
from .audit import log_audit_event as _log_action
from .sync import enqueue_sync_outbox


def _loyalty_account_payload(account: models.LoyaltyAccount) -> dict[str, Any]:
    return {
        "id": account.id,
        "customer_id": account.customer_id,
        "balance_points": float(to_decimal(account.balance_points)),
        "lifetime_points_earned": float(to_decimal(account.lifetime_points_earned)),
        "lifetime_points_redeemed": float(to_decimal(account.lifetime_points_redeemed)),
        "accrual_rate": float(to_decimal(account.accrual_rate)),
        "redemption_rate": float(to_decimal(account.redemption_rate)),
        "is_active": account.is_active,
        "expiration_days": account.expiration_days,
        "rule_config": account.rule_config,
    }


def _loyalty_transaction_payload(tx: models.LoyaltyTransaction) -> dict[str, Any]:
    return {
        "id": tx.id,
        "account_id": tx.account_id,
        "sale_id": tx.sale_id,
        "transaction_type": tx.transaction_type,
        "points": float(to_decimal(tx.points)),
        "balance_after": float(to_decimal(tx.balance_after)),
        "currency_amount": float(to_decimal(tx.currency_amount)),
        "description": tx.description,
        "registered_at": tx.registered_at.isoformat() if tx.registered_at else None,
        "expires_at": tx.expires_at.isoformat() if tx.expires_at else None,
        "details": tx.details,
    }


def get_loyalty_account(
    db: Session,
    customer_id: int,
    *,
    with_transactions: bool = False,
) -> models.LoyaltyAccount | None:
    statement = select(models.LoyaltyAccount).where(
        models.LoyaltyAccount.customer_id == customer_id
    )
    if with_transactions:
        statement = statement.options(
            selectinload(models.LoyaltyAccount.transactions)
        )
    return db.scalars(statement).first()


def get_loyalty_account_by_id(
    db: Session,
    account_id: int,
    *,
    with_transactions: bool = False,
) -> models.LoyaltyAccount | None:
    statement = select(models.LoyaltyAccount).where(
        models.LoyaltyAccount.id == account_id
    )
    if with_transactions:
        statement = statement.options(
            selectinload(models.LoyaltyAccount.transactions)
        )
    return db.scalars(statement).first()


def ensure_loyalty_account(
    db: Session,
    customer_id: int,
    *,
    defaults: dict[str, Any] | None = None,
) -> models.LoyaltyAccount:
    account = get_loyalty_account(db, customer_id, with_transactions=False)
    if account is not None:
        return account

    defaults = defaults or {}
    accrual_rate = quantize_rate(
        to_decimal(defaults.get("accrual_rate", Decimal("1")))
    )
    redemption_rate = quantize_rate(
        to_decimal(defaults.get("redemption_rate", Decimal("1")))
    )
    if redemption_rate <= Decimal("0"):
        redemption_rate = Decimal("1.0000")
    expiration_days = int(defaults.get("expiration_days", 365) or 0)
    is_active = bool(defaults.get("is_active", True))
    rule_config = (
        defaults.get("rule_config")
        if isinstance(defaults.get("rule_config"), dict)
        else {}
    )

    with transactional_session(db):
        account = models.LoyaltyAccount(
            customer_id=customer_id,
            accrual_rate=accrual_rate,
            redemption_rate=redemption_rate,
            expiration_days=max(0, expiration_days),
            is_active=is_active,
            rule_config=rule_config,
        )
        db.add(account)
        flush_session(db)
        db.refresh(account)
        enqueue_sync_outbox(
            db,
            entity_type="loyalty_account",
            entity_id=str(account.id),
            operation="UPSERT",
            payload=_loyalty_account_payload(account),
        )
    return account


def update_loyalty_account(
    db: Session,
    customer_id: int,
    payload: schemas.LoyaltyAccountUpdate,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.LoyaltyAccount:
    account = ensure_loyalty_account(db, customer_id)

    with transactional_session(db):
        if payload.accrual_rate is not None:
            account.accrual_rate = quantize_rate(
                to_decimal(payload.accrual_rate)
            )
        if payload.redemption_rate is not None:
            normalized_rate = quantize_rate(
                to_decimal(payload.redemption_rate)
            )
            if normalized_rate <= Decimal("0"):
                raise ValueError("loyalty_redemption_rate_invalid")
            account.redemption_rate = normalized_rate
        if payload.expiration_days is not None:
            account.expiration_days = max(0, int(payload.expiration_days))
        if payload.is_active is not None:
            account.is_active = bool(payload.is_active)
        if payload.rule_config is not None:
            account.rule_config = payload.rule_config
        db.add(account)
        flush_session(db)
        db.refresh(account)

        _log_action(
            db,
            action="loyalty_account_updated",
            entity_type="customer",
            entity_id=str(customer_id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "accrual_rate": float(to_decimal(account.accrual_rate)),
                    "redemption_rate": float(
                        to_decimal(account.redemption_rate)
                    ),
                    "expiration_days": account.expiration_days,
                    "reason": reason,
                }
            ),
        )

        enqueue_sync_outbox(
            db,
            entity_type="loyalty_account",
            entity_id=str(account.id),
            operation="UPSERT",
            payload=_loyalty_account_payload(account),
        )

    return account


def _expire_loyalty_account_if_needed(
    db: Session,
    account: models.LoyaltyAccount,
    *,
    reference_date: datetime,
    performed_by_id: int | None = None,
) -> models.LoyaltyTransaction | None:
    expiration_days = int(account.expiration_days or 0)
    if expiration_days <= 0:
        return None

    last_activity = account.last_redemption_at or account.last_accrual_at
    if last_activity is None:
        last_activity = account.created_at
    if last_activity is None:
        last_activity = reference_date

    deadline = last_activity + timedelta(days=expiration_days)
    if reference_date <= deadline:
        return None

    current_balance = quantize_points(to_decimal(account.balance_points))
    if current_balance <= Decimal("0"):
        account.last_expiration_at = reference_date
        db.add(account)
        return None

    expiration_tx = models.LoyaltyTransaction(
        account_id=account.id,
        transaction_type=models.LoyaltyTransactionType.EXPIRATION,
        points=-current_balance,
        balance_after=Decimal("0"),
        currency_amount=Decimal("0"),
        description="Expiración automática de puntos",
        details={"trigger": "auto_expiration"},
        registered_at=reference_date,
        registered_by_id=performed_by_id,
    )
    account.balance_points = Decimal("0")
    account.expired_points_total = quantize_points(
        to_decimal(account.expired_points_total) + current_balance
    )
    account.last_expiration_at = reference_date
    db.add(expiration_tx)
    db.add(account)
    flush_session(db)
    return expiration_tx


def _record_loyalty_transaction(
    db: Session,
    *,
    account: models.LoyaltyAccount,
    sale_id: int | None,
    transaction_type: models.LoyaltyTransactionType,
    points: Decimal,
    balance_after: Decimal,
    currency_amount: Decimal,
    description: str,
    performed_by_id: int | None,
    expires_at: datetime | None = None,
    details: dict[str, Any] | None = None,
) -> models.LoyaltyTransaction:
    transaction = models.LoyaltyTransaction(
        account_id=account.id,
        sale_id=sale_id,
        transaction_type=transaction_type,
        points=quantize_points(points),
        balance_after=quantize_points(balance_after),
        currency_amount=quantize_currency(currency_amount),
        description=description,
        details=details or {},
        registered_at=datetime.now(timezone.utc),
        registered_by_id=performed_by_id,
        expires_at=expires_at,
    )
    db.add(transaction)
    flush_session(db)
    db.refresh(transaction)
    enqueue_sync_outbox(
        db,
        entity_type="loyalty_transaction",
        entity_id=str(transaction.id),
        operation="UPSERT",
        payload=_loyalty_transaction_payload(transaction),
    )
    return transaction


def apply_loyalty_for_sale(
    db: Session,
    sale: models.Sale,
    *,
    points_payment_amount: Decimal,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> schemas.POSLoyaltySaleSummary | None:
    amount_currency = quantize_currency(to_decimal(points_payment_amount))
    if sale.customer_id is None:
        if amount_currency > Decimal("0"):
            raise ValueError("loyalty_requires_customer")
        return None

    account = ensure_loyalty_account(db, sale.customer_id)
    now = sale.created_at or datetime.now(timezone.utc)

    expiration_tx = _expire_loyalty_account_if_needed(
        db,
        account,
        reference_date=now,
        performed_by_id=performed_by_id,
    )

    redeemed_points = Decimal("0")
    if amount_currency > Decimal("0"):
        redemption_rate = to_decimal(account.redemption_rate)
        if redemption_rate <= Decimal("0"):
            raise ValueError("loyalty_redemption_disabled")
        required_points = quantize_points(amount_currency / redemption_rate)
        if required_points <= Decimal("0"):
            raise ValueError("loyalty_invalid_redeem_amount")
        available = quantize_points(to_decimal(account.balance_points))
        if required_points > available:
            raise ValueError("loyalty_insufficient_points")
        account.balance_points = quantize_points(available - required_points)
        account.lifetime_points_redeemed = quantize_points(
            to_decimal(account.lifetime_points_redeemed) + required_points
        )
        account.last_redemption_at = now
        redeemed_points = required_points
        sale.loyalty_points_redeemed = redeemed_points
        _record_loyalty_transaction(
            db,
            account=account,
            sale_id=sale.id,
            transaction_type=models.LoyaltyTransactionType.REDEEM,
            points=-redeemed_points,
            balance_after=account.balance_points,
            currency_amount=amount_currency,
            description=f"Canje aplicado a la venta #{sale.id}",
            performed_by_id=performed_by_id,
            details={"reason": reason or "redeem"},
        )

    earned_points = Decimal("0")
    if account.is_active:
        accrual_rate = to_decimal(account.accrual_rate)
        if accrual_rate > Decimal("0"):
            earned_points = quantize_points(
                to_decimal(sale.total_amount) * accrual_rate
            )
    if earned_points > Decimal("0"):
        account.balance_points = quantize_points(
            to_decimal(account.balance_points) + earned_points
        )
        account.lifetime_points_earned = quantize_points(
            to_decimal(account.lifetime_points_earned) + earned_points
        )
        account.last_accrual_at = now
        sale.loyalty_points_earned = earned_points
        expires_at = None
        if account.expiration_days > 0:
            expires_at = now + timedelta(days=account.expiration_days)
        _record_loyalty_transaction(
            db,
            account=account,
            sale_id=sale.id,
            transaction_type=models.LoyaltyTransactionType.EARN,
            points=earned_points,
            balance_after=account.balance_points,
            currency_amount=to_decimal(sale.total_amount),
            description=f"Puntos acumulados en venta #{sale.id}",
            performed_by_id=performed_by_id,
            expires_at=expires_at,
            details={"reason": reason or "earn"},
        )

    db.add(account)
    db.add(sale)
    flush_session(db)
    db.refresh(account)
    enqueue_sync_outbox(
        db,
        entity_type="loyalty_account",
        entity_id=str(account.id),
        operation="UPSERT",
        payload=_loyalty_account_payload(account),
    )

    summary = schemas.POSLoyaltySaleSummary(
        account_id=account.id,
        earned_points=earned_points,
        redeemed_points=redeemed_points,
        balance_points=quantize_points(to_decimal(account.balance_points)),
        redemption_amount=amount_currency,
        expiration_days=account.expiration_days if account.expiration_days > 0 else None,
        expires_at=(
            (now + timedelta(days=account.expiration_days))
            if account.expiration_days > 0
            else None
        ),
    )

    if expiration_tx is not None:
        enqueue_sync_outbox(
            db,
            entity_type="loyalty_transaction",
            entity_id=str(expiration_tx.id),
            operation="UPSERT",
            payload=_loyalty_transaction_payload(expiration_tx),
        )

    return summary


def list_loyalty_accounts(
    db: Session,
    *,
    is_active: bool | None = None,
    customer_id: int | None = None,
) -> list[models.LoyaltyAccount]:
    statement = select(models.LoyaltyAccount).options(
        joinedload(models.LoyaltyAccount.customer)
    ).order_by(models.LoyaltyAccount.created_at.desc())
    if is_active is not None:
        statement = statement.where(
            models.LoyaltyAccount.is_active.is_(is_active)
        )
    if customer_id is not None:
        statement = statement.where(
            models.LoyaltyAccount.customer_id == customer_id
        )
    return list(db.scalars(statement))


def list_loyalty_transactions(
    db: Session,
    *,
    account_id: int | None = None,
    customer_id: int | None = None,
    sale_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[models.LoyaltyTransaction]:
    statement = select(models.LoyaltyTransaction).options(
        joinedload(models.LoyaltyTransaction.account)
        .joinedload(models.LoyaltyAccount.customer)
    ).order_by(models.LoyaltyTransaction.registered_at.desc())
    if account_id is not None:
        statement = statement.where(
            models.LoyaltyTransaction.account_id == account_id
        )
    if customer_id is not None:
        statement = statement.join(models.LoyaltyAccount).where(
            models.LoyaltyAccount.customer_id == customer_id
        )
    if sale_id is not None:
        statement = statement.where(
            models.LoyaltyTransaction.sale_id == sale_id)
    if offset:
        statement = statement.offset(max(0, offset))
    if limit:
        statement = statement.limit(max(1, min(limit, 500)))
    return list(db.scalars(statement))


def get_loyalty_summary(db: Session) -> schemas.LoyaltyReportSummary:
    total_accounts = int(
        db.scalar(select(func.count()).select_from(models.LoyaltyAccount)) or 0
    )
    active_accounts = int(
        db.scalar(
            select(func.count()).where(
                models.LoyaltyAccount.is_active.is_(True))
        )
        or 0
    )
    inactive_accounts = total_accounts - active_accounts
    totals = db.execute(
        select(
            func.coalesce(func.sum(models.LoyaltyAccount.balance_points), 0),
            func.coalesce(
                func.sum(models.LoyaltyAccount.lifetime_points_earned), 0),
            func.coalesce(
                func.sum(models.LoyaltyAccount.lifetime_points_redeemed), 0),
            func.coalesce(
                func.sum(models.LoyaltyAccount.expired_points_total), 0),
        )
    ).one()
    balance_sum = quantize_points(to_decimal(totals[0]))
    earned_sum = quantize_points(to_decimal(totals[1]))
    redeemed_sum = quantize_points(to_decimal(totals[2]))
    expired_sum = quantize_points(to_decimal(totals[3]))

    last_activity = db.scalar(
        select(models.LoyaltyTransaction.registered_at)
        .order_by(models.LoyaltyTransaction.registered_at.desc())
        .limit(1)
    )

    return schemas.LoyaltyReportSummary(
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        inactive_accounts=inactive_accounts,
        total_balance=balance_sum,
        total_earned=earned_sum,
        total_redeemed=redeemed_sum,
        total_expired=expired_sum,
        last_activity=last_activity,
    )
