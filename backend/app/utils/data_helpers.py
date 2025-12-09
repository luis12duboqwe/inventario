"""
Utilidades auxiliares de datos y sincronización.

Extraídas desde crud_legacy.py para separación de responsabilidades.
"""

import json
from collections.abc import Sequence
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

from backend.app import models
from backend.app.utils.decimal_helpers import to_decimal
from backend.app.core.transactions import transactional_session
from backend.app.crud.sync import enqueue_sync_outbox


def hydrate_movement_references(
    db: Session, movements: Sequence[models.InventoryMovement]
) -> None:
    """Asocia los metadatos de referencia a los movimientos recuperados."""
    movement_ids = [
        movement.id for movement in movements if movement.id is not None]
    if not movement_ids:
        return

    str_ids = [str(movement_id) for movement_id in movement_ids]
    statement = (
        select(models.AuditLog)
        .where(
            models.AuditLog.entity_type == "inventory_movement",
            models.AuditLog.action == "inventory_movement_reference",
            models.AuditLog.entity_id.in_(str_ids),
        )
        .order_by(models.AuditLog.created_at.desc())
    )
    logs = list(db.scalars(statement))
    reference_map: dict[str, tuple[str | None, str | None]] = {}
    for log in logs:
        if log.entity_id in reference_map:
            continue
        data: dict[str, object]
        try:
            data = json.loads(log.details or "{}")
        except json.JSONDecodeError:
            data = {}
        reference_map[log.entity_id] = (
            str(data.get("reference_type")) if data.get(
                "reference_type") else None,
            str(data.get("reference_id")) if data.get(
                "reference_id") else None,
        )

    for movement in movements:
        reference = reference_map.get(str(movement.id))
        if not reference:
            continue
        reference_type, reference_id = reference
        if reference_type:
            setattr(movement, "reference_type", reference_type)
        if reference_id:
            setattr(movement, "reference_id", reference_id)


def attach_last_audit_trails(
    db: Session,
    records: Sequence,
    *,
    entity_type: str,
) -> None:
    """Adjunta la última auditoría a una lista de registros."""
    if not records:
        return

    record_ids = [
        str(getattr(record, "id", ""))
        for record in records
        if getattr(record, "id", None) is not None
    ]
    if not record_ids:
        return

    statement = (
        select(models.AuditLog)
        .where(
            models.AuditLog.entity_type == entity_type,
            models.AuditLog.entity_id.in_(record_ids),
        )
        .order_by(models.AuditLog.created_at.desc())
    )
    logs = list(db.scalars(statement))
    audit_trails: dict[str, models.AuditLog] = {}
    for log in logs:
        if log.entity_id in audit_trails:
            continue
        audit_trails[log.entity_id] = log

    for record in records:
        record_id = getattr(record, "id", None)
        audit_entry = (
            audit_trails.get(str(record_id)) if record_id is not None else None
        )
        setattr(record, "ultima_accion", audit_entry)


def sync_customer_ledger_entry(db: Session, entry: models.CustomerLedgerEntry) -> None:
    """Sincroniza una entrada de ledger de cliente."""
    with transactional_session(db):
        db.refresh(entry)
        db.refresh(entry, attribute_names=["created_by"])
        from backend.app.utils.ledger_helpers import customer_ledger_payload
        enqueue_sync_outbox(
            db,
            entity_type="customer_ledger_entry",
            entity_id=str(entry.id),
            operation="UPSERT",
            payload=customer_ledger_payload(entry),
        )


def sync_supplier_ledger_entry(db: Session, entry: models.SupplierLedgerEntry) -> None:
    """Sincroniza una entrada de ledger de proveedor."""
    with transactional_session(db):
        db.refresh(entry)
        db.refresh(entry, attribute_names=["created_by"])
        from backend.app.utils.ledger_helpers import supplier_ledger_payload
        enqueue_sync_outbox(
            db,
            entity_type="supplier_ledger_entry",
            entity_id=str(entry.id),
            operation="UPSERT",
            payload=supplier_ledger_payload(entry),
        )


def resolve_part_unit_cost(device: models.Device, provided: Decimal | float | int | None) -> Decimal:
    """Resuelve el costo unitario de una pieza."""
    candidate = to_decimal(provided)
    if candidate <= Decimal("0"):
        if device.costo_unitario and device.costo_unitario > 0:
            candidate = to_decimal(device.costo_unitario)
        else:
            candidate = to_decimal(device.unit_price)
    return candidate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
