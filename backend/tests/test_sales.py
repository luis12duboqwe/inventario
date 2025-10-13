from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "ventas_admin",
        "password": "Ventas123*",
        "full_name": "Ventas Admin",
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


def test_sale_and_return_flow(client, db_session):
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Ventas Norte", "location": "MX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SKU-VENTA-001",
        "name": "Tablet Pro",
        "quantity": 5,
        "unit_price": 500.0,
        "costo_unitario": 350.0,
        "margen_porcentaje": 20.0,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    sale_payload = {
        "store_id": store_id,
        "payment_method": "TARJETA",
        "discount_percent": 10.0,
        "items": [{"device_id": device_id, "quantity": 2}],
    }
    sale_response = client.post(
        "/sales",
        json=sale_payload,
        headers={**auth_headers, "X-Reason": "Venta mostrador"},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale_data = sale_response.json()
    assert sale_data["payment_method"] == "TARJETA"
    assert sale_data["total_amount"] == 900.0

    devices_after_sale = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    assert devices_after_sale.status_code == status.HTTP_200_OK
    device_after_sale = next(item for item in devices_after_sale.json() if item["id"] == device_id)
    assert device_after_sale["quantity"] == 3

    return_payload = {
        "sale_id": sale_data["id"],
        "items": [{"device_id": device_id, "quantity": 1, "reason": "Cliente arrepentido"}],
    }
    return_response = client.post(
        "/sales/returns",
        json=return_payload,
        headers={**auth_headers, "X-Reason": "Devolucion cliente"},
    )
    assert return_response.status_code == status.HTTP_200_OK
    assert len(return_response.json()) == 1

    devices_post_return = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    device_post_return = next(item for item in devices_post_return.json() if item["id"] == device_id)
    assert device_post_return["quantity"] == 4

    invalid_return = client.post(
        "/sales/returns",
        json={"sale_id": sale_data["id"], "items": [{"device_id": device_id, "quantity": 5, "reason": "Exceso"}]},
        headers={**auth_headers, "X-Reason": "Devolucion invalida"},
    )
    assert invalid_return.status_code == status.HTTP_409_CONFLICT

    settings.enable_purchases_sales = False
