from __future__ import annotations

from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "returns_admin",
        "password": "Retornos123*",
        "full_name": "Operador Devoluciones",
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


def test_returns_overview_includes_reasons(client, db_session):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Auditoría", "location": "MX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "RET-001",
            "name": "Lector Inventario",
            "quantity": 0,
            "unit_price": 120.0,
            "costo_unitario": 80.0,
            "margen_porcentaje": 20.0,
        },
        headers=auth_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    purchase_payload = {
        "store_id": store_id,
        "supplier": "Proveedor Central",
        "items": [{"device_id": device_id, "quantity_ordered": 5, "unit_cost": 90.0}],
    }
    purchase_response = client.post(
        "/purchases",
        json=purchase_payload,
        headers={**auth_headers, "X-Reason": "Planeación inventario"},
    )
    assert purchase_response.status_code == status.HTTP_201_CREATED
    order_id = purchase_response.json()["id"]

    receive_payload = {"items": [{"device_id": device_id, "quantity": 5}]}
    receive_response = client.post(
        f"/purchases/{order_id}/receive",
        json=receive_payload,
        headers={**auth_headers, "X-Reason": "Recepción inicial"},
    )
    assert receive_response.status_code == status.HTTP_200_OK

    purchase_return_payload = {
        "device_id": device_id,
        "quantity": 2,
        "reason": "Proveedor defectuoso",
    }
    purchase_return_response = client.post(
        f"/purchases/{order_id}/returns",
        json=purchase_return_payload,
        headers={**auth_headers, "X-Reason": "Devolución a proveedor"},
    )
    assert purchase_return_response.status_code == status.HTTP_200_OK

    sale_payload = {
        "store_id": store_id,
        "payment_method": "EFECTIVO",
        "items": [{"device_id": device_id, "quantity": 2}],
    }
    sale_response = client.post(
        "/sales",
        json=sale_payload,
        headers={**auth_headers, "X-Reason": "Venta mostrador"},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale_id = sale_response.json()["id"]

    sale_return_payload = {
        "sale_id": sale_id,
        "items": [
            {"device_id": device_id, "quantity": 1, "reason": "Cliente arrepentido"},
        ],
    }
    sale_return_response = client.post(
        "/sales/returns",
        json=sale_return_payload,
        headers={**auth_headers, "X-Reason": "Reingreso cliente"},
    )
    assert sale_return_response.status_code == status.HTTP_200_OK

    try:
        returns_response = client.get(
            "/returns",
            params={"store_id": store_id, "limit": 10},
            headers=auth_headers,
        )
        assert returns_response.status_code == status.HTTP_200_OK
        payload = returns_response.json()

        assert payload["totals"]["total"] == 2
        assert payload["totals"]["sales"] == 1
        assert payload["totals"]["purchases"] == 1

        reasons_by_type = {entry["type"]: entry["reason"] for entry in payload["items"]}
        assert reasons_by_type["sale"] == "Cliente arrepentido"
        assert reasons_by_type["purchase"] == "Proveedor defectuoso"

        processed = next(
            (entry for entry in payload["items"] if entry["type"] == "sale"),
            None,
        )
        assert processed is not None
        assert processed["processed_by_id"] == user_id
        assert "Venta #" in processed["reference_label"]
    finally:
        settings.enable_purchases_sales = original_flag
