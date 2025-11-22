from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_operator(client, db_session):
    payload = {
        "username": "rma_admin",
        "password": "RmaAdmin123*",
        "full_name": "Operador RMA",
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


def _auth_headers(token: str, reason: str = "Gestión RMA extendida") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Reason": reason}


def test_rma_lifecycle_with_links(client, db_session):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token, user_id = _bootstrap_operator(client, db_session)
        auth_headers = {"Authorization": f"Bearer {token}"}
        reason_headers = _auth_headers(token)

        store_response = client.post(
            "/stores",
            json={
                "name": "Sucursal RMA",
                "location": "HN",
                "timezone": "America/Tegucigalpa",
            },
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "RMA-01",
                "name": "Tablet Corporativa",
                "quantity": 10,
                "unit_price": 150.0,
                "costo_unitario": 90.0,
                "margen_porcentaje": 20.0,
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        sale_payload = {
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 2}],
        }
        sale_response = client.post(
            "/sales",
            json=sale_payload,
            headers=reason_headers,
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["id"]

        sale_return_payload = {
            "sale_id": sale_id,
            "items": [
                {
                    "device_id": device_id,
                    "quantity": 1,
                    "reason": "Falla intermitente",
                    "disposition": "reparacion",
                }
            ],
        }
        sale_return_response = client.post(
            "/sales/returns",
            json=sale_return_payload,
            headers=reason_headers,
        )
        assert sale_return_response.status_code == status.HTTP_200_OK
        sale_return_body = sale_return_response.json()[0]
        sale_return_id = sale_return_body["id"]

        replacement_sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "payment_method": "EFECTIVO",
                "items": [{"device_id": device_id, "quantity": 1}],
            },
            headers=reason_headers,
        )
        assert replacement_sale_response.status_code == status.HTTP_201_CREATED
        replacement_sale_id = replacement_sale_response.json()["id"]

        customer_response = client.post(
            "/customers",
            json={"name": "Cliente RMA", "phone": "555-222-3333"},
            headers=reason_headers,
        )
        assert customer_response.status_code == status.HTTP_201_CREATED
        customer_id = customer_response.json()["id"]

        repair_payload = {
            "store_id": store_id,
            "customer_id": customer_id,
            "customer_contact": "+504 9999 0000",
            "technician_name": "Técnico RMA",
            "damage_type": "Pantalla",
            "diagnosis": "Evaluar daño",
            "device_model": "Tablet Corporativa",
            "imei": "123456789012345",
            "device_description": "Equipo en revisión",
            "labor_cost": 80.0,
            "parts": [
                {
                    "device_id": device_id,
                    "quantity": 1,
                    "unit_cost": 30.0,
                    "source": "STOCK",
                }
            ],
        }
        repair_response = client.post(
            "/repairs",
            json=repair_payload,
            headers=reason_headers,
        )
        assert repair_response.status_code == status.HTTP_201_CREATED
        repair_order_id = repair_response.json()["id"]

        rma_create_response = client.post(
            "/returns/rma",
            json={
                "sale_return_id": sale_return_id,
                "disposition": "reparacion",
                "notes": "Ingreso RMA por falla",
                "replacement_sale_id": replacement_sale_id,
            },
            headers=reason_headers,
        )
        assert rma_create_response.status_code == status.HTTP_200_OK
        rma_body = rma_create_response.json()
        assert rma_body["status"] == "PENDIENTE"
        assert rma_body["sale_return_id"] == sale_return_id
        assert rma_body["replacement_sale_id"] == replacement_sale_id
        assert len(rma_body["history"]) == 1
        assert rma_body["history"][0]["status"] == "PENDIENTE"

        rma_id = rma_body["id"]

        authorize_response = client.post(
            f"/returns/rma/{rma_id}/authorize",
            json={
                "disposition": "reparacion",
                "notes": "Autorizada para revisión",
            },
            headers=reason_headers,
        )
        assert authorize_response.status_code == status.HTTP_200_OK
        authorize_body = authorize_response.json()
        assert authorize_body["status"] == "AUTORIZADA"
        assert authorize_body["notes"] == "Autorizada para revisión"

        process_response = client.post(
            f"/returns/rma/{rma_id}/process",
            json={
                "disposition": "reparacion",
                "notes": "Asignada a técnico",
                "repair_order_id": repair_order_id,
                "replacement_sale_id": replacement_sale_id,
            },
            headers=reason_headers,
        )
        assert process_response.status_code == status.HTTP_200_OK
        process_body = process_response.json()
        assert process_body["status"] == "EN_PROCESO"
        assert process_body["repair_order_id"] == repair_order_id

        close_response = client.post(
            f"/returns/rma/{rma_id}/close",
            json={
                "disposition": "reparacion",
                "notes": "Equipo resuelto",
                "repair_order_id": repair_order_id,
                "replacement_sale_id": replacement_sale_id,
            },
            headers=reason_headers,
        )
        assert close_response.status_code == status.HTTP_200_OK
        close_body = close_response.json()
        assert close_body["status"] == "CERRADA"
        assert close_body["history"][-1]["message"] == "Equipo resuelto"
        assert len(close_body["history"]) == 4

        detail_response = client.get(
            f"/returns/rma/{rma_id}",
            headers=auth_headers,
        )
        assert detail_response.status_code == status.HTTP_200_OK
        detail_body = detail_response.json()
        statuses = [event["status"] for event in detail_body["history"]]
        assert statuses == ["PENDIENTE", "AUTORIZADA", "EN_PROCESO", "CERRADA"]
        assert detail_body["store_id"] == store_id
        assert detail_body["device_id"] == device_id
        assert detail_body["history"][0]["created_by_id"] == user_id
    finally:
        settings.enable_purchases_sales = original_flag
