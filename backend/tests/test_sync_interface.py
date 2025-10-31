from __future__ import annotations

import json
from datetime import datetime, timedelta

from starlette import status

from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "sync_admin",
        "password": "Sync123*",
        "full_name": "Sync Admin",
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


def test_sync_overview_returns_branch_status(client, db_session):
    token, _ = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Central", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    session = models.SyncSession(
        store_id=store_id,
        mode=models.SyncMode.MANUAL,
        status=models.SyncStatus.SUCCESS,
        started_at=datetime.utcnow() - timedelta(minutes=5),
        finished_at=datetime.utcnow() - timedelta(minutes=4),
    )
    db_session.add(session)
    db_session.commit()

    overview_response = client.get("/sync/overview", headers=headers)
    assert overview_response.status_code == status.HTTP_200_OK
    overview = overview_response.json()
    assert isinstance(overview, list)
    assert any(entry["store_id"] == store_id for entry in overview)


def test_sync_conflict_exports_produce_files(client, db_session):
    token, _ = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Norte", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    conflict_payload = {
        "sku": "SKU-CONFLICTO",
        "product_name": "Router empresarial",
        "diferencia": 5,
        "max": [{"store_id": store_id, "store_name": "Norte", "quantity": 10}],
        "min": [{"store_id": store_id, "store_name": "Norte", "quantity": 5}],
    }
    log_entry = models.AuditLog(
        action="sync_discrepancy",
        entity_type="device",
        entity_id="SYNC-1",
        details=json.dumps(conflict_payload, ensure_ascii=False),
    )
    db_session.add(log_entry)
    db_session.commit()

    list_response = client.get(
        "/sync/conflicts",
        headers=headers,
        params={"limit": 200, "offset": 0},
    )
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.json(), "Se esperaba al menos un conflicto registrado"

    pdf_response = client.get(
        "/sync/conflicts/export/pdf",
        headers={**headers, "X-Reason": "Reporte conflictos"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"

    excel_response = client.get(
        "/sync/conflicts/export/xlsx",
        headers={**headers, "X-Reason": "Reporte conflictos"},
    )
    assert excel_response.status_code == status.HTTP_200_OK
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in excel_response.headers[
        "content-type"
    ]


def test_transfer_report_exports(client, db_session):
    previous_value = settings.enable_transfers
    settings.enable_transfers = True
    token, _ = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    origen = client.post(
        "/stores",
        json={"name": "Origen", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    destino = client.post(
        "/stores",
        json={"name": "Destino", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert origen.status_code == status.HTTP_201_CREATED
    assert destino.status_code == status.HTTP_201_CREATED
    origen_id = origen.json()["id"]
    destino_id = destino.json()["id"]

    device_payload = {
        "sku": "SKU-001",
        "name": "Router corporativo",
        "quantity": 10,
        "unit_price": 1500.0,
    }
    device_response = client.post(
        f"/stores/{origen_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    transfer_payload = {
        "origin_store_id": origen_id,
        "destination_store_id": destino_id,
        "reason": "Abastecimiento destino",
        "items": [{"device_id": device_id, "quantity": 2}],
    }
    create_transfer = client.post(
        "/transfers",
        json=transfer_payload,
        headers={**headers, "X-Reason": "Crear transferencia"},
    )
    assert create_transfer.status_code == status.HTTP_201_CREATED

    report_response = client.get("/transfers/report", headers=headers)
    assert report_response.status_code == status.HTTP_200_OK
    payload = report_response.json()
    assert payload["totals"]["total_transfers"] >= 1

    pdf_response = client.get(
        "/transfers/export/pdf",
        headers={**headers, "X-Reason": "Reporte transferencias"},
    )
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"

    excel_response = client.get(
        "/transfers/export/xlsx",
        headers={**headers, "X-Reason": "Reporte transferencias"},
    )
    assert excel_response.status_code == status.HTTP_200_OK
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in excel_response.headers[
        "content-type"
    ]

    settings.enable_transfers = previous_value
