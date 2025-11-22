from __future__ import annotations

from datetime import date, datetime

from fastapi import status

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN, OPERADOR


def _bootstrap_user(client, roles: list[str]) -> str:
    payload = {
        "username": f"reports_{roles[0].lower()}",
        "password": "Reports123*",
        "full_name": "Reports User",
        "roles": roles,
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def _create_store(client, headers) -> int:
    response = client.post(
        "/stores",
        json={"name": "Sucursal Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def _create_device(client, store_id: int, headers) -> int:
    payload = {
        "sku": "REP-100",
        "name": "Equipo Gerencial",
        "modelo": "Gadgets",
        "quantity": 8,
        "unit_price": 1200.0,
        "costo_unitario": 800.0,
        "margen_porcentaje": 25.0,
    }
    response = client.post(
        f"/stores/{store_id}/devices",
        json=payload,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def test_financial_report_json_and_exports(client, db_session):
    previous_analytics = settings.enable_analytics_adv
    previous_sales = settings.enable_purchases_sales
    settings.enable_analytics_adv = True
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_user(client, [ADMIN])
        headers = {"Authorization": f"Bearer {token}"}
        store_id = _create_store(client, headers)
        device_id = _create_device(client, store_id, headers)

        sale_headers = {**headers, "X-Reason": "Venta de prueba gerencial"}
        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "payment_method": "EFECTIVO",
                "items": [{"device_id": device_id, "quantity": 2}],
            },
            headers=sale_headers,
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["id"]

        sale_record = db_session.get(models.Sale, sale_id)
        assert sale_record is not None
        sale_record.created_at = datetime(2024, 1, 15, 10, 0)
        db_session.add(sale_record)
        db_session.commit()

        params = [
            ("store_ids", store_id),
            ("date_from", "2024-01-01"),
            ("date_to", "2024-01-31"),
        ]
        response = client.get("/reports/financial", params=params, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["totals"]["revenue"] > 0
        assert payload["profit_by_store"]
        assert payload["rotation"]
        assert payload["sales_by_category"]

        export_headers = {**headers, "X-Reason": "Exportar métricas financieras"}
        pdf_response = client.get(
            "/reports/financial",
            params=params + [("format", "pdf")],
            headers=export_headers,
        )
        assert pdf_response.status_code == status.HTTP_200_OK
        assert pdf_response.headers["content-type"].startswith("application/pdf")

        xlsx_response = client.get(
            "/reports/financial",
            params=params + [("format", "xlsx")],
            headers=export_headers,
        )
        assert xlsx_response.status_code == status.HTTP_200_OK
        assert "spreadsheetml" in xlsx_response.headers["content-type"]
    finally:
        settings.enable_analytics_adv = previous_analytics
        settings.enable_purchases_sales = previous_sales


def test_inventory_report_requires_manager_role(client):
    previous_analytics = settings.enable_analytics_adv
    settings.enable_analytics_adv = True
    try:
        token = _bootstrap_user(client, [OPERADOR])
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/reports/inventory", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        settings.enable_analytics_adv = previous_analytics


def test_inventory_report_category_breakdown(client, db_session):
    previous_analytics = settings.enable_analytics_adv
    previous_sales = settings.enable_purchases_sales
    settings.enable_analytics_adv = True
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_user(client, [ADMIN])
        headers = {"Authorization": f"Bearer {token}"}
        store_id = _create_store(client, headers)
        device_id = _create_device(client, store_id, headers)

        sale_headers = {**headers, "X-Reason": "Venta categoría gadgets"}
        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "payment_method": "TARJETA",
                "items": [{"device_id": device_id, "quantity": 1}],
            },
            headers=sale_headers,
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["id"]

        sale_record = db_session.get(models.Sale, sale_id)
        assert sale_record is not None
        sale_record.created_at = datetime(2024, 2, 10, 12, 0)
        db_session.add(sale_record)
        db_session.commit()

        params = [
            ("category", "Gadgets"),
            ("date_from", date(2024, 2, 1).isoformat()),
            ("date_to", date(2024, 2, 28).isoformat()),
        ]
        response = client.get("/reports/inventory", params=params, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        categories = {item["category"] for item in payload["sales_by_category"]}
        assert "Gadgets" in categories
        assert payload["sales_by_store"][0]["orders"] >= 1
        assert payload["rotation"][0]["sold_units"] >= 1
    finally:
        settings.enable_analytics_adv = previous_analytics
        settings.enable_purchases_sales = previous_sales
