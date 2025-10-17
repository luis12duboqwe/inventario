from fastapi import status

from backend.app.core.roles import ADMIN


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "admin-imei",
        "password": "ClaveSegura456",
        "full_name": "Admin Inventario",
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
    return {"Authorization": f"Bearer {token}", "X-Reason": "Gestion IMEI"}


def test_device_identifier_upsert_and_uniqueness(client) -> None:
    headers = _auth_headers(client)

    store_payload = {"name": "Sucursal IMEI", "location": "CDMX", "timezone": "America/Mexico_City"}
    store_response = client.post("/stores", json=store_payload, headers=headers)
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "SKU-IMEI-001",
        "name": "Galaxy Ultra",
        "quantity": 3,
        "unit_price": 18500.0,
    }
    device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    identifier_payload = {
        "imei_1": "490154203237518",
        "imei_2": "490154203237526",
        "numero_serie": "SERIE-EXT-0001",
        "estado_tecnico": "Revisado",
        "observaciones": "Sin daños visibles",
    }
    upsert_headers = {**headers, "X-Reason": "Registro IMEI principal"}
    upsert_response = client.put(
        f"/inventory/stores/{store_id}/devices/{device_id}/identifier",
        json=identifier_payload,
        headers=upsert_headers,
    )
    assert upsert_response.status_code == status.HTTP_200_OK
    identifier_data = upsert_response.json()
    assert identifier_data["imei_1"] == identifier_payload["imei_1"]
    assert identifier_data["estado_tecnico"] == identifier_payload["estado_tecnico"]

    retrieve_response = client.get(
        f"/inventory/stores/{store_id}/devices/{device_id}/identifier",
        headers=headers,
    )
    assert retrieve_response.status_code == status.HTTP_200_OK
    retrieved = retrieve_response.json()
    assert retrieved["numero_serie"] == identifier_payload["numero_serie"]

    devices_response = client.get(f"/stores/{store_id}/devices", headers=headers)
    assert devices_response.status_code == status.HTTP_200_OK
    device_list = devices_response.json()
    assert device_list[0]["identifier"]["imei_1"] == identifier_payload["imei_1"]
    assert device_list[0]["identifier"]["estado_tecnico"] == identifier_payload["estado_tecnico"]

    second_store_payload = {
        "name": "Sucursal Norte Identificadores",
        "location": "MTY",
        "timezone": "America/Monterrey",
    }
    second_store_response = client.post("/stores", json=second_store_payload, headers=headers)
    assert second_store_response.status_code == status.HTTP_201_CREATED
    second_store_id = second_store_response.json()["id"]

    second_device_payload = {
        "sku": "SKU-IMEI-002",
        "name": "Moto Edge",
        "quantity": 2,
        "unit_price": 9500.0,
    }
    second_device_response = client.post(
        f"/stores/{second_store_id}/devices",
        json=second_device_payload,
        headers=headers,
    )
    assert second_device_response.status_code == status.HTTP_201_CREATED
    second_device_id = second_device_response.json()["id"]

    duplicate_headers = {**headers, "X-Reason": "Duplicado IMEI"}
    duplicate_payload = {"imei_1": identifier_payload["imei_1"]}
    duplicate_response = client.put(
        f"/inventory/stores/{second_store_id}/devices/{second_device_id}/identifier",
        json=duplicate_payload,
        headers=duplicate_headers,
    )
    assert duplicate_response.status_code == status.HTTP_409_CONFLICT

    serial_conflict_headers = {**headers, "X-Reason": "Serial conflictivo"}
    serial_conflict_payload = {"serial": identifier_payload["numero_serie"]}
    serial_conflict_response = client.patch(
        f"/inventory/stores/{second_store_id}/devices/{second_device_id}",
        json=serial_conflict_payload,
        headers=serial_conflict_headers,
    )
    assert serial_conflict_response.status_code == status.HTTP_409_CONFLICT

    missing_identifier_response = client.get(
        f"/inventory/stores/{second_store_id}/devices/{second_device_id}/identifier",
        headers=headers,
    )
    assert missing_identifier_response.status_code == status.HTTP_404_NOT_FOUND
