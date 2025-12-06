"""Operaciones CRUD para el módulo de Almacenes (Warehouses)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from .. import models
from ..core.transactions import flush_session, transactional_session
from .stores import get_store


def unset_default_warehouse(db: Session, store_id: int, keep_id: int | None = None) -> None:
    query = db.query(models.Warehouse).filter(
        models.Warehouse.store_id == store_id)
    if keep_id is not None:
        query = query.filter(models.Warehouse.id != keep_id)
    query.update({"is_default": False}, synchronize_session=False)


def ensure_default_warehouse(db: Session, store_id: int) -> models.Warehouse:
    existing_default = db.scalars(
        select(models.Warehouse)
        .where(models.Warehouse.store_id == store_id)
        .where(models.Warehouse.is_default.is_(True))
    ).first()
    if existing_default:
        return existing_default
    fallback = db.scalars(
        select(models.Warehouse)
        .where(models.Warehouse.store_id == store_id)
        .where(func.lower(models.Warehouse.name) == "default")
    ).first()
    if fallback:
        with transactional_session(db):
            unset_default_warehouse(db, store_id, keep_id=fallback.id)
            fallback.is_default = True
            db.add(fallback)
        return fallback
    code = f"DEF-{store_id}"
    warehouse = models.Warehouse(
        store_id=store_id,
        name="Default",
        code=code,
        is_default=True,
    )
    with transactional_session(db):
        db.add(warehouse)
        flush_session(db)
    return warehouse


def list_warehouses(
    db: Session, store_id: int, *, include_inactive_default: bool = True
) -> list[models.Warehouse]:
    get_store(db, store_id)
    statement = (
        select(models.Warehouse)
        .where(models.Warehouse.store_id == store_id)
        .order_by(models.Warehouse.is_default.desc(), models.Warehouse.name.asc())
    )
    warehouses = list(db.scalars(statement))
    if warehouses:
        return warehouses
    default = ensure_default_warehouse(db, store_id)
    return [default]


def get_warehouse(
    db: Session, warehouse_id: int, *, store_id: int | None = None
) -> models.Warehouse:
    statement = select(models.Warehouse).where(models.Warehouse.id == warehouse_id)
    if store_id is not None:
        statement = statement.where(models.Warehouse.store_id == store_id)
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("warehouse_not_found") from exc


__all__ = [
    "ensure_default_warehouse",
    "get_warehouse",
    "list_warehouses",
    "unset_default_warehouse",
]
