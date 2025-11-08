from __future__ import annotations

from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "catalog_filters_admin",
        "password": "ClaveSegura123",
        "full_name": "Catalog Filters Admin",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == 201

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Reason": "Catalog filters test"}


def test_catalog_search_filters_by_estado_comercial(client, db_session) -> None:
    previous_flag = settings.enable_catalog_pro
    settings.enable_catalog_pro = True
    headers = _auth_headers(client)

    try:
        store_response = client.post(
            "/stores",
            json={
                "name": "Sucursal Clasificacion",
                "location": "MX",
                "timezone": "America/Mexico_City",
            },
            headers=headers,
        )
        assert store_response.status_code == 201
        store_id = store_response.json()["id"]

        base_payload = {
            "sku": "SKU-CLAS-001",
            "name": "Equipo Clasificacion",
            "quantity": 5,
            "unit_price": 12000.0,
            "costo_unitario": 9500.0,
            "costo_compra": 9500.0,
            "precio_venta": 12000.0,
            "marca": "Softmobile",
            "modelo": "X1",
            "categoria": "Smartphones",
            "condicion": "Nuevo",
            "color": "Negro",
            "capacidad_gb": 128,
            "estado": "disponible",
            "proveedor": "Softmobile MX",
            "margen_porcentaje": 20.0,
            "garantia_meses": 12,
        }

        first_device = client.post(
            f"/stores/{store_id}/devices",
            json={**base_payload, "imei": "490154203237519", "serial": "SN-CLAS-0001", "estado_comercial": "A"},
            headers=headers,
        )
        assert first_device.status_code == 201

        second_device = client.post(
            f"/stores/{store_id}/devices",
            json={**base_payload, "sku": "SKU-CLAS-002", "imei": "490154203237520", "serial": "SN-CLAS-0002", "estado_comercial": "C"},
            headers=headers,
        )
        assert second_device.status_code == 201

        search_response = client.get(
            "/inventory/devices/search",
            params={"estado_comercial": "a"},
            headers=headers,
        )
        assert search_response.status_code == 200
        payload = search_response.json()
        items = payload["items"]
        assert len(items) == 1
        assert items[0]["estado_comercial"] == "A"
        assert items[0]["sku"] == base_payload["sku"]

        db_session.expire_all()
        audit_entries = db_session.execute(
            select(models.AuditLog).where(models.AuditLog.action == "inventory_catalog_search")
        ).scalars().all()
        assert audit_entries, "Se esperaba al menos un registro de auditoría"
        last_entry = audit_entries[-1]
        assert last_entry.details is not None
        assert "\"estado_comercial\": \"A\"" in last_entry.details
        assert "\"results\": 1" in last_entry.details
    finally:
        settings.enable_catalog_pro = previous_flag


def test_catalog_search_rejects_invalid_estado_comercial(client) -> None:
    previous_flag = settings.enable_catalog_pro
    settings.enable_catalog_pro = True
    headers = _auth_headers(client)

    try:
        response = client.get(
            "/inventory/devices/search",
            params={"estado_comercial": "Z"},
            headers=headers,
        )
        assert response.status_code == 422
        detail = response.json().get("detail")
        assert isinstance(detail, list)
        assert any(
            (entry.get("msg") and "estado_comercial_invalido" in entry.get("msg", ""))
            or (
                isinstance(entry.get("ctx"), dict)
                and "estado_comercial_invalido" in str(entry["ctx"].get("error", ""))
            )
            for entry in detail
        )
    finally:
        settings.enable_catalog_pro = previous_flag
