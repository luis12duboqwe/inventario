from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import status

from backend.app import crud, models, schemas
from backend.app.core.roles import ADMIN


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "reservas_admin",
        "password": "ClaveSegura123",
        "full_name": "Reservas Admin",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    token = token_response.json()["access_token"]
    sanitized_reason = "Gestión reservas pruebas".encode("ascii", "ignore").decode("ascii")
    return {"Authorization": f"Bearer {token}", "X-Reason": sanitized_reason}


def _create_store(db_session, *, name: str = "Sucursal Centro", code: str = "SUC-001") -> models.Store:
    store = models.Store(name=name, code=code, timezone="UTC")
    db_session.add(store)
    db_session.flush()
    return store


def _create_device(
    db_session,
    store: models.Store,
    *,
    sku: str = "SKU-TEST-001",
    quantity: int = 5,
    imei: str | None = None,
) -> models.Device:
    device = models.Device(
        store_id=store.id,
        sku=sku,
        name="Dispositivo Demo",
        quantity=quantity,
        unit_price=Decimal("1500"),
        costo_unitario=Decimal("900"),
        categoria="Telefonía",
        imei=imei,
    )
    db_session.add(device)
    db_session.flush()
    return device


def _create_user(db_session, *, username: str = "usuario@demo.local") -> models.User:
    user = models.User(
        username=username,
        full_name="Usuario Demo",
        password_hash="hashed-password",
        rol="ADMIN",
        estado="ACTIVO",
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_inventory_reservation_endpoints_flow(client, db_session):
    store = _create_store(db_session)
    device = _create_device(db_session, store)

    headers = _auth_headers(client)
    expiration = (datetime.utcnow() + timedelta(hours=2)).replace(microsecond=0).isoformat()

    create_response = client.post(
        "/inventory/reservations",
        json={
            "store_id": store.id,
            "device_id": device.id,
            "quantity": 2,
            "expires_at": expiration,
        },
        headers=headers,
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    created = create_response.json()
    assert created["status"] == "RESERVADO"
    assert created["reason"] == headers["X-Reason"]

    list_response = client.get("/inventory/reservations", headers=headers)
    assert list_response.status_code == status.HTTP_200_OK
    items = list_response.json()["items"]
    assert any(item["id"] == created["id"] for item in items)

    new_expiration = (datetime.utcnow() + timedelta(hours=4)).replace(microsecond=0).isoformat()
    headers["X-Reason"] = "Renovar reserva programada"
    renew_response = client.put(
        f"/inventory/reservations/{created['id']}/renew",
        json={"expires_at": new_expiration},
        headers=headers,
    )
    assert renew_response.status_code == status.HTTP_200_OK
    renewed = renew_response.json()
    assert renewed["expires_at"].startswith(new_expiration[:16])

    headers["X-Reason"] = "Cancelar reserva pruebas"
    cancel_response = client.post(
        f"/inventory/reservations/{created['id']}/cancel",
        headers=headers,
    )
    assert cancel_response.status_code == status.HTTP_200_OK
    cancelled = cancel_response.json()
    assert cancelled["status"] == "CANCELADO"
    assert cancelled["quantity"] == 0

    stored = crud.get_inventory_reservation(db_session, created["id"])
    assert stored.status == models.InventoryState.CANCELADO
    assert stored.resolution_reason == headers["X-Reason"]


def test_expire_reservations_releases_serial_device(db_session):
    store = _create_store(db_session)
    device = _create_device(db_session, store, quantity=1, imei="123456789012345")
    user = _create_user(db_session)

    reservation = crud.create_reservation(
        db_session,
        store_id=store.id,
        device_id=device.id,
        quantity=1,
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        reserved_by_id=user.id,
        reason="Bloqueo preventivo",
    )

    reservation.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.flush()

    expired_count = crud.expire_reservations(db_session)
    assert expired_count == 1
    db_session.flush()

    updated_reservation = crud.get_inventory_reservation(db_session, reservation.id)
    db_session.refresh(device)

    assert updated_reservation.status == models.InventoryState.EXPIRADO
    assert updated_reservation.quantity == 0
    assert device.estado == "disponible"


def test_reservation_consumed_on_sale(db_session):
    store = _create_store(db_session)
    device = _create_device(db_session, store, quantity=1, imei="987654321098765")
    user = _create_user(db_session)

    reservation = crud.create_reservation(
        db_session,
        store_id=store.id,
        device_id=device.id,
        quantity=1,
        expires_at=datetime.utcnow() + timedelta(hours=1),
        reserved_by_id=user.id,
        reason="Reserva venta POS",
    )

    sale_payload = schemas.SaleCreate(
        store_id=store.id,
        customer_id=None,
        customer_name=None,
        payment_method=models.PaymentMethod.EFECTIVO,
        discount_percent=Decimal("0"),
        notes=None,
        items=[
            schemas.SaleItemCreate(
                device_id=device.id,
                quantity=1,
                discount_percent=Decimal("0"),
                reservation_id=reservation.id,
            )
        ],
    )

    sale = crud.create_sale(
        db_session,
        sale_payload,
        performed_by_id=user.id,
        tax_rate=Decimal("0"),
        reason="Venta con reserva",
    )

    updated_reservation = crud.get_inventory_reservation(db_session, reservation.id)
    db_session.refresh(device)

    assert sale.items[0].reservation_id == reservation.id
    assert updated_reservation.status == models.InventoryState.CONSUMIDO
    assert updated_reservation.consumed_at is not None
    assert updated_reservation.quantity == 0
    assert device.estado == "vendido"


def test_reservation_consumed_on_transfer(db_session):
    origin = _create_store(db_session, name="Sucursal Norte", code="SUC-010")
    destination = _create_store(db_session, name="Sucursal Sur", code="SUC-020")
    device = _create_device(db_session, origin, sku="SKU-TR-001", quantity=4)
    user = _create_user(db_session, username="transfer@demo.local")

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

    reservation = crud.create_reservation(
        db_session,
        store_id=origin.id,
        device_id=device.id,
        quantity=2,
        expires_at=datetime.utcnow() + timedelta(hours=2),
        reserved_by_id=user.id,
        reason="Reserva transferencia",
    )

    order_payload = schemas.TransferOrderCreate(
        origin_store_id=origin.id,
        destination_store_id=destination.id,
        reason="Transferencia con reserva",
        items=[
            schemas.TransferOrderItemCreate(
                device_id=device.id,
                quantity=2,
                reservation_id=reservation.id,
            )
        ],
    )
    order = crud.create_transfer_order(
        db_session,
        order_payload,
        requested_by_id=user.id,
    )

    received = crud.receive_transfer_order(
        db_session,
        order.id,
        performed_by_id=user.id,
        reason="Recepción programada",
    )

    updated_reservation = crud.get_inventory_reservation(db_session, reservation.id)
    db_session.refresh(device)

    assert received.status == models.TransferStatus.RECIBIDA
    assert updated_reservation.status == models.InventoryState.CONSUMIDO
    assert updated_reservation.reference_type == "transfer_order"
    assert updated_reservation.reference_id == str(order.id)

    origin_device = crud.get_device(db_session, origin.id, device.id)
    assert origin_device.quantity == 2

    destination_devices = (
        db_session.query(models.Device)
        .filter(models.Device.store_id == destination.id, models.Device.sku == device.sku)
        .all()
    )
    assert destination_devices
    assert destination_devices[0].quantity == 2
