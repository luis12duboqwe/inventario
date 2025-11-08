"""Servicios de apoyo para consumo de lotes en ventas."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models


def _normalize_code(value: str) -> str:
    return value.strip()


def consume_supplier_batch(
    db: Session,
    *,
    store: models.Store,
    device: models.Device,
    batch_code: str,
    quantity: int,
) -> models.SupplierBatch:
    """Descuenta la cantidad vendida del lote indicado."""

    normalized_code = _normalize_code(batch_code)
    if not normalized_code:
        raise ValueError("supplier_batch_code_required")

    statement = (
        select(models.SupplierBatch)
        .where(func.lower(models.SupplierBatch.batch_code) == normalized_code.lower())
        .order_by(models.SupplierBatch.purchase_date.desc(), models.SupplierBatch.created_at.desc())
    )
    candidates = list(db.scalars(statement))
    target: models.SupplierBatch | None = None
    for batch in candidates:
        if batch.store_id not in (None, store.id):
            continue
        if batch.device_id not in (None, device.id):
            continue
        target = batch
        break

    if target is None:
        raise LookupError("supplier_batch_not_found")
    if target.quantity < quantity:
        raise ValueError("supplier_batch_insufficient_stock")

    target.quantity -= quantity
    target.updated_at = datetime.utcnow()
    if target.store_id is None:
        target.store_id = store.id
    if target.device_id is None:
        target.device_id = device.id
    target.model_name = device.name
    db.add(target)
    db.flush()
    db.refresh(target)
    return target
