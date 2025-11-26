from decimal import Decimal

from backend.app import crud, models, schemas


def _create_store(db_session, *, name: str, code: str) -> models.Store:
    store = models.Store(name=name, code=code, timezone="UTC")
    db_session.add(store)
    db_session.flush()
    return store


def _create_device(db_session, store: models.Store, *, sku: str, quantity: int) -> models.Device:
    device = models.Device(
        store_id=store.id,
        sku=sku,
        name="Equipo Demo",
        quantity=quantity,
        unit_price=Decimal("1200"),
        costo_unitario=Decimal("800"),
        categoria="Telefonía",
    )
    db_session.add(device)
    db_session.flush()
    return device


def _create_user(db_session, *, username: str) -> models.User:
    user = models.User(
        username=username,
        full_name="Usuario Transferencias",
        password_hash="hashed-password",
        rol="ADMIN",
        estado="ACTIVO",
    )
    db_session.add(user)
    db_session.flush()
    return user


def _grant_transfer_memberships(db_session, user: models.User, origin: models.Store, destination: models.Store) -> None:
    origin_membership = models.StoreMembership(
        user_id=user.id,
        store_id=origin.id,
        can_create_transfer=True,
        can_receive_transfer=False,
    )
    destination_membership = models.StoreMembership(
        user_id=user.id,
        store_id=destination.id,
        can_create_transfer=False,
        can_receive_transfer=True,
    )
    db_session.add_all([origin_membership, destination_membership])
    db_session.flush()


def test_transfer_dispatch_and_receive_moves_stock(db_session):
    origin = _create_store(db_session, name="Sucursal Test A", code="TR-A")
    destination = _create_store(db_session, name="Sucursal Test B", code="TR-B")
    device = _create_device(db_session, origin, sku="SKU-TX-01", quantity=5)
    user = _create_user(db_session, username="transfer-user@test.local")
    _grant_transfer_memberships(db_session, user, origin, destination)

    order_payload = schemas.TransferOrderCreate(
        origin_store_id=origin.id,
        destination_store_id=destination.id,
        reason="Envio inicial",
        items=[
            schemas.TransferOrderItemCreate(
                device_id=device.id,
                quantity=2,
                reservation_id=None,
            )
        ],
    )
    order = crud.create_transfer_order(
        db_session,
        order_payload,
        requested_by_id=user.id,
    )

    dispatched = crud.dispatch_transfer_order(
        db_session,
        order.id,
        performed_by_id=user.id,
        reason="Despacho programado",
    )
    db_session.refresh(device)

    assert dispatched.status == models.TransferStatus.EN_TRANSITO
    assert device.quantity == 3

    reception_items = [
        schemas.TransferReceptionItem(
            item_id=dispatched.items[0].id,
            received_quantity=2,
        )
    ]
    received = crud.receive_transfer_order(
        db_session,
        dispatched.id,
        performed_by_id=user.id,
        reason="Recepción confirmada",
        items=reception_items,
    )

    db_session.refresh(device)
    destination_device = (
        db_session.query(models.Device)
        .filter(models.Device.store_id == destination.id, models.Device.sku == device.sku)
        .first()
    )

    assert received.status == models.TransferStatus.RECIBIDA
    assert received.items[0].dispatched_quantity == 2
    assert received.items[0].received_quantity == 2
    assert device.quantity == 3
    assert destination_device is not None
    assert destination_device.quantity == 2


def test_transfer_rejection_restores_stock(db_session):
    origin = _create_store(db_session, name="Sucursal Test C", code="TR-C")
    destination = _create_store(db_session, name="Sucursal Test D", code="TR-D")
    device = _create_device(db_session, origin, sku="SKU-TX-02", quantity=3)
    user = _create_user(db_session, username="transfer-reject@test.local")
    _grant_transfer_memberships(db_session, user, origin, destination)

    order_payload = schemas.TransferOrderCreate(
        origin_store_id=origin.id,
        destination_store_id=destination.id,
        reason="Envio rechazable",
        items=[
            schemas.TransferOrderItemCreate(
                device_id=device.id,
                quantity=2,
                reservation_id=None,
            )
        ],
    )
    order = crud.create_transfer_order(
        db_session,
        order_payload,
        requested_by_id=user.id,
    )

    dispatched = crud.dispatch_transfer_order(
        db_session,
        order.id,
        performed_by_id=user.id,
        reason="Salida a destino",
    )
    db_session.refresh(device)

    assert dispatched.status == models.TransferStatus.EN_TRANSITO
    assert device.quantity == 1

    rejected = crud.reject_transfer_order(
        db_session,
        dispatched.id,
        performed_by_id=user.id,
        reason="Daño en tránsito",
    )
    db_session.refresh(device)

    destination_devices = (
        db_session.query(models.Device)
        .filter(models.Device.store_id == destination.id, models.Device.sku == device.sku)
        .all()
    )

    assert rejected.status == models.TransferStatus.RECHAZADA
    assert rejected.items[0].received_quantity == 0
    assert device.quantity == 3
    assert not destination_devices or destination_devices[0].quantity == 0
