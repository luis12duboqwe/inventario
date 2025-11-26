from fastapi import status
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "warranty_admin",
        "password": "Garantias123*",
        "full_name": "Garantías Admin",
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


def test_warranty_assignment_and_claim_flow(client, db_session):
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Garantías Centro", "location": "MX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SKU-GAR-001",
        "name": "Smartphone Garantía",
        "quantity": 2,
        "unit_price": 450.0,
        "costo_unitario": 300.0,
        "margen_porcentaje": 20.0,
        "garantia_meses": 12,
        "imei": "358001234567890",
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
        "payment_method": "EFECTIVO",
        "discount_percent": 0.0,
        "items": [{"device_id": device_id, "quantity": 1}],
    }
    sale_response = client.post(
        "/sales",
        json=sale_payload,
        headers={**auth_headers, "X-Reason": "Venta garantia"},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale_data = sale_response.json()
    assert sale_data["items"][0]["warranty_status"] == "ACTIVA"

    list_response = client.get("/warranties", headers=auth_headers)
    assert list_response.status_code == status.HTTP_200_OK
    warranties = list_response.json()
    assert len(warranties) == 1
    assignment = warranties[0]
    assert assignment["coverage_months"] == 12
    assert assignment["status"] == "ACTIVA"
    assert assignment["remaining_days"] >= 330  # margen generoso por calendario

    metrics_response = client.get("/warranties/metrics", headers=auth_headers)
    assert metrics_response.status_code == status.HTTP_200_OK
    metrics = metrics_response.json()
    assert metrics["total_assignments"] == 1
    assert metrics["active_assignments"] == 1

    claim_payload = {
        "claim_type": "REPARACION",
        "notes": "Pantalla con falla de pixeles",
        "repair_order": {
            "store_id": store_id,
            "customer_id": None,
            "customer_name": "Cliente Garantía",
            "customer_contact": "555-0101",
            "technician_name": "Técnico Garantías",
            "damage_type": "PANTALLA",
            "diagnosis": "Sin imagen",
            "device_model": "Modelo X",
            "imei": "358001234567890",
            "device_description": "Equipo vendido con garantía",
            "notes": "Cobertura completa",
            "labor_cost": 150.0,
            "parts": [],
        },
    }
    claim_response = client.post(
        f"/warranties/{assignment['id']}/claims",
        json=claim_payload,
        headers={**auth_headers, "X-Reason": "Reclamo garantia"},
    )
    assert claim_response.status_code == status.HTTP_201_CREATED
    updated_assignment = claim_response.json()
    assert updated_assignment["status"] == "RECLAMO"
    assert updated_assignment["claims"][0]["status"] == "EN_PROCESO"

    claim_id = updated_assignment["claims"][0]["id"]
    resolution_payload = {"status": "RESUELTO", "notes": "Equipo reemplazado"}
    resolution_response = client.patch(
        f"/warranties/claims/{claim_id}",
        json=resolution_payload,
        headers={**auth_headers, "X-Reason": "Cerrar reclamo"},
    )
    assert resolution_response.status_code == status.HTTP_200_OK
    resolved_assignment = resolution_response.json()
    assert resolved_assignment["status"] == "RESUELTA"
    assert resolved_assignment["claims"][0]["status"] == "RESUELTO"

    metrics_after = client.get("/warranties/metrics", headers=auth_headers).json()
    assert metrics_after["claims_resolved"] == 1
    assert metrics_after["claims_open"] == 0

    settings.enable_purchases_sales = False
