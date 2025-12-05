import pytest
from decimal import Decimal
from sqlalchemy.orm import Session
from backend.app import models, schemas
from backend.app.crud import inventory as crud_inventory
from backend.app.models import MovementType


def test_create_inventory_movement_direct(db_session: Session):
    # Setup: Create store and device
    store = models.Store(name="CRUD Test Store",
                         location="123 Test St", code="TEST-001")
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)

    device = models.Device(
        sku="CRUD-TEST-001",
        name="CRUD Test Device",
        quantity=10,
        unit_price=100.0,
        costo_unitario=50.0,
        store_id=store.id
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    # Test: Create movement (OUT)
    movement_data = schemas.MovementCreate(
        producto_id=device.id,
        tipo_movimiento=MovementType.OUT,
        cantidad=2,
        comentario="Test CRUD OUT",
        unit_cost=Decimal("50.0")
    )
    movement = crud_inventory.create_inventory_movement(
        db=db_session,
        payload=movement_data,
        performed_by_id=None,
        store_id=store.id
    )

    # Verify
    assert movement.id is not None
    assert movement.quantity == 2
    assert movement.movement_type == MovementType.OUT

    db_session.refresh(device)
    assert device.quantity == 8  # 10 - 2

    # Verify device stock updated
    db_session.refresh(device)
    assert device.quantity == 8


def test_create_inventory_movement_in_direct(db_session: Session):
    # Setup: Create store and device
    store = models.Store(name="CRUD Test Store IN",
                         location="123 Test St", code="TEST-002")
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)

    device = models.Device(
        sku="CRUD-TEST-002",
        name="CRUD Test Device IN",
        quantity=10,
        unit_price=100.0,
        costo_unitario=50.0,
        store_id=store.id
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    # Test: Create movement (IN)
    movement_data = schemas.MovementCreate(
        producto_id=device.id,
        tipo_movimiento=MovementType.IN,
        cantidad=5,
        comentario="Test CRUD IN",
        unit_cost=Decimal("60.0")
    )

    movement = crud_inventory.create_inventory_movement(
        db=db_session,
        payload=movement_data,
        performed_by_id=None,
        store_id=store.id
    )

    # Verify
    assert movement.id is not None
    assert movement.quantity == 5
    assert movement.movement_type == MovementType.IN

    db_session.refresh(device)
    assert device.quantity == 15  # 10 + 5

    # Verify device stock updated
    db_session.refresh(device)
    assert device.quantity == 15

    # Verify weighted average cost
    # (10 * 50 + 5 * 60) / 15 = (500 + 300) / 15 = 800 / 15 = 53.333...
    assert 53.33 <= device.costo_unitario <= 53.34
