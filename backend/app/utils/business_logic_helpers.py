"""
Utilidades de lógica de negocios para créditos de tienda y lealtad.

Extraídas desde crud_legacy.py para separación de responsabilidades.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

from backend.app import models
from backend.app.utils.decimal_helpers import (
    to_decimal,
    quantize_currency,
    quantize_points,
    format_currency,
)
from backend.app.utils.customer_helpers import ensure_positive_decimal
from backend.app.utils.json_helpers import append_customer_history
from backend.app.utils.normalization_helpers import normalize_optional_note
from backend.app.crud.common import flush_session


def generate_store_credit_code(db: Session) -> str:
    """Genera un código único para nota de crédito."""
    for _ in range(10):
        candidate = f"NC-{uuid4().hex[:10].upper()}"
        exists = db.scalar(
            select(models.StoreCredit.id).where(
                models.StoreCredit.code == candidate)
        )
        if not exists:
            return candidate
    raise RuntimeError("store_credit_code_generation_failed")


def apply_store_credit_redemption(
    db: Session,
    *,
    credit: models.StoreCredit,
    amount: Decimal,
    sale_id: int | None,
    notes: str | None,
    performed_by_id: int | None,
    create_ledger_entry_fn,  # Función _create_customer_ledger_entry
) -> models.StoreCreditRedemption:
    """Aplica una redención de crédito de tienda."""
    amount_value = ensure_positive_decimal(
        amount, "store_credit_invalid_amount")
    current_balance = to_decimal(credit.balance_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if amount_value > current_balance:
        raise ValueError("store_credit_insufficient_balance")

    new_balance = (current_balance - amount_value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    credit.balance_amount = new_balance
    if new_balance == Decimal("0"):
        credit.status = models.StoreCreditStatus.REDIMIDO
        credit.redeemed_at = datetime.now(timezone.utc)
    else:
        credit.status = models.StoreCreditStatus.PARCIAL

    redemption = models.StoreCreditRedemption(
        store_credit_id=credit.id,
        sale_id=sale_id,
        amount=amount_value,
        notes=notes,
        created_by_id=performed_by_id,
    )
    db.add(redemption)

    customer = credit.customer
    message = (
        f"Aplicación de nota de crédito {credit.code} por ${format_currency(amount_value)}"
    )
    append_customer_history(customer, message)
    details = {
        "amount_applied": float(amount_value),
        "balance_after": float(new_balance),
        "code": credit.code,
        "sale_id": sale_id,
    }
    create_ledger_entry_fn(
        db,
        customer=customer,
        entry_type=models.CustomerLedgerEntryType.STORE_CREDIT_REDEEMED,
        amount=Decimal("0"),
        note=notes,
        reference_type="store_credit",
        reference_id=str(credit.id),
        details=details,
        created_by_id=performed_by_id,
    )
    return redemption


def expire_loyalty_account_if_needed(
    db: Session,
    account: models.LoyaltyAccount,
    *,
    reference_date: datetime,
    performed_by_id: int | None = None,
) -> models.LoyaltyTransaction | None:
    """Expira puntos de lealtad si es necesario."""
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


def record_loyalty_transaction(
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
    enqueue_sync_fn,  # Función enqueue_sync_outbox
    loyalty_transaction_payload_fn,  # Función _loyalty_transaction_payload
) -> models.LoyaltyTransaction:
    """Registra una transacción de lealtad."""
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
    enqueue_sync_fn(
        db,
        entity_type="loyalty_transaction",
        entity_id=str(transaction.id),
        operation="UPSERT",
        payload=loyalty_transaction_payload_fn(transaction),
    )
    return transaction


def register_purchase_status_event(
    db: Session,
    order: models.PurchaseOrder,
    *,
    status: models.PurchaseStatus,
    note: str | None = None,
    created_by_id: int | None = None,
) -> models.PurchaseOrderStatusEvent:
    """Registra un evento de cambio de estado en orden de compra."""
    event = models.PurchaseOrderStatusEvent(
        purchase_order_id=order.id,
        status=status,
        note=normalize_optional_note(note),
        created_by_id=created_by_id,
    )
    db.add(event)
    flush_session(db)
    db.refresh(event)
    return event
