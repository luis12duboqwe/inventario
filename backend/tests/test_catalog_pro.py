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
    return {"Authorization": f"Bearer {token}", "X-Reason": "Operacion catalogo"}


def test_advanced_catalog_search_and_audit(client) -> None:
    previous_flag = settings.enable_catalog_pro
    settings.enable_catalog_pro = True
    headers = _auth_headers(client)

    try:
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
            "categoria": "Smartphones",
            "condicion": "Exhibición",
            "color": "Grafito",
            "capacidad_gb": 256,
            "capacidad": "256 GB",
            "estado": "apartado",
            "estado_comercial": "nuevo",
            "proveedor": "Apple MX",
            "costo_unitario": 18500.0,
            "costo_compra": 18500.0,
            "precio_venta": 23999.0,
            "margen_porcentaje": 25.0,
            "garantia_meses": 24,
            "lote": "L-001",
            "fecha_compra": "2025-01-15",
            "fecha_ingreso": "2025-01-16",
            "ubicacion": "Pasillo A - Estante 3",
            "descripcion": "Equipo de vitrina con accesorios completos",
            "imagen_url": "https://cdn.softmobile.test/catalogo/iphone15pro.png",
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
        created_body = create_device.json()
        assert created_body["categoria"] == device_payload["categoria"]
        assert created_body["estado"] == device_payload["estado"]
        assert created_body["ubicacion"] == device_payload["ubicacion"]
        assert created_body["descripcion"].startswith("Equipo de vitrina")
        assert created_body["imagen_url"] == device_payload["imagen_url"]
        assert created_body["costo_compra"] == device_payload["costo_compra"]
        assert created_body["precio_venta"] == device_payload["precio_venta"]

        duplicated = client.post(
            f"/stores/{store_b_id}/devices",
            json={**device_payload, "sku": "SKU-CAT-002"},
            headers=headers,
        )
        assert duplicated.status_code == status.HTTP_409_CONFLICT
        assert duplicated.json()["detail"]["code"] == "device_identifier_conflict"

        update_response = client.patch(
            f"/inventory/stores/{store_a_id}/devices/{device_id}",
            json={
                "costo_compra": 19000.0,
                "costo_unitario": 19000.0,
                "precio_venta": 24999.0,
                "proveedor": "Apple Direct",
            },
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["unit_price"] > sale_price
        assert update_response.json()["proveedor"] == "Apple Direct"
        assert update_response.json()["precio_venta"] == 24999.0

        search_response = client.get(
            "/inventory/devices/search",
            params={"categoria": device_payload["categoria"], "estado": device_payload["estado"]},
            headers=headers,
        )
        assert search_response.status_code == status.HTTP_200_OK
        results_payload = search_response.json()
        results = results_payload["items"]
        assert len(results) == 1
        assert results[0]["store_name"] == "Tienda Norte"
        assert results[0]["imei"] == device_payload["imei"]
        assert results[0]["proveedor"] == "Apple Direct"

        audit_response = client.get("/reports/audit", headers=headers)
        assert audit_response.status_code == status.HTTP_200_OK
        audit_items = audit_response.json()["items"]
        assert any(
            log["entity_id"] == str(device_id) and "costo_unitario" in (log.get("details") or "")
            for log in audit_items
        )

        settings.enable_catalog_pro = False
        disabled_search = client.get(
            "/inventory/devices/search",
            params={"categoria": device_payload["categoria"], "estado": device_payload["estado"]},
            headers=headers,
        )
        assert disabled_search.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_catalog_pro = previous_flag


def test_inventory_import_export_roundtrip(client) -> None:
    previous_flag = settings.enable_catalog_pro
    settings.enable_catalog_pro = True
    headers = _auth_headers(client)

    store = client.post(
        "/stores",
        json={"name": "Tienda Centro", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store.status_code == status.HTTP_201_CREATED
    store_id = store.json()["id"]

    csv_content = (
        "sku,name,categoria,condicion,color,capacidad,estado,estado_comercial,quantity,costo_compra,precio_venta,"
        "proveedor,ubicacion,fecha_compra,fecha_ingreso,descripcion,imagen_url\n"
        "SKU-IMPORT-1,Galaxy S24,Smartphones,Nuevo,Negro,256 GB,disponible,nuevo,5,15000,18900,Samsung MX,Estante 1,"
        "2025-01-10,2025-01-12,Ingreso inicial,https://cdn.softmobile.test/galaxy-s24.png\n"
        "SKU-IMPORT-1,Galaxy S24,,Reacondicionado,,,apartado,A,7,15000,19900,Samsung MX,Estante 2,,,,\n"
    )

    response_import = client.post(
        f"/inventory/stores/{store_id}/devices/import",
        files={"file": ("catalogo.csv", csv_content, "text/csv")},
        headers=headers,
    )
    assert response_import.status_code == status.HTTP_201_CREATED
    summary = response_import.json()
    assert summary["created"] == 1
    assert summary["updated"] == 1
    assert summary["skipped"] == 0

    export_response = client.get(
        f"/inventory/stores/{store_id}/devices/export",
        headers=headers,
    )
    assert export_response.status_code == status.HTTP_200_OK
    assert "SKU-IMPORT-1" in export_response.text
    assert "apartado" in export_response.text

    list_response = client.get(
        f"/stores/{store_id}/devices",
        params={"estado_inventario": "apartado", "limit": 200, "offset": 0},
        headers=headers,
    )
    assert list_response.status_code == status.HTTP_200_OK
    devices_payload = list_response.json()
    devices = devices_payload["items"]
    assert len(devices) == 1
    assert devices[0]["estado"] == "apartado"
    assert devices[0]["categoria"] == "Smartphones"

    settings.enable_catalog_pro = False
    try:
        disabled_response = client.get(
            f"/stores/{store_id}/devices",
            params={"estado_inventario": "apartado", "limit": 200, "offset": 0},
            headers=headers,
        )
        assert disabled_response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_catalog_pro = previous_flag
