from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import status

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "risk_admin",
        "password": "RiskAdmin123*",
        "full_name": "Risk Admin",
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


def test_risk_alerts_detect_discount_and_cancellation(client, db_session):
    previous_analytics = settings.enable_analytics_adv
    previous_sales = settings.enable_purchases_sales
    settings.enable_analytics_adv = True
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}", "X-Reason": "Riesgos automáticos"}

    store_resp = client.post(
        "/stores",
        json={"name": "Riesgos Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_resp.status_code == status.HTTP_201_CREATED
    store_id = store_resp.json()["id"]

    device_resp = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "RISK-001",
            "name": "Equipo riesgo",
            "quantity": 5,
            "unit_price": 1500.0,
            "costo_unitario": 900.0,
            "margen_porcentaje": 20.0,
            "fecha_compra": datetime.utcnow().date().isoformat(),
        },
        headers=headers,
    )
    assert device_resp.status_code == status.HTTP_201_CREATED
    device_id = device_resp.json()["id"]

    sale_resp = client.post(
        "/sales",
        json={
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "discount_percent": 35.0,
            "items": [{"device_id": device_id, "quantity": 1}],
        },
        headers=headers,
    )
    assert sale_resp.status_code == status.HTTP_201_CREATED
    sale = db_session.get(models.Sale, sale_resp.json()["id"])
    sale.created_at = datetime.utcnow() - timedelta(days=2)
    sale.discount_percent = Decimal("35.00")
    db_session.add(sale)

    cancellation_resp = client.post(
        "/sales",
        json={
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 1}],
        },
        headers=headers,
    )
    assert cancellation_resp.status_code == status.HTTP_201_CREATED
    cancellation_sale = db_session.get(models.Sale, cancellation_resp.json()["id"])
    cancellation_sale.status = "CANCELADA"
    cancellation_sale.updated_at = datetime.utcnow() - timedelta(days=1)
    db_session.add(cancellation_sale)
    db_session.commit()

    response = client.get("/reports/analytics/risk", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    codes = {alert["code"] for alert in payload["alerts"]}
    assert "discount_spikes" in codes
    assert "cancellations_peak" in codes

    settings.enable_analytics_adv = previous_analytics
    settings.enable_purchases_sales = previous_sales
