"""Domain services for inventory operations."""
from sqlalchemy.orm import Session

from .. import schemas
from ..models import Device, Store


def list_stores(db: Session) -> list[schemas.Store]:
    """Return all stores ordered alphabetically."""

    stores = db.query(Store).order_by(Store.name).all()
    return [schemas.Store.model_validate(store) for store in stores]


def create_store(db: Session, store_in: schemas.StoreCreate) -> schemas.Store:
    """Persist a new store and return it as schema."""

    store = Store(name=store_in.name, location=store_in.location, timezone=store_in.timezone)
    db.add(store)
    db.commit()
    db.refresh(store)
    return schemas.Store.model_validate(store)


def list_devices(db: Session, store_id: int) -> list[schemas.Device]:
    """Return devices belonging to a store."""

    devices = db.query(Device).filter(Device.store_id == store_id).order_by(Device.sku).all()
    return [schemas.Device.model_validate(device) for device in devices]


def create_device(db: Session, *, store_id: int, device_in: schemas.DeviceCreate) -> schemas.Device:
    """Persist a new device for a store."""

    device = Device(
        store_id=store_id,
        sku=device_in.sku,
        name=device_in.name,
        quantity=device_in.quantity,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return schemas.Device.model_validate(device)
