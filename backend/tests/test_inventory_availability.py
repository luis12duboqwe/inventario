from fastapi import status

from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "availability_admin",
        "password": "Disponibilidad123*",
        "full_name": "Inventario Global",
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
    return token_response.json()["access_token"]


def _create_store(client, headers, name):
    response = client.post(
        "/stores",
        json={"name": name, "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def _create_device(client, headers, store_id, sku, quantity):
    response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": sku,
            "name": f"Dispositivo {sku}",
            "quantity": quantity,
            "unit_price": 1000.0,
            "costo_unitario": 750.0,
            "margen_porcentaje": 20.0,
        },
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_inventory_availability_endpoint_groups_by_store(client):
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    store_a = _create_store(client, headers, "Sucursal Centro")
    store_b = _create_store(client, headers, "Sucursal Norte")

    sku = "SKU-AGG-01"
    device_a = _create_device(client, headers, store_a, sku, 5)
    device_b = _create_device(client, headers, store_b, sku, 3)

    response = client.get(
        "/inventory/availability",
        headers=headers,
        params={"sku": [sku]},
    )
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert "items" in payload
    assert payload["items"], "Se esperaba al menos un registro de disponibilidad"

    availability = payload["items"][0]
    assert availability["reference"] == sku.lower()
    assert sorted(availability["device_ids"]) == sorted([device_a["id"], device_b["id"]])
    stores = {entry["store_id"]: entry for entry in availability["stores"]}
    assert stores[store_a]["quantity"] == 5
    assert stores[store_b]["quantity"] == 3
    assert availability["total_quantity"] == 8


def test_inventory_availability_cache_invalidated_after_movement(client):
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    store_id = _create_store(client, headers, "Sucursal Disponibilidad")
    sku = "SKU-AGG-02"
    device = _create_device(client, headers, store_id, sku, 7)

    first_response = client.get(
        "/inventory/availability",
        headers=headers,
        params={"sku": [sku]},
    )
    assert first_response.status_code == status.HTTP_200_OK
    first_total = first_response.json()["items"][0]["total_quantity"]
    assert first_total == 7

    movement_payload = {
        "producto_id": device["id"],
        "tipo_movimiento": "salida",
        "cantidad": 2,
        "comentario": "Salida corporativa",
    }
    movement_headers = {**headers, "X-Reason": "Salida corporativa"}
    movement_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=movement_payload,
        headers=movement_headers,
    )
    assert movement_response.status_code == status.HTTP_201_CREATED

    refreshed_response = client.get(
        "/inventory/availability",
        headers=headers,
        params={"sku": [sku]},
    )
    assert refreshed_response.status_code == status.HTTP_200_OK
    refreshed_total = refreshed_response.json()["items"][0]["total_quantity"]
    assert refreshed_total == 5
