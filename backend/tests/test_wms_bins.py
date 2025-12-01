from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import create_app
from backend.app.config import settings
from backend.app.database import get_db


def _make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.expunge_all()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client


def _bootstrap_admin_token(client: TestClient) -> str:
    payload = {
        "username": "wms_admin",
        "password": "WmsAdmin123*",
        "full_name": "WMS Admin",
        "roles": ["ADMIN"],
    }
    bootstrap_headers = {}
    if settings.bootstrap_token:
        bootstrap_headers["X-Bootstrap-Token"] = settings.bootstrap_token
    resp = client.post("/auth/bootstrap", json=payload,
                       headers=bootstrap_headers)
    assert resp.status_code in (201, 200)

    token_resp = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 200
    return token_resp.json()["access_token"]


def test_wms_bins_flag_disabled_returns_404(db_session: Session) -> None:
    # Desactivar la bandera y crear app dedicada
    settings.enable_wms_bins = False
    client = _make_client(db_session)
    token = _bootstrap_admin_token(client)
    auth = {"Authorization": f"Bearer {token}", "X-Reason": "WMS QA"}

    # Crear una sucursal
    store_resp = client.post(
        "/stores", json={"name": "Sucursal WMS", "code": "SUC-WMS"}, headers=auth
    )
    assert store_resp.status_code == 201
    store_id = store_resp.json()["id"]

    # La ruta debe responder 404 al estar deshabilitada la bandera
    list_resp = client.get(f"/inventory/stores/{store_id}/bins", headers=auth)
    assert list_resp.status_code == 404
    assert "Funcionalidad no disponible" in list_resp.text


def test_wms_bins_crud_and_assignment_flow(db_session: Session) -> None:
    # Activar la bandera y crear app dedicada
    settings.enable_wms_bins = True
    client = _make_client(db_session)
    token = _bootstrap_admin_token(client)
    base_headers = {"Authorization": f"Bearer {token}",
                    "X-Reason": "Operacion WMS"}

    # Crear sucursal
    store_resp = client.post(
        "/stores", json={"name": "Sucursal Centro", "code": "SUC-100"}, headers=base_headers
    )
    assert store_resp.status_code == 201
    store_id = store_resp.json()["id"]

    # Crear bin
    bin_payload = {"codigo": "A1-01",
                   "pasillo": "A1", "rack": "R1", "nivel": "01"}
    create_resp = client.post(
        f"/inventory/stores/{store_id}/bins", json=bin_payload, headers=base_headers
    )
    assert create_resp.status_code == 201
    bin_id = create_resp.json()["id"]
    assert create_resp.json()["codigo"] == "A1-01"

    # Listar bins
    list_resp = client.get(
        f"/inventory/stores/{store_id}/bins", headers=base_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == bin_id for item in list_resp.json())

    # Actualizar bin (cambiar código)
    update_resp = client.put(
        f"/inventory/stores/{store_id}/bins/{bin_id}",
        json={"codigo": "A1-02"},
        headers=base_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["codigo"] == "A1-02"

    # Crear dispositivo
    device_payload = {
        "sku": "SKU-WMS-1",
        "name": "Telefono Demo",
        "quantity": 1,
        "precio_venta": 10.0,
    }
    device_resp = client.post(
        f"/stores/{store_id}/devices", json=device_payload, headers=base_headers
    )
    assert device_resp.status_code == 201
    device_id = device_resp.json()["id"]

    # Asignar dispositivo al bin (requiere X-Reason)
    assign_resp = client.post(
        f"/inventory/stores/{store_id}/devices/{device_id}/bin",
        params={"bin_id": bin_id},
        headers=base_headers,
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["bin"]["id"] == bin_id

    # Obtener bin actual del dispositivo
    current_bin_resp = client.get(
        f"/inventory/stores/{store_id}/devices/{device_id}/bin", headers=base_headers
    )
    assert current_bin_resp.status_code == 200
    assert current_bin_resp.json()["id"] == bin_id

    # Listar dispositivos por bin
    devices_in_bin = client.get(
        f"/inventory/stores/{store_id}/bins/{bin_id}/devices", headers=base_headers
    )
    assert devices_in_bin.status_code == 200
    device_ids = [d["id"] for d in devices_in_bin.json()]
    assert device_id in device_ids

    # Validar rechazo por falta de X-Reason en una operación sensible
    missing_reason_headers = {"Authorization": f"Bearer {token}"}
    bad_resp = client.post(
        f"/inventory/stores/{store_id}/devices/{device_id}/bin",
        params={"bin_id": bin_id},
        headers=missing_reason_headers,
    )
    assert bad_resp.status_code in (400, 422)
