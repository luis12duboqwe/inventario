from fastapi import status

from backend.app.core.roles import ADMIN


def _create_store(
    client,
    headers: dict[str, str],
    *,
    name: str,
    location: str,
    timezone: str = "America/Mexico_City",
) -> int:
    payload = {"name": name, "location": location, "timezone": timezone}
    response = client.post("/stores", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def _create_device(
    client,
    headers: dict[str, str],
    *,
    store_id: int,
    sku: str,
    name: str,
    quantity: int = 1,
    unit_price: float = 1000.0,
    imei: str | None = None,
    serial: str | None = None,
) -> int:
    payload: dict[str, object] = {
        "sku": sku,
        "name": name,
        "quantity": quantity,
        "unit_price": unit_price,
    }
    if imei is not None:
        payload["imei"] = imei
    if serial is not None:
        payload["serial"] = serial
    response = client.post(
        f"/stores/{store_id}/devices",
        json=payload,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


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

    store_id = _create_store(
        client,
        headers,
        name="Sucursal IMEI",
        location="CDMX",
    )

    device_id = _create_device(
        client,
        headers,
        store_id=store_id,
        sku="SKU-IMEI-001",
        name="Galaxy Ultra",
        quantity=3,
        unit_price=18500.0,
    )

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

    second_store_id = _create_store(
        client,
        headers,
        name="Sucursal Norte Identificadores",
        location="MTY",
        timezone="America/Monterrey",
    )

    second_device_id = _create_device(
        client,
        headers,
        store_id=second_store_id,
        sku="SKU-IMEI-002",
        name="Moto Edge",
        quantity=2,
        unit_price=9500.0,
    )

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


def test_device_creation_rejects_conflicts_from_identifier_table(client) -> None:
    headers = _auth_headers(client)

    store_id = _create_store(
        client,
        headers,
        name="Sucursal Identificadores Conflicto",
        location="GDL",
    )
    device_id = _create_device(
        client,
        headers,
        store_id=store_id,
        sku="SKU-CONFLICTO-0001",
        name="iPhone Identificador",
        quantity=1,
        unit_price=23500.0,
    )
    identifier_payload = {
        "imei_1": "490154203237534",
        "imei_2": "490154203237542",
        "numero_serie": "SERIE-CONFLICTO-01",
        "estado_tecnico": "Inspeccionado",
    }
    response = client.put(
        f"/inventory/stores/{store_id}/devices/{device_id}/identifier",
        json=identifier_payload,
        headers={**headers, "X-Reason": "Registro Identificadores"},
    )
    assert response.status_code == status.HTTP_200_OK

    imei_conflict_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "SKU-CONFLICTO-0002",
            "name": "Galaxy Conflicto",
            "quantity": 2,
            "unit_price": 12500.0,
            "imei": identifier_payload["imei_2"],
        },
        headers=headers,
    )
    assert imei_conflict_response.status_code == status.HTTP_409_CONFLICT
    imei_detail = imei_conflict_response.json()
    assert imei_detail["detail"]["code"] == "device_identifier_conflict"

    serial_conflict_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "SKU-CONFLICTO-0003",
            "name": "Pixel Conflicto",
            "quantity": 1,
            "unit_price": 9800.0,
            "serial": identifier_payload["numero_serie"],
        },
        headers=headers,
    )
    assert serial_conflict_response.status_code == status.HTTP_409_CONFLICT
    serial_detail = serial_conflict_response.json()
    assert serial_detail["detail"]["code"] == "device_identifier_conflict"
