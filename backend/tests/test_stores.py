from fastapi import status

from backend.app.core.roles import ADMIN


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "admin",
        "password": "MuySegura123",
        "full_name": "Admin General",
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
    return {"Authorization": f"Bearer {token}", "X-Reason": "Operacion de prueba"}


def test_inventory_flow(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Centro", "location": "CDMX", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SKU-001", "name": "Galaxy S24", "quantity": 5, "unit_price": 15000.0}
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    low_stock_payload = {"sku": "SKU-LOW", "name": "Moto G", "quantity": 2, "unit_price": 4500.0}
    low_stock_response = client.post(
        f"/stores/{store_id}/devices", json=low_stock_payload, headers=headers
    )
    assert low_stock_response.status_code == status.HTTP_201_CREATED
    low_stock_id = low_stock_response.json()["id"]

    movement_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "entrada",
        "cantidad": 10,
        "comentario": "Inventario inicial",
    }
    movement_response = client.post(
        f"/inventory/stores/{store_id}/movements", json=movement_payload, headers=headers
    )
    assert movement_response.status_code == status.HTTP_201_CREATED
    movement_data = movement_response.json()
    assert movement_data["producto_id"] == device_id
    assert movement_data["tienda_destino_id"] == store_id

    summary_response = client.get("/inventory/summary", headers=headers)
    assert summary_response.status_code == status.HTTP_200_OK
    summary = summary_response.json()
    assert summary[0]["total_items"] == 17
    assert summary[0]["total_value"] == 15 * 15000.0 + 2 * 4500.0
    assert any(device["unit_price"] == 15000.0 for device in summary[0]["devices"])
    assert any(device["inventory_value"] == 2 * 4500.0 for device in summary[0]["devices"])

    sync_response = client.post("/sync/run", json={"store_id": store_id}, headers=headers)
    assert sync_response.status_code == status.HTTP_200_OK

    logs_response = client.get("/reports/audit", headers=headers)
    assert logs_response.status_code == status.HTTP_200_OK
    assert any(log["action"] == "inventory_movement" for log in logs_response.json())

    metrics_response = client.get("/reports/metrics", headers=headers)
    assert metrics_response.status_code == status.HTTP_200_OK
    metrics = metrics_response.json()
    assert metrics["totals"]["total_units"] == 17
    assert metrics["totals"]["total_value"] == summary[0]["total_value"]
    assert metrics["top_stores"][0]["store_id"] == store_id
    low_stock_devices = metrics["low_stock_devices"]
    assert any(device["device_id"] == low_stock_id for device in low_stock_devices)
    audit_alerts = metrics["audit_alerts"]
    assert audit_alerts["total"] == audit_alerts["critical"] + audit_alerts["warning"] + audit_alerts["info"]
    assert audit_alerts["has_alerts"] == (
        audit_alerts["critical"] > 0 or audit_alerts["warning"] > 0
    )
    assert isinstance(audit_alerts["highlights"], list)


def test_device_filters_by_search_and_state(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal Norte", "location": "MTY", "timezone": "America/Monterrey"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    devices = [
        {
            "sku": "SKU-IPHONE",
            "name": "iPhone 15 Pro",
            "quantity": 4,
            "unit_price": 32500.0,
            "imei": "490154203237518",
            "modelo": "iPhone 15 Pro",
            "estado_comercial": "A",
        },
        {
            "sku": "SKU-MOTO",
            "name": "Moto Edge 50",
            "quantity": 6,
            "unit_price": 14500.0,
            "serial": "MOTO-EDGE-50-XYZ",
            "estado_comercial": "B",
        },
        {
            "sku": "SKU-GALAXY",
            "name": "Galaxy S24",
            "quantity": 8,
            "unit_price": 28999.0,
            "modelo": "Galaxy S24",
            "estado_comercial": "nuevo",
        },
    ]

    for payload in devices:
        create_response = client.post(f"/stores/{store_id}/devices", json=payload, headers=headers)
        assert create_response.status_code == status.HTTP_201_CREATED

    search_response = client.get(
        f"/stores/{store_id}/devices",
        headers=headers,
        params={"search": "iphone"},
    )
    assert search_response.status_code == status.HTTP_200_OK
    search_results = search_response.json()
    assert len(search_results) == 1
    assert search_results[0]["sku"] == "SKU-IPHONE"

    estado_response = client.get(
        f"/stores/{store_id}/devices",
        headers=headers,
        params={"estado": "B"},
    )
    assert estado_response.status_code == status.HTTP_200_OK
    estado_results = estado_response.json()
    assert len(estado_results) == 1
    assert all(device["estado_comercial"] == "B" for device in estado_results)

    mixed_response = client.get(
        f"/stores/{store_id}/devices",
        headers=headers,
        params={"search": "galaxy", "estado": "nuevo"},
    )
    assert mixed_response.status_code == status.HTTP_200_OK
    mixed_results = mixed_response.json()
    assert len(mixed_results) == 1
    assert mixed_results[0]["sku"] == "SKU-GALAXY"

    invalid_response = client.get(
        f"/stores/{store_id}/devices",
        headers=headers,
        params={"estado": "Z"},
    )
    assert invalid_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_requires_authentication(client) -> None:
    store_payload = {"name": "Sucursal Sin Token"}
    response = client.post("/stores", json=store_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
