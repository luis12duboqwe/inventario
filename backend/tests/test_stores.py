from __future__ import annotations


def test_create_and_list_stores(client):
    payload = {"name": "Sucursal Centro", "location": "CDMX", "timezone": "America/Mexico_City"}
    response = client.post("/stores", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == payload["name"]

    list_response = client.get("/stores")
    assert list_response.status_code == 200
    data = list_response.json()
    assert len(data) == 1
    assert data[0]["name"] == payload["name"]


def test_duplicate_store_returns_conflict(client):
    payload = {"name": "Sucursal Norte"}
    first = client.post("/stores", json=payload)
    assert first.status_code == 201

    duplicate = client.post("/stores", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "store_already_exists"


def test_get_store_not_found(client):
    response = client.get("/stores/999")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "store_not_found"


def test_create_device_for_store(client):
    store = client.post("/stores", json={"name": "Inventario Sur"}).json()
    payload = {"sku": "SKU-123", "name": "Galaxy A54", "quantity": 5}
    response = client.post(f"/stores/{store['id']}/devices", json=payload)

    assert response.status_code == 201
    device = response.json()
    assert device["sku"] == payload["sku"]
    assert device["store_id"] == store["id"]

    list_response = client.get(f"/stores/{store['id']}/devices")
    assert list_response.status_code == 200
    devices = list_response.json()
    assert len(devices) == 1
    assert devices[0]["sku"] == payload["sku"]


def test_duplicate_device_per_store(client):
    store = client.post("/stores", json={"name": "Sucursal Oeste"}).json()
    payload = {"sku": "SKU-555", "name": "iPhone 15", "quantity": 2}
    first = client.post(f"/stores/{store['id']}/devices", json=payload)
    assert first.status_code == 201

    duplicate = client.post(f"/stores/{store['id']}/devices", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "device_already_exists"


def test_create_device_store_not_found(client):
    payload = {"sku": "SKU-404", "name": "Pixel 8"}
    response = client.post("/stores/999/devices", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "store_not_found"
