"""Operaciones de base de datos para las entidades principales."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from . import models, schemas


def create_store(db: Session, payload: schemas.StoreCreate) -> models.Store:
    store = models.Store(**payload.dict())
    db.add(store)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("store_already_exists") from exc
    db.refresh(store)
    return store


def list_stores(db: Session) -> list[models.Store]:
    statement = select(models.Store).order_by(models.Store.name.asc())
    return list(db.scalars(statement))


def get_store(db: Session, store_id: int) -> models.Store:
    statement = select(models.Store).where(models.Store.id == store_id)
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("store_not_found") from exc


def create_device(db: Session, store_id: int, payload: schemas.DeviceCreate) -> models.Device:
    get_store(db, store_id)  # valida existencia
    device = models.Device(store_id=store_id, **payload.dict())
    db.add(device)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("device_already_exists") from exc
    db.refresh(device)
    return device


def list_devices(db: Session, store_id: int) -> list[models.Device]:
    get_store(db, store_id)
    statement = select(models.Device).where(models.Device.store_id == store_id).order_by(models.Device.sku.asc())
    return list(db.scalars(statement))
