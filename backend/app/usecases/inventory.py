"""Casos de uso de inventario que desacoplan servicios de CRUD."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .. import crud, models, schemas


def list_stores(
    db: Session,
    *,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.Store]:
    """Obtiene las sucursales registradas respetando los límites solicitados."""

    stores = crud.list_stores(db, limit=limit, offset=offset)
    return list(stores)


def create_store(
    db: Session,
    store_in: schemas.StoreCreate,
    *,
    performed_by_id: int | None,
) -> models.Store:
    """Registra una nueva sucursal manteniendo el historial de auditoría."""

    return crud.create_store(db, store_in, performed_by_id=performed_by_id)


def list_devices(
    db: Session,
    store_id: int,
    *,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.Device]:
    """Obtiene los dispositivos asociados a una sucursal corporativa."""

    devices = crud.list_devices(db, store_id, limit=limit, offset=offset)
    return list(devices)


def create_device(
    db: Session,
    *,
    store_id: int,
    device_in: schemas.DeviceCreate,
    performed_by_id: int | None,
) -> models.Device:
    """Registra un dispositivo siguiendo las validaciones de catálogo pro."""

    return crud.create_device(
        db,
        store_id,
        device_in,
        performed_by_id=performed_by_id,
    )


__all__ = [
    "list_stores",
    "create_store",
    "list_devices",
    "create_device",
]
