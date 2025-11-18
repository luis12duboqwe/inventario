from datetime import date
from decimal import Decimal

from backend.app import crud, schemas
from backend.app.models import Device
from backend.app.services import pricing


def _create_store(db_session) -> int:
    store = crud.create_store(
        db_session,
        schemas.StoreCreate(
            name="Sucursal Centro",
            location=None,
            phone=None,
            manager=None,
            status="activa",
            timezone="UTC",
            code=None,
        ),
        performed_by_id=None,
    )
    return store.id


def _create_customer(db_session) -> int:
    customer = crud.create_customer(
        db_session,
        schemas.CustomerCreate(
            name="Cliente Demo",
            phone="5512345678",
            contact_name=None,
            email="cliente@example.com",
            address=None,
            customer_type="minorista",
            status="activo",
            credit_limit=Decimal("0"),
            notes=None,
            outstanding_debt=Decimal("0"),
            history=[],
        ),
        performed_by_id=None,
    )
    return customer.id


def _create_device(db_session, store_id: int) -> int:
    device = Device(
        store_id=store_id,
        sku="SKU-001",
        name="Equipo Demo",
        quantity=1,
        unit_price=Decimal("150.00"),
        costo_unitario=Decimal("120.00"),
        margen_porcentaje=Decimal("0"),
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device.id


def test_resolve_device_price_prefers_specific_scope(db_session):
    store_id = _create_store(db_session)
    customer_id = _create_customer(db_session)
    device_id = _create_device(db_session, store_id)

    global_list = crud.create_price_list(
        db_session,
        schemas.PriceListCreate(
            name="Global",
            description="Lista global",
            is_active=True,
            store_id=None,
            customer_id=None,
            currency="MXN",
            valid_from=None,
            valid_until=None,
        ),
        performed_by_id=None,
    )
    crud.create_price_list_item(
        db_session,
        global_list.id,
        schemas.PriceListItemCreate(
            device_id=device_id,
            price=Decimal("200.00"),
            discount_percentage=None,
            notes=None,
        ),
        performed_by_id=None,
    )

    store_list = crud.create_price_list(
        db_session,
        schemas.PriceListCreate(
            name="Sucursal",
            description=None,
            is_active=True,
            store_id=store_id,
            customer_id=None,
            currency="MXN",
            valid_from=None,
            valid_until=None,
        ),
        performed_by_id=None,
    )
    crud.create_price_list_item(
        db_session,
        store_list.id,
        schemas.PriceListItemCreate(
            device_id=device_id,
            price=Decimal("190.00"),
            discount_percentage=None,
            notes="Precio de sucursal",
        ),
        performed_by_id=None,
    )

    customer_list = crud.create_price_list(
        db_session,
        schemas.PriceListCreate(
            name="Cliente",
            description=None,
            is_active=True,
            store_id=None,
            customer_id=customer_id,
            currency="MXN",
            valid_from=None,
            valid_until=None,
        ),
        performed_by_id=None,
    )
    crud.create_price_list_item(
        db_session,
        customer_list.id,
        schemas.PriceListItemCreate(
            device_id=device_id,
            price=Decimal("185.00"),
            discount_percentage=Decimal("5"),
            notes="Cliente preferente",
        ),
        performed_by_id=None,
    )

    targeted_list = crud.create_price_list(
        db_session,
        schemas.PriceListCreate(
            name="Acuerdo",
            description=None,
            is_active=True,
            store_id=store_id,
            customer_id=customer_id,
            currency="MXN",
            valid_from=None,
            valid_until=None,
        ),
        performed_by_id=None,
    )
    crud.create_price_list_item(
        db_session,
        targeted_list.id,
        schemas.PriceListItemCreate(
            device_id=device_id,
            price=Decimal("170.00"),
            discount_percentage=Decimal("10"),
            notes="Acuerdo especial",
        ),
        performed_by_id=None,
    )

    resolution = pricing.resolve_device_price(
        db_session,
        device_id=device_id,
        store_id=store_id,
        customer_id=customer_id,
        reference_date=date.today(),
    )

    assert resolution is not None
    assert resolution.price_list_id == targeted_list.id
    assert resolution.scope == "store_customer"
    assert resolution.base_price == Decimal("170.00")
    assert resolution.discount_percentage == Decimal("10.00")
    assert resolution.final_price == Decimal("153.00")
    assert resolution.currency == "MXN"


def test_resolve_device_price_fallback(db_session):
    store_id = _create_store(db_session)
    device_id = _create_device(db_session, store_id)

    resolution = pricing.resolve_device_price(
        db_session,
        device_id=device_id,
        store_id=store_id,
        reference_date=date.today(),
        default_price=Decimal("125.55"),
        default_currency="usd",
    )

    assert resolution is not None
    assert resolution.price_list_id is None
    assert resolution.scope == "fallback"
    assert resolution.source == "fallback"
    assert resolution.currency == "USD"
    assert resolution.final_price == Decimal("125.55")
    assert resolution.discount_percentage is None
