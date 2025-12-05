"""Utilidades para asignar lotes de proveedores durante compras."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models


def _normalize_code(value: str) -> str:
    return value.strip()


def _normalize_name(value: str) -> str:
    return value.strip()


def _find_supplier_by_name(db: Session, supplier_name: str) -> models.Supplier | None:
    normalized = _normalize_name(supplier_name)
    if not normalized:
        return None
    statement = select(models.Supplier).where(
        func.lower(models.Supplier.name) == normalized.lower()
    )
    return db.scalars(statement).first()


def _ensure_supplier(db: Session, supplier_name: str) -> models.Supplier:
    supplier = _find_supplier_by_name(db, supplier_name)
    if supplier is not None:
        return supplier
    normalized = _normalize_name(supplier_name)
    supplier = models.Supplier(name=normalized)
    supplier.created_at = datetime.now(timezone.utc)
    supplier.updated_at = supplier.created_at
    db.add(supplier)
    db.flush()
    db.refresh(supplier)
    return supplier


def assign_supplier_batch(
    db: Session,
    *,
    supplier_name: str,
    store: models.Store,
    device: models.Device,
    batch_code: str,
    quantity: int,
    unit_cost: Decimal,
    purchase_date: date | None = None,
) -> models.SupplierBatch:
    """Crea o actualiza el lote indicado agregando la cantidad recibida."""

    normalized_code = _normalize_code(batch_code)
    if not normalized_code:
        raise ValueError("supplier_batch_code_required")
    supplier = _ensure_supplier(db, supplier_name)

    statement = (
        select(models.SupplierBatch)
        .where(models.SupplierBatch.supplier_id == supplier.id)
        .where(func.lower(models.SupplierBatch.batch_code) == normalized_code.lower())
        .order_by(models.SupplierBatch.created_at.desc())
    )
    batch = db.scalars(statement).first()

    if batch is None:
        batch = models.SupplierBatch(
            supplier_id=supplier.id,
            store_id=store.id,
            device_id=device.id,
            model_name=device.name,
            batch_code=normalized_code,
            unit_cost=unit_cost,
            quantity=0,
            purchase_date=purchase_date or date.today(),
        )
    else:
        if batch.store_id != store.id:
            batch.store_id = store.id
        if batch.device_id != device.id:
            batch.device_id = device.id
        batch.model_name = device.name
        batch.unit_cost = unit_cost
        batch.purchase_date = purchase_date or batch.purchase_date

    batch.quantity += quantity
    batch.updated_at = datetime.now(timezone.utc)
    db.add(batch)
    db.flush()
    db.refresh(batch)
    return batch
