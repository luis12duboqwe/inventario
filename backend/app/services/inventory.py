"""Servicios de dominio para operaciones de inventario."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .. import schemas
from ..models import Device, Store


def list_stores(db: Session) -> list[schemas.StoreResponse]:
    """Devuelve todas las sucursales ordenadas alfabéticamente."""

    stores = db.query(Store).order_by(Store.name).all()
    return [schemas.StoreResponse.model_validate(store) for store in stores]


def create_store(db: Session, store_in: schemas.StoreCreate) -> schemas.StoreResponse:
    """Persiste una nueva sucursal y la retorna como esquema."""

    store = Store(name=store_in.name, location=store_in.location, timezone=store_in.timezone)
    db.add(store)
    db.commit()
    db.refresh(store)
    return schemas.StoreResponse.model_validate(store)


def list_devices(db: Session, store_id: int) -> list[schemas.DeviceResponse]:
    """Devuelve los dispositivos pertenecientes a una sucursal."""

    devices = db.query(Device).filter(Device.store_id == store_id).order_by(Device.sku).all()
    return [schemas.DeviceResponse.model_validate(device) for device in devices]


def create_device(db: Session, *, store_id: int, device_in: schemas.DeviceCreate) -> schemas.DeviceResponse:
    """Persiste un nuevo dispositivo para una sucursal."""

    device = Device(
        store_id=store_id,
        sku=device_in.sku,
        name=device_in.name,
        quantity=device_in.quantity,
        unit_price=device_in.unit_price,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return schemas.DeviceResponse.model_validate(device)
