from datetime import date, datetime, timedelta

from fastapi import status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.core.roles import ADMIN
from backend.app import models


def _bootstrap_admin(client):
    payload = {
        "username": "analytics_admin",
        "password": "Analytics123*",
        "full_name": "Analytics Admin",
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
    return token_response.json()["access_token"]


def test_advanced_analytics_endpoints(client, db_session: Session):
    previous_analytics = settings.enable_analytics_adv
    previous_sales = settings.enable_purchases_sales
    settings.enable_analytics_adv = True
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    store_resp = client.post(
        "/stores",
        json={"name": "Analitica Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_resp.status_code == status.HTTP_201_CREATED
    store_id = store_resp.json()["id"]

    store_resp_north = client.post(
        "/stores",
        json={"name": "Analitica Norte", "location": "MTY", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_resp_north.status_code == status.HTTP_201_CREATED
    store_north_id = store_resp_north.json()["id"]

    device_resp = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "ANL-001",
            "name": "Equipo Analitico",
            "quantity": 10,
            "unit_price": 1000.0,
            "costo_unitario": 700.0,
            "margen_porcentaje": 20.0,
            "fecha_compra": date(2024, 1, 1).isoformat(),
        },
        headers=headers,
    )
    assert device_resp.status_code == status.HTTP_201_CREATED
    device_id = device_resp.json()["id"]

    north_device_resp = client.post(
        f"/stores/{store_north_id}/devices",
        json={
            "sku": "ANL-002",
            "name": "Router Norte",
            "quantity": 6,
            "unit_price": 1200.0,
            "costo_unitario": 850.0,
            "margen_porcentaje": 25.0,
            "fecha_compra": date(2024, 2, 1).isoformat(),
        },
        headers=headers,
    )
    assert north_device_resp.status_code == status.HTTP_201_CREATED
    north_device_id = north_device_resp.json()["id"]

    sale_resp = client.post(
        "/sales",
        json={"store_id": store_id, "payment_method": "EFECTIVO", "items": [{"device_id": device_id, "quantity": 2}]},
        headers={**headers, "X-Reason": "Venta analitica"},
    )
    assert sale_resp.status_code == status.HTTP_201_CREATED
    sale_id = sale_resp.json()["id"]
    first_sale = db_session.get(models.Sale, sale_id)
    first_sale.created_at = datetime.utcnow() - timedelta(days=5)
    db_session.commit()

    sale_resp_followup = client.post(
        "/sales",
        json={
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 3}],
        },
        headers={**headers, "X-Reason": "Venta analitica 2"},
    )
    assert sale_resp_followup.status_code == status.HTTP_201_CREATED
    follow_sale = db_session.get(models.Sale, sale_resp_followup.json()["id"])
    follow_sale.created_at = datetime.utcnow() - timedelta(days=1)
    db_session.commit()

    sale_resp_north = client.post(
        "/sales",
        json={
            "store_id": store_north_id,
            "payment_method": "TARJETA",
            "items": [{"device_id": north_device_id, "quantity": 1}],
        },
        headers={**headers, "X-Reason": "Venta norte"},
    )
    assert sale_resp_north.status_code == status.HTTP_201_CREATED
    north_sale = db_session.get(models.Sale, sale_resp_north.json()["id"])
    north_sale.created_at = datetime.utcnow() - timedelta(days=3)
    db_session.commit()

    admin_user = db_session.query(models.User).filter_by(
        username="analytics_admin"
    ).first()
    assert admin_user is not None
    for index in range(4):
        db_session.add(
            models.SaleReturn(
                sale_id=sale_id,
                device_id=device_id,
                quantity=1,
                reason="Cliente insatisfecho",
                processed_by_id=admin_user.id,
                created_at=datetime.utcnow() - timedelta(days=index),
            )
        )
    db_session.commit()

    device_record = db_session.get(models.Device, device_id)
    device_record.quantity = 3
    db_session.commit()

    rotation_response = client.get("/reports/analytics/rotation", headers=headers)
    assert rotation_response.status_code == status.HTTP_200_OK
    rotation_items = rotation_response.json()["items"]
    assert any(item["device_id"] == device_id for item in rotation_items)

    rotation_filtered = client.get(
        f"/reports/analytics/rotation?store_ids={store_id}",
        headers=headers,
    )
    assert rotation_filtered.status_code == status.HTTP_200_OK
    assert all(item["store_id"] == store_id for item in rotation_filtered.json()["items"])

    aging_response = client.get("/reports/analytics/aging", headers=headers)
    assert aging_response.status_code == status.HTTP_200_OK
    assert any(item["device_id"] == device_id for item in aging_response.json()["items"])

    forecast_response = client.get("/reports/analytics/stockout_forecast", headers=headers)
    assert forecast_response.status_code == status.HTTP_200_OK
    assert any(item["device_id"] == device_id for item in forecast_response.json()["items"])
    for item in forecast_response.json()["items"]:
        assert "trend" in item
        assert "confidence" in item
        assert "alert_level" in item

    comparative_response = client.get("/reports/analytics/comparative", headers=headers)
    assert comparative_response.status_code == status.HTTP_200_OK
    comparative_items = comparative_response.json()["items"]
    assert any(item["store_id"] == store_id for item in comparative_items)

    profit_response = client.get("/reports/analytics/profit_margin", headers=headers)
    assert profit_response.status_code == status.HTTP_200_OK
    profit_items = profit_response.json()["items"]
    assert any(item["store_id"] == store_id for item in profit_items)

    projection_response = client.get("/reports/analytics/sales_forecast", headers=headers)
    assert projection_response.status_code == status.HTTP_200_OK
    projection_items = projection_response.json()["items"]
    assert any(item["store_id"] == store_id for item in projection_items)
    for item in projection_items:
        assert "trend" in item
        assert "revenue_trend_score" in item

    forecast_response_store = client.get(
        "/reports/analytics/store_sales_forecast", headers=headers
    )
    assert forecast_response_store.status_code == status.HTTP_200_OK
    store_forecast_items = forecast_response_store.json()["items"]
    assert any(item["store_id"] == store_id for item in store_forecast_items)
    assert all("projected_revenue" in item for item in store_forecast_items)

    reorder_response = client.get(
        "/reports/analytics/reorder_suggestions", headers=headers
    )
    assert reorder_response.status_code == status.HTTP_200_OK
    reorder_items = reorder_response.json()["items"]
    assert any(item["store_id"] == store_id for item in reorder_items)
    assert all(item["recommended_order"] >= 0 for item in reorder_items)

    anomalies_response = client.get(
        "/reports/analytics/return_anomalies", headers=headers
    )
    assert anomalies_response.status_code == status.HTTP_200_OK
    anomalies = anomalies_response.json()["items"]
    assert any(item["is_anomalous"] for item in anomalies)

    download_headers = {**headers, "X-Reason": "Descarga analitica"}
    pdf_response = client.get("/reports/analytics/pdf", headers=download_headers)
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"

    csv_response = client.get("/reports/analytics/export.csv", headers=download_headers)
    assert csv_response.status_code == status.HTTP_200_OK
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "Comparativo" in csv_response.text

    categories_response = client.get("/reports/analytics/categories", headers=headers)
    assert categories_response.status_code == status.HTTP_200_OK
    categories = categories_response.json()["categories"]
    assert len(categories) > 0

    date_from = (date.today() - timedelta(days=7)).isoformat()
    date_to = date.today().isoformat()
    alert_response = client.get(
        f"/reports/analytics/alerts?date_from={date_from}&date_to={date_to}",
        headers=headers,
    )
    assert alert_response.status_code == status.HTTP_200_OK
    alert_items = alert_response.json()["items"]
    assert any(alert["type"] == "stock" for alert in alert_items)

    realtime_response = client.get("/reports/analytics/realtime", headers=headers)
    assert realtime_response.status_code == status.HTTP_200_OK
    realtime_items = realtime_response.json()["items"]
    assert any("trend" in widget for widget in realtime_items)

    rotation_filtered = client.get(
        f"/reports/analytics/rotation?store_ids={store_id}&date_from={date_from}&date_to={date_to}&category=ANL-001",
        headers=headers,
    )
    assert rotation_filtered.status_code == status.HTTP_200_OK
    assert all(item["store_id"] == store_id for item in rotation_filtered.json()["items"])

    try:
        settings.enable_purchases_sales = False
        disabled_sales_response = client.get("/reports/analytics/rotation", headers=headers)
        assert disabled_sales_response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_purchases_sales = True

    try:
        settings.enable_analytics_adv = False
        settings.enable_purchases_sales = True
        disabled_response = client.get("/reports/analytics/rotation", headers=headers)
        assert disabled_response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_analytics_adv = previous_analytics
        settings.enable_purchases_sales = previous_sales
