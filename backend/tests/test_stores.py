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
    return {"Authorization": f"Bearer {token}"}


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

    movement_payload = {"device_id": device_id, "movement_type": "entrada", "quantity": 10}
    movement_response = client.post(
        f"/inventory/stores/{store_id}/movements", json=movement_payload, headers=headers
    )
    assert movement_response.status_code == status.HTTP_201_CREATED

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


def test_requires_authentication(client) -> None:
    store_payload = {"name": "Sucursal Sin Token"}
    response = client.post("/stores", json=store_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
