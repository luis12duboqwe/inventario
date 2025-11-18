from datetime import datetime, timedelta

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import models


def _bootstrap_admin(client: TestClient) -> str:
    payload = {
        "username": "admin_soporte",
        "password": "AdminSoporte123*",
        "full_name": "Admin Soporte",
        "roles": ["ADMIN"],
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


def test_submit_feedback_creates_record(client: TestClient, db_session):
    payload = {
        "module": "inventory",
        "category": "incidente",
        "priority": "alta",
        "title": "No carga la vista de inventario",
        "description": "La tabla queda en blanco al aplicar filtros avanzados.",
        "contact": "ops@softmobile.test",
        "metadata": {"filters": ["marca:ACME"], "tab": "resumen"},
        "usage_context": {"browser": "Playwright"},
    }

    response = client.post("/support/feedback", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "abierto"
    assert body["tracking_id"]

    stored = db_session.scalar(
        select(models.SupportFeedback).where(models.SupportFeedback.title == payload["title"])
    )
    assert stored is not None
    assert stored.category.value == payload["category"]
    assert stored.priority.value == payload["priority"]


def test_feedback_metrics_and_status_updates(client: TestClient, db_session):
    admin_token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    first = client.post(
        "/support/feedback",
        json={
            "module": "inventory",
            "category": "mejora",
            "priority": "media",
            "title": "Filtrar por costo",
            "description": "Solicitamos filtros por costo y margen para priorizar compras.",
        },
    )
    assert first.status_code == status.HTTP_201_CREATED
    tracking_id = first.json()["tracking_id"]

    second = client.post(
        "/support/feedback",
        json={
            "module": "sales",
            "category": "rendimiento",
            "priority": "critica",
            "title": "POS tarda en cargar",
            "description": "El POS demora más de 12 segundos en abrir en sucursal norte.",
        },
    )
    assert second.status_code == status.HTTP_201_CREATED

    db_session.add_all(
        [
            models.AuditUI(
                ts=datetime.utcnow() - timedelta(days=1),
                user_id="demo",
                module="sales",
                action="pos_open",
                entity_id="demo-pos",
            ),
            models.AuditUI(
                ts=datetime.utcnow() - timedelta(days=2),
                user_id="demo",
                module="sales",
                action="pos_charge",
                entity_id="demo-pos",
            ),
            models.AuditUI(
                ts=datetime.utcnow() - timedelta(days=3),
                user_id="demo",
                module="inventory",
                action="view",
                entity_id="device-1",
            ),
        ]
    )
    db_session.commit()

    status_response = client.patch(
        f"/support/feedback/{tracking_id}",
        json={"status": "en_progreso", "resolution_notes": "Analizando logs"},
        headers=headers,
    )
    assert status_response.status_code == status.HTTP_200_OK
    assert status_response.json()["status"] == "en_progreso"

    metrics = client.get("/support/feedback/metrics", headers=headers)
    assert metrics.status_code == status.HTTP_200_OK
    data = metrics.json()
    assert data["totals"]["feedback"] >= 2
    assert data["by_category"].get("mejora") == 1
    assert any(hotspot["module"] == "sales" for hotspot in data["hotspots"])
