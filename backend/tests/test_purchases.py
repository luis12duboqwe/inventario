from decimal import Decimal

from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "compras_admin",
        "password": "Compras123*",
        "full_name": "Compras Admin",
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

    user = db_session.execute(
        select(models.User).where(models.User.username == payload["username"])
    ).scalar_one()
    return token, user.id


def test_purchase_receipt_and_return_flow(client, db_session):
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Compras Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SKU-COMP-001",
        "name": "Smartphone corporativo",
        "quantity": 10,
        "unit_price": 1500.0,
        "costo_unitario": 1000.0,
        "margen_porcentaje": 15.0,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    order_payload = {
        "store_id": store_id,
        "supplier": "Proveedor Mayorista",
        "items": [
            {"device_id": device_id, "quantity_ordered": 10, "unit_cost": 850.0},
        ],
    }
    order_response = client.post("/purchases", json=order_payload, headers=auth_headers)
    assert order_response.status_code == status.HTTP_201_CREATED
    order_id = order_response.json()["id"]

    partial_receive = client.post(
        f"/purchases/{order_id}/receive",
        json={"items": [{"device_id": device_id, "quantity": 5}]},
        headers={**auth_headers, "X-Reason": "Recepcion parcial"},
    )
    assert partial_receive.status_code == status.HTTP_200_OK
    partial_data = partial_receive.json()
    assert partial_data["status"] == "PARCIAL"

    devices_after_partial = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    assert devices_after_partial.status_code == status.HTTP_200_OK
    stored_device = next(item for item in devices_after_partial.json() if item["id"] == device_id)
    assert stored_device["quantity"] == 15
    assert Decimal(str(stored_device["costo_unitario"])) == Decimal("950.00")

    complete_receive = client.post(
        f"/purchases/{order_id}/receive",
        json={"items": [{"device_id": device_id, "quantity": 5}]},
        headers={**auth_headers, "X-Reason": "Recepcion final"},
    )
    assert complete_receive.status_code == status.HTTP_200_OK
    assert complete_receive.json()["status"] == "COMPLETADA"

    return_response = client.post(
        f"/purchases/{order_id}/returns",
        json={"device_id": device_id, "quantity": 2, "reason": "Equipo danado"},
        headers={**auth_headers, "X-Reason": "Devolucion proveedor"},
    )
    assert return_response.status_code == status.HTTP_200_OK

    inventory_after_return = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    assert inventory_after_return.status_code == status.HTTP_200_OK
    device_post_return = next(item for item in inventory_after_return.json() if item["id"] == device_id)
    assert device_post_return["quantity"] == 18

    settings.enable_purchases_sales = False
