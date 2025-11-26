from datetime import date, timedelta
import tempfile

import pytest

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.config import settings as core_settings
from backend.app.core.roles import ADMIN
from backend.app.main import create_app
from backend.app.database import get_db


@pytest.fixture()
def client(db_session, monkeypatch):
    monkeypatch.setattr("backend.database.run_migrations", lambda: None)
    monkeypatch.setattr("backend.db.run_migrations", lambda: None)

    previous_scheduler = settings.enable_background_scheduler
    previous_backup_scheduler = settings.enable_backup_scheduler
    previous_backup_dir = settings.backup_directory
    settings.enable_background_scheduler = False
    settings.enable_backup_scheduler = False

    backup_tmp_dir = tempfile.TemporaryDirectory()
    settings.backup_directory = backup_tmp_dir.name

    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.expunge_all()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            if settings.bootstrap_token:
                test_client.headers.update(
                    {"X-Bootstrap-Token": settings.bootstrap_token}
                )
            yield test_client
    finally:
        app.dependency_overrides.clear()
        settings.enable_background_scheduler = previous_scheduler
        settings.enable_backup_scheduler = previous_backup_scheduler
        settings.backup_directory = previous_backup_dir
        backup_tmp_dir.cleanup()


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "dte_admin",
        "password": "DteAdmin123*",
        "full_name": "DTE Admin",
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


def _create_store(client, headers):
    response = client.post(
        "/stores",
        json={
            "name": "Sucursal DTE",
            "location": "Tegucigalpa",
            "timezone": "America/Tegucigalpa",
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def _create_device(client, store_id: int, headers):
    response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "DTE-001",
            "name": "Equipo Fiscal",
            "quantity": 10,
            "unit_price": 1500.0,
            "costo_unitario": 950.0,
            "margen_porcentaje": 15.0,
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def _create_sale(client, store_id: int, device_id: int, headers):
    payload = {
        "store_id": store_id,
        "customer_name": "Cliente Fiscal",
        "items": [{"device_id": device_id, "quantity": 1}],
        "payment_method": "EFECTIVO",
    }
    response = client.post(
        "/sales",
        json=payload,
        headers={**headers, "X-Reason": "Venta fiscal"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_dte_generation_flow_with_queue(client, db_session):
    previous_sales_flag = settings.enable_purchases_sales
    previous_dte_flag = core_settings.enable_dte
    settings.enable_purchases_sales = True
    core_settings.enable_dte = True
    try:
        token, user_id = _bootstrap_admin(client, db_session)
        auth_headers = {"Authorization": f"Bearer {token}"}

        store_id = _create_store(client, auth_headers)
        device_id = _create_device(client, store_id, auth_headers)
        sale_data = _create_sale(client, store_id, device_id, auth_headers)

        assert sale_data["dte_status"] is None or sale_data["dte_status"] == "PENDIENTE"
        assert sale_data["dte_reference"] is None

        authorization_payload = {
            "document_type": "FACTURA",
            "serie": "A001",
            "range_start": 1,
            "range_end": 20,
            "expiration_date": (date.today() + timedelta(days=30)).isoformat(),
            "cai": "CAI-20250101-ABCDEF123456",
            "store_id": store_id,
            "notes": "Serie inicial",
        }
        authorization_response = client.post(
            "/dte/authorizations",
            json=authorization_payload,
            headers={**auth_headers, "X-Reason": "Configurar serie"},
        )
        assert authorization_response.status_code == status.HTTP_201_CREATED
        authorization_id = authorization_response.json()["id"]

        generation_payload = {
            "sale_id": sale_data["id"],
            "authorization_id": authorization_id,
            "issuer": {
                "rtn": "08011985123960",
                "name": "Softmobile Honduras",
                "address": "Boulevard Centro",
            },
            "signer": {
                "certificate_serial": "CERT-001",
                "private_key": "clave-privada-dte",
            },
            "offline": True,
        }
        document_response = client.post(
            "/dte/documents/generate",
            json=generation_payload,
            headers={**auth_headers, "X-Reason": "Emitir DTE"},
        )
        assert document_response.status_code == status.HTTP_201_CREATED
        document_payload = document_response.json()

        assert document_payload["status"] == "PENDIENTE"
        assert document_payload["control_number"].startswith("A001-")
        assert document_payload["queue"]
        assert document_payload["queue"][0]["status"] == "PENDING"

        queue_response = client.get(
            "/dte/queue",
            headers=auth_headers,
        )
        assert queue_response.status_code == status.HTTP_200_OK
        assert queue_response.json()[0]["status"] == "PENDING"

        send_response = client.post(
            f"/dte/documents/{document_payload['id']}/send",
            json={"mode": "ONLINE"},
            headers={**auth_headers, "X-Reason": "Enviar DTE"},
        )
        assert send_response.status_code == status.HTTP_200_OK
        sent_payload = send_response.json()
        assert sent_payload["sent_at"] is not None

        queue_after = client.get("/dte/queue", headers=auth_headers)
        assert queue_after.status_code == status.HTTP_200_OK
        assert queue_after.json()[0]["status"] == "SENT"

        ack_payload = {
            "status": "EMITIDO",
            "code": "ACK-001",
            "detail": "Documento aceptado",
        }
        ack_response = client.post(
            f"/dte/documents/{document_payload['id']}/ack",
            json=ack_payload,
            headers={**auth_headers, "X-Reason": "Registrar acuse"},
        )
        assert ack_response.status_code == status.HTTP_200_OK
        ack_document = ack_response.json()
        assert ack_document["status"] == "EMITIDO"
        assert ack_document["ack_code"] == "ACK-001"

        refreshed_sale = db_session.get(models.Sale, sale_data["id"])
        assert refreshed_sale is not None
        assert refreshed_sale.dte_status == models.DTEStatus.EMITIDO
        assert refreshed_sale.dte_reference == "ACK-001"
    finally:
        settings.enable_purchases_sales = previous_sales_flag
        core_settings.enable_dte = previous_dte_flag


def test_dte_authorization_conflict(client, db_session):
    previous_sales_flag = settings.enable_purchases_sales
    previous_dte_flag = core_settings.enable_dte
    settings.enable_purchases_sales = True
    core_settings.enable_dte = True
    try:
        token, _ = _bootstrap_admin(client, db_session)
        auth_headers = {"Authorization": f"Bearer {token}"}
        store_id = _create_store(client, auth_headers)

        base_payload = {
            "document_type": "FACTURA",
            "serie": "B001",
            "range_start": 1,
            "range_end": 10,
            "expiration_date": (date.today() + timedelta(days=60)).isoformat(),
            "cai": "CAI-20250102-XYZ987654321",
            "store_id": store_id,
        }
        response = client.post(
            "/dte/authorizations",
            json=base_payload,
            headers={**auth_headers, "X-Reason": "Configurar serie"},
        )
        assert response.status_code == status.HTTP_201_CREATED

        conflict_payload = base_payload | {"cai": "CAI-20250103-CONFLICTO"}
        conflict_response = client.post(
            "/dte/authorizations",
            json=conflict_payload,
            headers={**auth_headers, "X-Reason": "Configurar serie"},
        )
        assert conflict_response.status_code == status.HTTP_409_CONFLICT
    finally:
        settings.enable_purchases_sales = previous_sales_flag
        core_settings.enable_dte = previous_dte_flag
