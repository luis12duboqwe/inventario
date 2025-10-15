"""Servicios de dominio para operaciones de inventario heredadas."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .. import crud, schemas


def list_stores(db: Session) -> list[schemas.StoreResponse]:
    """Devuelve todas las sucursales disponibles ordenadas alfabéticamente."""

    stores = crud.list_stores(db)
    return [schemas.StoreResponse.model_validate(store, from_attributes=True) for store in stores]


def create_store(db: Session, store_in: schemas.StoreCreate) -> schemas.StoreResponse:
    """Persiste una nueva sucursal reutilizando las validaciones corporativas."""

    store = crud.create_store(db, store_in, performed_by_id=None)
    return schemas.StoreResponse.model_validate(store, from_attributes=True)


def list_devices(db: Session, store_id: int) -> list[schemas.DeviceResponse]:
    """Devuelve los dispositivos pertenecientes a una sucursal."""

    devices = crud.list_devices(db, store_id)
    return [schemas.DeviceResponse.model_validate(device, from_attributes=True) for device in devices]


def create_device(
    db: Session,
    *,
    store_id: int,
    device_in: schemas.DeviceCreate,
) -> schemas.DeviceResponse:
    """Persiste un nuevo dispositivo para una sucursal con reglas de catálogo pro."""

    device = crud.create_device(db, store_id, device_in, performed_by_id=None)
    return schemas.DeviceResponse.model_validate(device, from_attributes=True)
