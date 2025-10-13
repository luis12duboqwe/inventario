from sqlalchemy import select
from starlette import status

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "transfer_admin",
        "password": "Transfer123*",
        "full_name": "Transfer Admin",
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

    user = db_session.execute(
        select(models.User).where(models.User.username == payload["username"])
    ).scalar_one()
    return token, user.id


def test_full_transfer_flow(client, db_session):
    settings.enable_transfers = True
    token, user_id = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    store_norte = client.post(
        "/stores",
        json={"name": "Norte", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_norte.status_code == status.HTTP_201_CREATED
    store_norte_id = store_norte.json()["id"]

    store_sur = client.post(
        "/stores",
        json={"name": "Sur", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_sur.status_code == status.HTTP_201_CREATED
    store_sur_id = store_sur.json()["id"]

    # otorgar permisos por tienda
    membership_payload = {
        "user_id": user_id,
        "store_id": store_norte_id,
        "can_create_transfer": True,
        "can_receive_transfer": False,
    }
    membership_response = client.put(
        f"/stores/{store_norte_id}/memberships/{user_id}",
        json=membership_payload,
        headers=headers,
    )
    assert membership_response.status_code == status.HTTP_200_OK

    membership_dest_payload = {
        "user_id": user_id,
        "store_id": store_sur_id,
        "can_create_transfer": False,
        "can_receive_transfer": True,
    }
    membership_dest_response = client.put(
        f"/stores/{store_sur_id}/memberships/{user_id}",
        json=membership_dest_payload,
        headers=headers,
    )
    assert membership_dest_response.status_code == status.HTTP_200_OK

    device_payload = {
        "sku": "SKU-TR-001",
        "name": "Router empresarial",
        "quantity": 5,
        "unit_price": 1500.0,
        "costo_unitario": 1000.0,
        "margen_porcentaje": 10.0,
    }
    device_response = client.post(
        f"/stores/{store_norte_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    transfer_payload = {
        "origin_store_id": store_norte_id,
        "destination_store_id": store_sur_id,
        "reason": "Reabastecimiento Sur",
        "items": [
            {"device_id": device_id, "quantity": 2},
        ],
    }
    reason_headers = {**headers, "X-Reason": "Transferencia corporativa"}
    create_transfer = client.post("/transfers", json=transfer_payload, headers=reason_headers)
    assert create_transfer.status_code == status.HTTP_201_CREATED
    transfer_id = create_transfer.json()["id"]
    assert create_transfer.json()["status"] == "SOLICITADA"

    dispatch_response = client.post(
        f"/transfers/{transfer_id}/dispatch",
        json={"reason": "Salida autorizada"},
        headers=reason_headers,
    )
    assert dispatch_response.status_code == status.HTTP_200_OK
    assert dispatch_response.json()["status"] == "EN_TRANSITO"

    receive_response = client.post(
        f"/transfers/{transfer_id}/receive",
        json={"reason": "Ingreso completado"},
        headers=reason_headers,
    )
    assert receive_response.status_code == status.HTTP_200_OK
    data = receive_response.json()
    assert data["status"] == "RECIBIDA"
    assert data["received_at"] is not None

    origen_devices = client.get(f"/stores/{store_norte_id}/devices", headers=headers)
    assert origen_devices.status_code == status.HTTP_200_OK
    origen_qty = next(item for item in origen_devices.json() if item["id"] == device_id)["quantity"]
    assert origen_qty == 3

    destino_devices = client.get(f"/stores/{store_sur_id}/devices", headers=headers)
    assert destino_devices.status_code == status.HTTP_200_OK
    transferred = next(item for item in destino_devices.json() if item["sku"] == "SKU-TR-001")
    assert transferred["quantity"] == 2

    settings.enable_transfers = False


def test_transfer_without_membership_forbidden(client, db_session):
    settings.enable_transfers = True
    token, user_id = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    origen = client.post(
        "/stores",
        json={"name": "Centro", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    destino = client.post(
        "/stores",
        json={"name": "Occidente", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert origen.status_code == status.HTTP_201_CREATED
    assert destino.status_code == status.HTTP_201_CREATED

    device_payload = {
        "sku": "SKU-TR-002",
        "name": "Switch", "quantity": 1,
        "unit_price": 700.0,
        "costo_unitario": 500.0,
        "margen_porcentaje": 5.0,
    }
    device = client.post(
        f"/stores/{origen.json()['id']}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device.status_code == status.HTTP_201_CREATED

    transfer_payload = {
        "origin_store_id": origen.json()["id"],
        "destination_store_id": destino.json()["id"],
        "items": [{"device_id": device.json()["id"], "quantity": 1}],
    }
    response = client.post(
        "/transfers",
        json=transfer_payload,
        headers={**headers, "X-Reason": "Transfer sin permisos"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    settings.enable_transfers = False
