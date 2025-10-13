"""Tests covering store and device flows."""
from fastapi.testclient import TestClient


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
