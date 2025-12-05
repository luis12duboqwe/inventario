# // [PACK29-*] Cobertura de endpoints de reportes de ventas
"""Pruebas de reportes de ventas."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


# // [PACK29-*] Utilidad para registrar un administrador y obtener token
def _bootstrap_admin(client) -> str:
    payload = {
        "username": "reports_admin",
        "password": "Reports123*",
        "full_name": "Reports Admin",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def test_reports_sales_summary_requires_reason(client):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        missing_reason_headers = {
            "Authorization": f"Bearer {token}", "X-Reason": ""}
        response = client.get("/reports/sales/summary",
                              headers=missing_reason_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        valid_headers = {
            "Authorization": f"Bearer {token}",
            "X-Reason": "Consulta reportes QA",
        }
        ok_response = client.get(
            "/reports/sales/summary", headers=valid_headers)
        assert ok_response.status_code != status.HTTP_400_BAD_REQUEST
    finally:
        settings.enable_purchases_sales = previous_flag


# // [PACK29-*] Verifica resumen, top de productos y cierre sugerido
def test_sales_reports_summary_products_and_cash_close(client, db_session: Session) -> None:
    previous_analytics_flag = settings.enable_analytics_adv
    previous_sales_flag = settings.enable_purchases_sales
    settings.enable_analytics_adv = True
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        headers = {"Authorization": f"Bearer {token}"}

        store_response = client.post(
            "/stores",
            json={"name": "Sucursal Centro", "location": "CDMX",
                  "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "REP-001",
                "name": "Router Empresarial",
                "quantity": 25,
                "unit_price": 150.0,
                "costo_unitario": 120.0,
                "margen_porcentaje": 25.0,
            },
            headers=headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        sale_headers = {**headers, "X-Reason": "Registro de venta de prueba"}
        sale_payload = {
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 3}],
        }
        first_sale_response = client.post(
            "/sales", json=sale_payload, headers=sale_headers)
        assert first_sale_response.status_code == status.HTTP_201_CREATED
        first_sale_id = first_sale_response.json()["id"]

        second_sale_response = client.post(
            "/sales",
            json={"store_id": store_id, "payment_method": "TARJETA",
                  "items": [{"device_id": device_id, "quantity": 2}]},
            headers=sale_headers,
        )
        assert second_sale_response.status_code == status.HTTP_201_CREATED
        second_sale_id = second_sale_response.json()["id"]

        report_date = date.today()
        first_sale_record = db_session.get(models.Sale, first_sale_id)
        second_sale_record = db_session.get(models.Sale, second_sale_id)
        assert first_sale_record is not None
        assert second_sale_record is not None
        base_datetime = datetime.combine(report_date, datetime.min.time())
        first_sale_record.created_at = base_datetime + timedelta(hours=9)
        second_sale_record.created_at = base_datetime + timedelta(hours=12)
        db_session.add_all([first_sale_record, second_sale_record])
        db_session.commit()

        return_payload = {
            "sale_id": first_sale_id,
            "items": [{"device_id": device_id, "quantity": 1, "reason": "Fallo en equipo"}],
        }
        return_headers = {**headers, "X-Reason": "Devolucion de prueba"}
        return_response = client.post(
            "/sales/returns", json=return_payload, headers=return_headers)
        assert return_response.status_code == status.HTTP_200_OK
        returns_json = return_response.json()
        assert len(returns_json) == 1
        return_record = db_session.get(
            models.SaleReturn, returns_json[0]["id"])
        assert return_record is not None
        return_record.created_at = base_datetime + timedelta(hours=15)
        db_session.add(return_record)
        db_session.commit()

        params = {
            "from": (report_date - timedelta(days=1)).isoformat(),
            "to": (report_date + timedelta(days=1)).isoformat(),
            "branchId": store_id,
        }

        summary_headers = {**headers, "X-Reason": "Reporte de ventas"}
        summary_response = client.get(
            "/reports/sales/summary", params=params, headers=summary_headers)
        assert summary_response.status_code == status.HTTP_200_OK
        summary = summary_response.json()
        assert summary["totalSales"] == pytest.approx(750.0)
        assert summary["totalOrders"] == 2
        assert summary["avgTicket"] == pytest.approx(375.0)
        assert summary["returnsCount"] == 1
        assert summary["net"] == pytest.approx(600.0)

        top_response = client.get(
            "/reports/sales/by-product", params={**params, "limit": 5}, headers=summary_headers)
        assert top_response.status_code == status.HTTP_200_OK
        products = top_response.json()
        assert len(products) == 1
        product_entry = products[0]
        assert product_entry["sku"] == "REP-001"
        assert product_entry["qty"] == 5
        assert product_entry["gross"] == pytest.approx(750.0)
        assert product_entry["net"] == pytest.approx(600.0)

        csv_response = client.get(
            "/reports/sales/by-product",
            params={**params, "limit": 5, "format": "csv"},
            headers=summary_headers,
        )
        assert csv_response.status_code == status.HTTP_200_OK
        assert "text/csv" in csv_response.headers["content-type"].lower()
        assert "REP-001" in csv_response.text

        cash_response = client.get(
            "/reports/cash-close",
            params={"date": report_date.isoformat(), "branchId": store_id},
            headers=summary_headers,
        )
        assert cash_response.status_code == status.HTTP_200_OK
        cash_report = cash_response.json()
        assert cash_report["opening"] == pytest.approx(0.0)
        assert cash_report["salesGross"] == pytest.approx(750.0)
        assert cash_report["refunds"] == pytest.approx(150.0)
        assert cash_report["closingSuggested"] == pytest.approx(600.0)
    finally:
        settings.enable_analytics_adv = previous_analytics_flag
        settings.enable_purchases_sales = previous_sales_flag


def test_sales_daily_report_default_payload(client) -> None:
    previous_analytics_flag = settings.enable_analytics_adv
    previous_sales_flag = settings.enable_purchases_sales
    settings.enable_analytics_adv = True
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reason": "Consulta reporte diario"
        }
        target_date = date.today().isoformat()

        response = client.get(
            "/reports/sales/daily",
            params={"date": target_date},
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["date"] == target_date
        assert payload["totals"]["gross"] == pytest.approx(0.0)

        csv_response = client.get(
            "/reports/sales/daily/export.csv",
            params={"date": target_date},
            headers=headers,
        )
        assert csv_response.status_code == status.HTTP_200_OK
        assert "text/csv" in csv_response.headers["content-type"].lower()
        assert target_date in csv_response.text
    finally:
        settings.enable_analytics_adv = previous_analytics_flag
        settings.enable_purchases_sales = previous_sales_flag
