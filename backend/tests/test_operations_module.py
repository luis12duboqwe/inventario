"""Pruebas del módulo Operaciones para plantillas, importaciones e historial."""
from __future__ import annotations

from typing import Tuple, Any, Iterable

from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _extract_items(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    return payload["items"]


def _bootstrap_admin(client, db_session) -> Tuple[str, int]:
    payload = {
        "username": "operaciones_admin",
        "password": "Operaciones123*",
        "full_name": "Operaciones Admin",
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


def _create_store(client, headers) -> int:
    response = client.post(
        "/stores",
        json={
            "name": "Operaciones Centro",
            "location": "CDMX",
            "timezone": "America/Mexico_City",
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def _create_device(client, store_id: int, headers) -> int:
    response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "OPS-001",
            "name": "Equipo de prueba operaciones",
            "quantity": 25,
            "unit_price": 1299.0,
            "costo_unitario": 980.0,
            "margen_porcentaje": 15.0,
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def test_purchase_import_from_csv_creates_orders(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token, user_id = _bootstrap_admin(client, db_session)
        headers = {"Authorization": f"Bearer {token}", "X-Reason": "Carga CSV masiva"}

        store_id = _create_store(client, headers)
        device_id = _create_device(client, store_id, headers)

        csv_content = (
            "store_id,supplier,device_id,quantity,unit_cost,notes\n"
            f"{store_id},Proveedor CSV,{device_id},3,845.50,Notas iniciales\n"
        )

        response = client.post(
            "/purchases/import",
            headers=headers,
            files={"file": ("ordenes.csv", csv_content, "text/csv")},
        )
        assert response.status_code == status.HTTP_201_CREATED
        payload = response.json()

        assert payload["imported"] == 1
        assert payload["errors"] == []
        assert len(payload["orders"]) == 1

        order = payload["orders"][0]
        assert order["store_id"] == store_id
        assert order["supplier"] == "Proveedor CSV"
        assert order["created_by_id"] == user_id
        assert "Importación CSV: Carga CSV masiva" in (order["notes"] or "")
        assert order["items"][0]["quantity_ordered"] == 3
        assert order["items"][0]["unit_cost"] == 845.5
    finally:
        settings.enable_purchases_sales = previous_flag


def test_recurring_order_flow_creates_purchase(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token, user_id = _bootstrap_admin(client, db_session)
        headers = {"Authorization": f"Bearer {token}", "X-Reason": "Plantilla operativa"}

        store_id = _create_store(client, headers)
        device_id = _create_device(client, store_id, headers)

        template_payload = {
            "name": "Reabasto semanal",
            "description": "Plantilla automática de compras",
            "order_type": "purchase",
            "payload": {
                "store_id": store_id,
                "supplier": "Mayorista Plantilla",
                "notes": "Reabasto programado",
                "items": [
                    {
                        "device_id": device_id,
                        "quantity_ordered": 4,
                        "unit_cost": 765.0,
                    }
                ],
            },
        }

        create_response = client.post(
            "/operations/recurring-orders",
            json=template_payload,
            headers=headers,
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        template_id = create_response.json()["id"]
        assert create_response.json()["created_by_id"] == user_id

        list_response = client.get(
            "/operations/recurring-orders",
            params={"order_type": "purchase", "limit": 200, "offset": 0},
            headers=headers,
        )
        assert list_response.status_code == status.HTTP_200_OK
        template_payload = _extract_items(list_response.json())
        template_ids = {item["id"] for item in template_payload}
        assert template_id in template_ids

        execute_response = client.post(
            f"/operations/recurring-orders/{template_id}/execute",
            headers=headers,
        )
        assert execute_response.status_code == status.HTTP_200_OK
        execution = execute_response.json()
        assert execution["template_id"] == template_id
        assert execution["order_type"] == "purchase"
        assert execution["store_id"] == store_id

        purchases_response = client.get(
            "/purchases",
            params={"store_id": store_id, "limit": 200, "offset": 0},
            headers=headers,
        )
        assert purchases_response.status_code == status.HTTP_200_OK
        purchase_payload = _extract_items(purchases_response.json())
        purchase_ids = {order["id"] for order in purchase_payload}
        assert execution["reference_id"] in purchase_ids
    finally:
        settings.enable_purchases_sales = previous_flag


def test_operations_history_endpoint_returns_recent_records(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token, user_id = _bootstrap_admin(client, db_session)
        headers = {"Authorization": f"Bearer {token}", "X-Reason": "Flujo operaciones"}

        store_id = _create_store(client, headers)
        device_id = _create_device(client, store_id, headers)

        purchase_payload = {
            "store_id": store_id,
            "supplier": "Proveedor Historial",
            "items": [
                {"device_id": device_id, "quantity_ordered": 5, "unit_cost": 812.0}
            ],
        }
        purchase_response = client.post(
            "/purchases",
            json=purchase_payload,
            headers=headers,
        )
        assert purchase_response.status_code == status.HTTP_201_CREATED
        purchase_id = purchase_response.json()["id"]

        sale_payload = {
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [
                {
                    "device_id": device_id,
                    "quantity": 2,
                }
            ],
        }
        sale_response = client.post(
            "/sales",
            json=sale_payload,
            headers=headers,
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["id"]

        history_response = client.get(
            "/operations/history",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 200, "offset": 0},
        )
        assert history_response.status_code == status.HTTP_200_OK
        history = history_response.json()

        record_types = {record["operation_type"] for record in history["records"]}
        assert "purchase" in record_types
        assert "sale" in record_types

        assert any(record["reference"] == f"PO-{purchase_id}" for record in history["records"])
        assert any(record["reference"] == f"VNT-{sale_id}" for record in history["records"])

        technician_ids = {tech["id"] for tech in history["technicians"]}
        assert user_id in technician_ids

        filtered_response = client.get(
            "/operations/history",
            params={"technician_id": user_id, "limit": 200, "offset": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert filtered_response.status_code == status.HTTP_200_OK
        filtered = filtered_response.json()
        assert all(record["technician_id"] == user_id for record in filtered["records"])
    finally:
        settings.enable_purchases_sales = previous_flag

