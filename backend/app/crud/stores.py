"""Operaciones CRUD para el módulo de Sucursales (Stores)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.transactions import flush_session, transactional_session
from .common import to_decimal
from .audit import log_audit_event as _log_action


def _normalize_store_status(value: str | None) -> str:
    if value is None:
        return "activa"
    normalized = value.strip().lower()
    return normalized or "activa"


def _normalize_store_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def _generate_store_code(db: Session) -> str:
    statement = select(models.Store.code)
    highest_sequence = 0
    for existing_code in db.scalars(statement):
        if not existing_code:
            continue
        prefix, separator, suffix = existing_code.partition("-")
        if prefix != "SUC" or separator != "-" or not suffix.isdigit():
            continue
        highest_sequence = max(highest_sequence, int(suffix))
    return f"SUC-{highest_sequence + 1:03d}"


def create_store(
    db: Session,
    payload: schemas.StoreCreate,
    *,
    performed_by_id: int | None = None
) -> models.Store:
    with transactional_session(db):
        status = _normalize_store_status(payload.status)
        code = _normalize_store_code(payload.code)
        timezone_val = (payload.timezone or "UTC").strip()
        store = models.Store(
            name=payload.name.strip(),
            location=payload.location.strip() if payload.location else None,
            phone=payload.phone.strip() if payload.phone else None,
            manager=payload.manager.strip() if payload.manager else None,
            status=status,
            code=code or _generate_store_code(db),
            timezone=timezone_val or "UTC",
        )
        db.add(store)
        try:
            flush_session(db)
        except IntegrityError as exc:
            message = str(getattr(exc, "orig", exc)).lower()
            if "codigo" in message or "uq_sucursales_codigo" in message:
                raise ValueError("store_code_already_exists") from exc
            raise ValueError("store_already_exists") from exc
        db.refresh(store)

        _log_action(
            db,
            action="store_created",
            entity_type="store",
            entity_id=str(store.id),
            performed_by_id=performed_by_id,
        )
        flush_session(db)
        db.refresh(store)
    return store


def get_store(db: Session, store_id: int) -> models.Store:
    statement = select(models.Store).where(
        models.Store.id == store_id, models.Store.is_deleted.is_(False)
    )
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("store_not_found") from exc


def update_store(
    db: Session,
    store_id: int,
    payload: schemas.StoreUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.Store:
    store = get_store(db, store_id)

    changes: list[str] = []
    if payload.name is not None:
        normalized_name = payload.name.strip()
        if normalized_name and normalized_name != store.name:
            changes.append(f"name:{store.name}->{normalized_name}")
            store.name = normalized_name

    if payload.location is not None:
        normalized_location = payload.location.strip() if payload.location else None
        if normalized_location != store.location:
            previous = store.location or ""
            new_value = normalized_location or ""
            changes.append(f"location:{previous}->{new_value}")
            store.location = normalized_location

    if payload.status is not None:
        normalized_status = _normalize_store_status(payload.status)
        if normalized_status != store.status:
            changes.append(f"status:{store.status}->{normalized_status}")
            store.status = normalized_status

    if payload.code is not None:
        normalized_code = _normalize_store_code(payload.code)
        if normalized_code != store.code and normalized_code is not None:
            changes.append(f"code:{store.code}->{normalized_code}")
            store.code = normalized_code

    if payload.timezone is not None:
        normalized_timezone = (payload.timezone or "UTC").strip() or "UTC"
        if normalized_timezone != store.timezone:
            changes.append(f"timezone:{store.timezone}->{normalized_timezone}")
            store.timezone = normalized_timezone

    if not changes:
        return store

    with transactional_session(db):
        db.add(store)
        try:
            flush_session(db)
        except IntegrityError as exc:
            message = str(getattr(exc, "orig", exc)).lower()
            if "codigo" in message or "uq_sucursales_codigo" in message:
                raise ValueError("store_code_already_exists") from exc
            raise ValueError("store_already_exists") from exc
        db.refresh(store)

        details = ", ".join(changes)
        _log_action(
            db,
            action="store_updated",
            entity_type="store",
            entity_id=str(store.id),
            performed_by_id=performed_by_id,
            details=details or None,
        )
        flush_session(db)
        db.refresh(store)
    return store


def list_stores(
    db: Session,
    *,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.Store]:
    statement = (
        select(models.Store)
        .where(models.Store.is_deleted.is_(False))
        .order_by(models.Store.name.asc())
    )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement))


def count_stores(db: Session) -> int:
    statement = select(func.count()).select_from(models.Store).where(
        models.Store.is_deleted.is_(False)
    )
    return int(db.scalar(statement) or 0)


def get_store_by_name(db: Session, name: str) -> models.Store | None:
    normalized = (name or "").strip()
    if not normalized:
        return None
    statement = (
        select(models.Store)
        .where(
            func.lower(models.Store.name) == normalized.lower(),
            models.Store.is_deleted.is_(False),
        )
    )
    return db.scalars(statement).first()


def soft_delete_store(
    db: Session,
    store_id: int,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.Store:
    store = get_store(db, store_id)
    if store.is_deleted:
        return store

    with transactional_session(db):
        store.is_deleted = True
        store.deleted_at = datetime.now(timezone.utc)
        db.add(store)

        details = {
            "description": f"Sucursal desactivada: {store.name}",
            "metadata": {"store_id": store.id},
        }
        if reason:
            details["metadata"]["reason"] = reason.strip()

        _log_action(
            db,
            action="store_soft_deleted",
            entity_type="store",
            entity_id=str(store.id),
            performed_by_id=performed_by_id,
            details=json.dumps(details),
        )
        flush_session(db)
        db.refresh(store)
    return store


def ensure_store_by_name(
    db: Session, name: str, *, performed_by_id: int | None = None
) -> tuple[models.Store, bool]:
    existing = get_store_by_name(db, name)
    if existing is not None:
        return existing, False
    payload = schemas.StoreCreate(
        name=name.strip(),
        location=None,
        phone=None,
        manager=None,
        status="activa",
        timezone="UTC",
        code=None,
    )
    store = create_store(db, payload, performed_by_id=performed_by_id)
    return store, True


def recalculate_store_inventory_value(
    db: Session, store: models.Store | int
) -> Decimal:
    if isinstance(store, models.Store):
        store_obj = store
    else:
        store_obj = get_store(db, int(store))
    flush_session(db)
    total_value = db.scalar(
        select(func.coalesce(
            func.sum(models.Device.quantity * models.Device.unit_price), 0))
        .where(models.Device.store_id == store_obj.id)
    )
    normalized_total = to_decimal(total_value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    store_obj.inventory_value = normalized_total
    db.add(store_obj)
    flush_session(db)
    return normalized_total


def recalculate_store_inventory_value(
    db: Session, store: models.Store | int
) -> Decimal:
    if isinstance(store, models.Store):
        store_obj = store
    else:
        store_obj = get_store(db, int(store))
    flush_session(db)
    total_value = db.scalar(
        select(func.coalesce(
            func.sum(models.Device.quantity * models.Device.unit_price), 0))
        .where(models.Device.store_id == store_obj.id)
    )
    normalized_total = to_decimal(total_value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    store_obj.inventory_value = normalized_total
    db.add(store_obj)
    flush_session(db)
    return normalized_total
