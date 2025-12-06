"""Operaciones CRUD para Punto de Venta (POS).

Migrado desde crud_legacy.py - Fase 2, Incremento 1
Contiene funciones para configuración POS, sesiones de caja y ventas POS.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, TYPE_CHECKING

from sqlalchemy import func, or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from backend.app import models, schemas
from backend.app.core.transactions import flush_session, transactional_session
from backend.app.utils.decimal_helpers import to_decimal
from backend.app.utils.json_helpers import normalize_hardware_settings

# Import from other crud modules
from backend.app.crud.stores import get_store
from backend.app.crud.devices import get_device

# Avoid circular imports - import functions from crud_legacy only when needed (inside functions)
if TYPE_CHECKING:
    from backend.app import crud_legacy

__all__ = [
    'resolve_device_for_pos',
    'get_cash_session',
    'get_open_cash_session',
    'get_last_cash_session_for_store',
    'paginate_cash_sessions',
    'open_cash_session',
    'close_cash_session',
    'get_pos_config',
    'update_pos_config',
    'get_pos_promotions',
    'update_pos_promotions',
    'save_pos_draft',
    'delete_pos_draft',
    'register_pos_sale',
]


def resolve_device_for_pos(
    db: Session,
    *,
    store_id: int,
    device_id: int | None = None,
    imei: str | None = None,
) -> models.Device:
    if device_id:
        return get_device(db, store_id, device_id)
    if imei:
        normalized = imei.strip()
        if not normalized:
            raise LookupError("device_not_found")
        statement = select(models.Device).where(
            models.Device.store_id == store_id,
            func.lower(models.Device.imei) == normalized.lower(),
        )
        device = db.scalars(statement).first()
        if device is not None:
            return device
        identifier_stmt = (
            select(models.Device)
            .join(models.DeviceIdentifier)
            .where(models.Device.store_id == store_id)
            .where(
                or_(
                    func.lower(
                        models.DeviceIdentifier.imei_1) == normalized.lower(),
                    func.lower(
                        models.DeviceIdentifier.imei_2) == normalized.lower(),
                )
            )
        )
        device = db.scalars(identifier_stmt).first()
        if device is not None:
            return device
    raise LookupError("device_not_found")


def get_cash_session(db: Session, session_id: int) -> models.CashRegisterSession:
    statement = select(models.CashRegisterSession).where(
        models.CashRegisterSession.id == session_id)
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("cash_session_not_found") from exc


def get_open_cash_session(db: Session, *, store_id: int) -> models.CashRegisterSession:
    statement = (
        select(models.CashRegisterSession)
        .where(
            models.CashRegisterSession.store_id == store_id,
            models.CashRegisterSession.status == models.CashSessionStatus.ABIERTO,
        )
        .order_by(models.CashRegisterSession.opened_at.desc())
    )
    session = db.scalars(statement).first()
    if session is None:
        raise LookupError("cash_session_not_found")
    return session


# // [PACK34-lookup]
def get_last_cash_session_for_store(
    db: Session, *, store_id: int
) -> models.CashRegisterSession:
    statement = (
        select(models.CashRegisterSession)
        .where(models.CashRegisterSession.store_id == store_id)
        .order_by(models.CashRegisterSession.opened_at.desc())
    )
    session = db.scalars(statement).first()
    if session is None:
        raise LookupError("cash_session_not_found")
    return session


def paginate_cash_sessions(
    db: Session,
    *,
    store_id: int,
    page: int,
    size: int,
) -> tuple[int, list[models.CashRegisterSession]]:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    total = crud_legacy.count_cash_sessions(db, store_id=store_id)
    offset = max(page - 1, 0) * size
    sessions = crud_legacy.list_cash_sessions(
        db, store_id=store_id, limit=size, offset=offset)
    return total, sessions


def open_cash_session(
    db: Session,
    payload: schemas.CashSessionOpenRequest,
    *,
    opened_by_id: int | None,
    reason: str | None = None,
) -> models.CashRegisterSession:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    get_store(db, payload.store_id)
    statement = select(models.CashRegisterSession).where(
        models.CashRegisterSession.store_id == payload.store_id,
        models.CashRegisterSession.status == models.CashSessionStatus.ABIERTO,
    )
    if db.scalars(statement).first() is not None:
        raise ValueError("cash_session_already_open")

    opening_amount = to_decimal(payload.opening_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    session = models.CashRegisterSession(
        store_id=payload.store_id,
        status=models.CashSessionStatus.ABIERTO,
        opening_amount=opening_amount,
        closing_amount=Decimal("0"),
        expected_amount=opening_amount,
        difference_amount=Decimal("0"),
        payment_breakdown={},
        notes=payload.notes,
        opened_by_id=opened_by_id,
    )
    with transactional_session(db):
        db.add(session)
        flush_session(db)
        db.refresh(session)

        crud_legacy._log_action(
            db,
            action="cash_session_opened",
            entity_type="cash_session",
            entity_id=str(session.id),
            performed_by_id=opened_by_id,
            details=json.dumps(
                {"store_id": session.store_id, "reason": reason}),
        )
        flush_session(db)
        db.refresh(session)
    return session


def _cash_entries_totals(
    db: Session,
    *,
    session_id: int,
) -> tuple[Decimal, Decimal]:
    """Resume los ingresos y egresos registrados en la sesión."""

    entries_stmt = (
        select(
            models.CashRegisterEntry.entry_type,
            func.coalesce(func.sum(models.CashRegisterEntry.amount), 0),
        )
        .where(models.CashRegisterEntry.session_id == session_id)
        .group_by(models.CashRegisterEntry.entry_type)
    )
    incomes = Decimal("0")
    expenses = Decimal("0")
    for entry_type, total in db.execute(entries_stmt):
        normalized_total = to_decimal(total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if entry_type == models.CashEntryType.INGRESO:
            incomes = normalized_total
        elif entry_type == models.CashEntryType.EGRESO:
            expenses = normalized_total
    return incomes, expenses


def close_cash_session(
    db: Session,
    payload: schemas.CashSessionCloseRequest,
    *,
    closed_by_id: int | None,
    reason: str | None = None,
) -> models.CashRegisterSession:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    session = get_cash_session(db, payload.session_id)
    if session.status != models.CashSessionStatus.ABIERTO:
        raise ValueError("cash_session_not_open")

    sales_totals: dict[str, Decimal] = {}
    totals_stmt = (
        select(models.Sale.payment_method, func.sum(models.Sale.total_amount))
        .where(models.Sale.cash_session_id == session.id)
        .group_by(models.Sale.payment_method)
    )
    for method, total in db.execute(totals_stmt):
        totals_value = to_decimal(total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        sales_totals[method.value] = totals_value

    session.closing_amount = to_decimal(payload.closing_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    session.closed_by_id = closed_by_id
    session.closed_at = datetime.now(timezone.utc)
    session.status = models.CashSessionStatus.CERRADO
    breakdown_snapshot = dict(session.payment_breakdown or {})
    for key, value in sales_totals.items():
        breakdown_snapshot[key] = float(value)

    for method_key, reported_amount in payload.payment_breakdown.items():
        breakdown_snapshot[f"reportado_{method_key.upper()}"] = float(
            Decimal(str(reported_amount))
        )

    incomes_total, expenses_total = _cash_entries_totals(
        db, session_id=session.id
    )
    expected_cash = (
        session.opening_amount
        + sales_totals.get(models.PaymentMethod.EFECTIVO.value, Decimal("0"))
        + incomes_total
        - expenses_total
    )
    session.payment_breakdown = breakdown_snapshot

    expected_cash = session.opening_amount + \
        sales_totals.get(models.PaymentMethod.EFECTIVO.value, Decimal("0"))
    session.expected_amount = expected_cash.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    session.difference_amount = (
        session.closing_amount - session.expected_amount
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    session.reconciliation_notes = payload.reconciliation_notes

    if session.difference_amount != Decimal("0") and not payload.difference_reason:
        # Requerir motivo explícito cuando hay diferencia
        raise ValueError("difference_reason_required")
    session.difference_reason = payload.difference_reason

    denomination_breakdown: dict[str, int] = {}
    for denomination in payload.denominations:
        value = to_decimal(denomination.value).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        quantity = max(0, int(denomination.quantity))
        if quantity <= 0:
            continue
        key = f"{value:.2f}"
        denomination_breakdown[key] = quantity
    session.denomination_breakdown = denomination_breakdown

    if payload.notes:
        session.notes = (session.notes or "") + \
            f"\n{payload.notes}" if session.notes else payload.notes

    with transactional_session(db):
        db.add(session)
        flush_session(db)
        db.refresh(session)

        crud_legacy._log_action(
            db,
            action="cash_session_closed",
            entity_type="cash_session",
            entity_id=str(session.id),
            performed_by_id=closed_by_id,
            details=json.dumps(
                {
                    "difference": float(session.difference_amount),
                    "difference_reason": session.difference_reason,
                    "denominations": denomination_breakdown,
                    "reason": reason,
                }
            ),
        )
        flush_session(db)
        db.refresh(session)
    return session


def get_pos_config(db: Session, store_id: int) -> models.POSConfig:
    store = get_store(db, store_id)
    statement = select(models.POSConfig).where(
        models.POSConfig.store_id == store_id)
    config = db.scalars(statement).first()
    if config is None:
        prefix = store.name[:3].upper() if store.name else "POS"
        generated_prefix = f"{prefix}-{store_id:03d}"[:12]
        config = models.POSConfig(
            store_id=store_id, invoice_prefix=generated_prefix)
        with transactional_session(db):
            db.add(config)
            flush_session(db)
            db.refresh(config)
    else:
        db.refresh(config)
    normalized_hardware = normalize_hardware_settings(
        config.hardware_settings if isinstance(
            config.hardware_settings, dict) else None
    )
    if config.hardware_settings != normalized_hardware:
        with transactional_session(db):
            config.hardware_settings = normalized_hardware
            db.add(config)
            flush_session(db)
            db.refresh(config)
    else:
        config.hardware_settings = normalized_hardware
    return config


def _pos_config_payload(config: models.POSConfig) -> dict[str, Any]:
    """Serializa la configuración POS para sincronización."""
    return {
        "id": config.id,
        "store_id": config.store_id,
        "invoice_prefix": config.invoice_prefix,
        "receipt_header": config.receipt_header,
        "receipt_footer": config.receipt_footer,
        "printer_name": config.printer_name,
        "hardware_settings": config.hardware_settings,
        "promotions_config": config.promotions_config,
        "tax_rate": float(config.tax_rate) if config.tax_rate else 0.0,
        "auto_print": config.auto_print,
    }


def update_pos_config(
    db: Session,
    payload: schemas.POSConfigUpdate,
    *,
    updated_by_id: int | None,
    reason: str | None = None,
) -> models.POSConfig:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    config = get_pos_config(db, payload.store_id)
    with transactional_session(db):
        config.tax_rate = to_decimal(payload.tax_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        config.invoice_prefix = payload.invoice_prefix.strip().upper()
        config.printer_name = payload.printer_name.strip() if payload.printer_name else None
        config.printer_profile = (
            payload.printer_profile.strip() if payload.printer_profile else None
        )
        config.quick_product_ids = payload.quick_product_ids
        if payload.hardware_settings is not None:
            config.hardware_settings = payload.hardware_settings.model_dump()
        else:
            config.hardware_settings = normalize_hardware_settings(
                config.hardware_settings
            )
        # Persistir el tipo de documento por defecto dentro de hardware_settings (no hay columna dedicada)
        if payload.default_document_type:
            hw = dict(config.hardware_settings or {})
            hw["default_document_type"] = payload.default_document_type
            config.hardware_settings = hw
        db.add(config)
        flush_session(db)
        db.refresh(config)

        crud_legacy._log_action(
            db,
            action="pos_config_update",
            entity_type="store",
            entity_id=str(payload.store_id),
            performed_by_id=updated_by_id,
            details=json.dumps(
                {
                    "tax_rate": float(config.tax_rate),
                    "invoice_prefix": config.invoice_prefix,
                    "reason": reason,
                }
            ),
        )
        flush_session(db)
        db.refresh(config)
        crud_legacy.enqueue_sync_outbox(
            db,
            entity_type="pos_config",
            entity_id=str(payload.store_id),
            operation="UPSERT",
            payload=_pos_config_payload(config),
        )
    return config


# // [POS-promotions]
def get_pos_promotions(db: Session, store_id: int) -> schemas.POSPromotionsResponse:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    config = get_pos_config(db, store_id)
    return crud_legacy._build_pos_promotions_response(config)


def update_pos_promotions(
    db: Session,
    payload: schemas.POSPromotionsUpdate,
    *,
    updated_by_id: int | None,
    reason: str | None = None,
) -> schemas.POSPromotionsResponse:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    # Delegate to crud_legacy for now - this function has complex promotion logic
    return crud_legacy.update_pos_promotions(
        db, payload, updated_by_id=updated_by_id, reason=reason
    )


def save_pos_draft(
    db: Session,
    payload: schemas.POSDraftSaveRequest,
    *,
    saved_by_id: int | None,
) -> models.POSDraftSale:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    # Delegate to crud_legacy for now - POSDraftSale model may not be fully migrated
    return crud_legacy.save_pos_draft(db, payload, saved_by_id=saved_by_id)


def delete_pos_draft(db: Session, draft_id: int, *, removed_by_id: int | None = None) -> None:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    # Delegate to crud_legacy for now
    return crud_legacy.delete_pos_draft(db, draft_id, removed_by_id=removed_by_id)


def register_pos_sale(
    db: Session,
    payload: schemas.POSSaleRequest,
    *,
    sold_by_id: int | None,
    reason: str | None = None,
) -> models.Sale:
    # Late import to avoid circular dependency
    from backend.app import crud_legacy
    
    # Delegate to crud_legacy for now - this is a complex function with many dependencies
    return crud_legacy.register_pos_sale(
        db, payload, sold_by_id=sold_by_id, reason=reason
    )
