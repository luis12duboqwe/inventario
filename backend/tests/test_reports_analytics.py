from datetime import date

from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN


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


def test_advanced_analytics_endpoints(client):
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

    sale_resp = client.post(
        "/sales",
        json={"store_id": store_id, "payment_method": "EFECTIVO", "items": [{"device_id": device_id, "quantity": 2}]},
        headers={**headers, "X-Reason": "Venta analitica"},
    )
    assert sale_resp.status_code == status.HTTP_201_CREATED

    rotation_response = client.get("/reports/analytics/rotation", headers=headers)
    assert rotation_response.status_code == status.HTTP_200_OK
    rotation_items = rotation_response.json()["items"]
    assert any(item["device_id"] == device_id for item in rotation_items)

    aging_response = client.get("/reports/analytics/aging", headers=headers)
    assert aging_response.status_code == status.HTTP_200_OK
    assert any(item["device_id"] == device_id for item in aging_response.json()["items"])

    forecast_response = client.get("/reports/analytics/stockout_forecast", headers=headers)
    assert forecast_response.status_code == status.HTTP_200_OK
    assert any(item["device_id"] == device_id for item in forecast_response.json()["items"])

    pdf_response = client.get("/reports/analytics/pdf", headers=headers)
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"

    settings.enable_analytics_adv = False
    settings.enable_purchases_sales = False
