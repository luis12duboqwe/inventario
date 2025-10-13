from __future__ import annotations

from fastapi import status


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "admin",
        "password": "MuySegura123",
        "full_name": "Admin General",
        "roles": ["admin"],
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

    device_payload = {"sku": "SKU-001", "name": "Galaxy S24", "quantity": 5}
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    movement_payload = {"device_id": device_id, "movement_type": "entrada", "quantity": 10}
    movement_response = client.post(
        f"/inventory/stores/{store_id}/movements", json=movement_payload, headers=headers
    )
    assert movement_response.status_code == status.HTTP_201_CREATED

    summary_response = client.get("/inventory/summary", headers=headers)
    assert summary_response.status_code == status.HTTP_200_OK
    summary = summary_response.json()
    assert summary[0]["total_items"] == 15

    sync_response = client.post("/sync/run", json={"store_id": store_id}, headers=headers)
    assert sync_response.status_code == status.HTTP_200_OK

    logs_response = client.get("/reports/audit", headers=headers)
    assert logs_response.status_code == status.HTTP_200_OK
    assert any(log["action"] == "inventory_movement" for log in logs_response.json())


def test_requires_authentication(client) -> None:
    store_payload = {"name": "Sucursal Sin Token"}
    response = client.post("/stores", json=store_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
"""Tests covering store and device flows using the simplified stack."""
from app.http import TestClient


def test_create_store(client: TestClient) -> None:
    payload = {"name": "Sucursal Norte", "location": "CDMX", "timezone": "America/Mexico_City"}
    response = client.post("/api/v1/stores/", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == payload["name"]


def test_create_duplicate_store(client: TestClient) -> None:
    payload = {"name": "Sucursal Centro"}
    first = client.post("/api/v1/stores/", json=payload)
    assert first.status_code == 201

    duplicate = client.post("/api/v1/stores/", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "store_already_exists"


def test_create_device_for_store(client: TestClient) -> None:
    store_payload = {"name": "Sucursal Sur"}
    store_response = client.post("/api/v1/stores/", json=store_payload)
    store_id = store_response.json()["id"]

    device_payload = {"sku": "SM-001", "name": "iPhone 15", "quantity": 10}
    device_response = client.post(f"/api/v1/stores/{store_id}/devices/", json=device_payload)
    assert device_response.status_code == 201
    device_body = device_response.json()
    assert device_body["store_id"] == store_id
    assert device_body["sku"] == "SM-001"

    list_response = client.get(f"/api/v1/stores/{store_id}/devices/")
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["name"] == "iPhone 15"


def test_device_creation_requires_existing_store(client: TestClient) -> None:
    response = client.post(
        "/api/v1/stores/999/devices/",
        json={"sku": "MISSING", "name": "Test", "quantity": 1},
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "store_not_found"


def test_duplicate_device_per_store_is_blocked(client: TestClient) -> None:
    store = client.post("/api/v1/stores/", json={"name": "Sucursal Centro Sur"})
    store_id = store.json()["id"]
    device = {"sku": "SKU-001", "name": "Galaxy", "quantity": 5}
    first = client.post(f"/api/v1/stores/{store_id}/devices/", json=device)
    assert first.status_code == 201

    duplicate = client.post(f"/api/v1/stores/{store_id}/devices/", json=device)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "device_already_exists"


def test_list_devices_for_unknown_store_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/stores/123/devices/")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "store_not_found"
