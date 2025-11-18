from __future__ import annotations

import json
from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "suggestions_admin",
        "password": "Compras123*",
        "full_name": "Sugerencias Admin",
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


def test_purchase_suggestions_endpoint_returns_grouped_items(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, _ = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    try:
        store_response = client.post(
            "/stores",
            json={
                "name": "Sucursal Centro",
                "location": "CDMX",
                "timezone": "America/Mexico_City",
            },
            headers={**auth_headers, "X-Reason": "Alta sucursal"},
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SKU-SUG-001",
                "name": "Smartphone empresarial",
                "quantity": 12,
                "unit_price": 1500.0,
                "costo_unitario": 900.0,
                "margen_porcentaje": 15.0,
                "proveedor": "Tecno Global",
            },
            headers={**auth_headers, "X-Reason": "Alta dispositivo"},
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        vendor_response = client.post(
            "/purchases/vendors",
            json={"nombre": "Tecno Global"},
            headers={**auth_headers, "X-Reason": "Alta proveedor"},
        )
        assert vendor_response.status_code == status.HTTP_201_CREATED
        vendor_id = vendor_response.json()["id_proveedor"]

        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "payment_method": "EFECTIVO",
                "items": [{"device_id": device_id, "quantity": 9}],
            },
            headers={**auth_headers, "X-Reason": "Venta sugerencia"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED

        suggestions_response = client.get(
            "/purchases/suggestions",
            headers=auth_headers,
        )
        assert suggestions_response.status_code == status.HTTP_200_OK
        payload = suggestions_response.json()

        assert payload["minimum_stock"] >= 0
        assert payload["total_items"] >= 1
        assert payload["stores"], "Se esperaba al menos una sucursal con sugerencias"

        store_payload = payload["stores"][0]
        assert store_payload["store_id"] == store_id
        assert store_payload["items"]
        suggestion = store_payload["items"][0]
        assert suggestion["device_id"] == device_id
        assert suggestion["supplier_id"] == vendor_id
        assert suggestion["supplier_name"] == "Tecno Global"
        assert suggestion["average_daily_sales"] > 0
        assert suggestion["suggested_quantity"] > 0
        assert suggestion["reason"] in {"below_minimum", "projected_consumption"}
    finally:
        settings.enable_purchases_sales = previous_flag


def test_purchase_suggestions_create_order_logs_reason(client, db_session):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    try:
        store_response = client.post(
            "/stores",
            json={
                "name": "Sucursal Norte",
                "location": "Monterrey",
                "timezone": "America/Mexico_City",
            },
            headers={**auth_headers, "X-Reason": "Alta sucursal"},
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SKU-SUG-002",
                "name": "Tablet corporativa",
                "quantity": 10,
                "unit_price": 2400.0,
                "costo_unitario": 1400.0,
                "margen_porcentaje": 20.0,
                "proveedor": "Distribuciones Norte",
            },
            headers={**auth_headers, "X-Reason": "Alta dispositivo"},
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "payment_method": "EFECTIVO",
                "items": [{"device_id": device_id, "quantity": 7}],
            },
            headers={**auth_headers, "X-Reason": "Venta sugerencia"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED

        order_payload = {
            "store_id": store_id,
            "supplier": "Distribuciones Norte",
            "items": [
                {"device_id": device_id, "quantity_ordered": 4, "unit_cost": 1450.0},
            ],
        }
        reason = "Generar PO con sugerencia"

        order_response = client.post(
            "/purchases/suggestions/orders",
            json=order_payload,
            headers={**auth_headers, "X-Reason": reason},
        )
        assert order_response.status_code == status.HTTP_201_CREATED
        order_data = order_response.json()
        assert order_data["supplier"] == "Distribuciones Norte"
        assert order_data["store_id"] == store_id

        db_order = db_session.get(models.PurchaseOrder, order_data["id"])
        assert db_order is not None
        assert db_order.created_by_id == user_id

        log_entry = db_session.execute(
            select(models.AuditLog)
            .where(models.AuditLog.action == "purchase_order_generated_from_suggestion")
            .where(models.AuditLog.entity_id == str(db_order.id))
            .order_by(models.AuditLog.created_at.desc())
        ).scalars().first()
        assert log_entry is not None
        assert log_entry.performed_by_id == user_id

        details = json.loads(log_entry.details or "{}")
        assert details.get("reason") == reason
        assert details.get("source") == "purchase_suggestion"
        assert details.get("store_id") == store_id
    finally:
        settings.enable_purchases_sales = previous_flag
