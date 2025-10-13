from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "catalog_admin",
        "password": "ClaveSegura123",
        "full_name": "Catálogo Admin",
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
    return {"Authorization": f"Bearer {token}"}


def test_advanced_catalog_search_and_audit(client) -> None:
    settings.enable_catalog_pro = True
    headers = _auth_headers(client)

    store_a = client.post(
        "/stores",
        json={"name": "Tienda Norte", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_a.status_code == status.HTTP_201_CREATED
    store_a_id = store_a.json()["id"]

    store_b = client.post(
        "/stores",
        json={"name": "Tienda Sur", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_b.status_code == status.HTTP_201_CREATED
    store_b_id = store_b.json()["id"]

    device_payload = {
        "sku": "SKU-CAT-001",
        "name": "iPhone 15 Pro",
        "quantity": 3,
        "imei": "490154203237518",
        "serial": "SN-CAT-0001",
        "marca": "Apple",
        "modelo": "15 Pro",
        "color": "Grafito",
        "capacidad_gb": 256,
        "estado_comercial": "nuevo",
        "proveedor": "Apple MX",
        "costo_unitario": 18500.0,
        "margen_porcentaje": 25.0,
        "garantia_meses": 24,
        "lote": "L-001",
    }
    create_device = client.post(
        f"/stores/{store_a_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert create_device.status_code == status.HTTP_201_CREATED
    device_id = create_device.json()["id"]
    sale_price = create_device.json()["unit_price"]
    assert sale_price > device_payload["costo_unitario"]

    duplicated = client.post(
        f"/stores/{store_b_id}/devices",
        json={**device_payload, "sku": "SKU-CAT-002"},
        headers=headers,
    )
    assert duplicated.status_code == status.HTTP_409_CONFLICT
    assert duplicated.json()["detail"]["code"] == "device_identifier_conflict"

    update_response = client.patch(
        f"/inventory/stores/{store_a_id}/devices/{device_id}",
        json={"costo_unitario": 19000.0, "proveedor": "Apple Direct"},
        headers=headers,
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["unit_price"] > sale_price

    search_response = client.get(
        "/inventory/devices/search",
        params={"imei": device_payload["imei"]},
        headers=headers,
    )
    assert search_response.status_code == status.HTTP_200_OK
    results = search_response.json()
    assert len(results) == 1
    assert results[0]["store_name"] == "Tienda Norte"
    assert results[0]["imei"] == device_payload["imei"]
    assert results[0]["proveedor"] == "Apple Direct"

    audit_response = client.get("/reports/audit", headers=headers)
    assert audit_response.status_code == status.HTTP_200_OK
    assert any(
        log["entity_id"] == str(device_id) and "costo_unitario" in (log.get("details") or "")
        for log in audit_response.json()
    )

    settings.enable_catalog_pro = False
