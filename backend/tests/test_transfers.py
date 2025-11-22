from sqlalchemy import select
from typing import Any, Iterable
from starlette import status

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _extract_items(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    return payload["items"]


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
    create_transfer = client.post(
        "/transfers",
        json=transfer_payload,
        headers={**headers, "X-Reason": "Crear transferencia"},
    )
    assert create_transfer.status_code == status.HTTP_201_CREATED
    transfer_id = create_transfer.json()["id"]
    assert create_transfer.json()["status"] == "SOLICITADA"

    dispatch_response = client.post(
        f"/transfers/{transfer_id}/dispatch",
        json={"reason": "Salida autorizada"},
        headers={**headers, "X-Reason": "Despachar transferencia"},
    )
    assert dispatch_response.status_code == status.HTTP_200_OK
    assert dispatch_response.json()["status"] == "EN_TRANSITO"

    receive_response = client.post(
        f"/transfers/{transfer_id}/receive",
        json={"reason": "Ingreso completado"},
        headers={**headers, "X-Reason": "Recibir transferencia"},
    )
    assert receive_response.status_code == status.HTTP_200_OK
    data = receive_response.json()
    assert data["status"] == "RECIBIDA"
    assert data["received_at"] is not None

    origen_devices = client.get(f"/stores/{store_norte_id}/devices", headers=headers)
    assert origen_devices.status_code == status.HTTP_200_OK
    origen_qty = next(
        item for item in _extract_items(origen_devices.json()) if item["id"] == device_id
    )["quantity"]
    assert origen_qty == 3

    destino_devices = client.get(f"/stores/{store_sur_id}/devices", headers=headers)
    assert destino_devices.status_code == status.HTTP_200_OK
    transferred = next(
        item
        for item in _extract_items(destino_devices.json())
        if item["sku"] == "SKU-TR-001"
    )
    assert transferred["quantity"] == 2

    settings.enable_transfers = False


def test_transfer_rejection_and_permissions(client, db_session):
    previous_flag = settings.enable_transfers
    settings.enable_transfers = True
    token, user_id = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    try:
        origin = client.post(
            "/stores",
            json={"name": "Origen Rechazo", "location": "MX", "timezone": "America/Mexico_City"},
            headers=headers,
        )
        destination = client.post(
            "/stores",
            json={"name": "Destino Rechazo", "location": "MX", "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert origin.status_code == status.HTTP_201_CREATED
        assert destination.status_code == status.HTTP_201_CREATED
        origin_id = origin.json()["id"]
        destination_id = destination.json()["id"]

        create_membership = client.put(
            f"/stores/{origin_id}/memberships/{user_id}",
            json={
                "user_id": user_id,
                "store_id": origin_id,
                "can_create_transfer": True,
                "can_receive_transfer": False,
            },
            headers=headers,
        )
        assert create_membership.status_code == status.HTTP_200_OK

        destination_membership = client.put(
            f"/stores/{destination_id}/memberships/{user_id}",
            json={
                "user_id": user_id,
                "store_id": destination_id,
                "can_create_transfer": False,
                "can_receive_transfer": False,
            },
            headers=headers,
        )
        assert destination_membership.status_code == status.HTTP_200_OK

        device = client.post(
            f"/stores/{origin_id}/devices",
            json={
                "sku": "SKU-RECH-001",
                "name": "Servidor Edge",
                "quantity": 2,
                "unit_price": 2100.0,
                "costo_unitario": 1500.0,
                "margen_porcentaje": 12.0,
            },
            headers=headers,
        )
        assert device.status_code == status.HTTP_201_CREATED
        device_id = device.json()["id"]

        transfer = client.post(
            "/transfers",
            json={
                "origin_store_id": origin_id,
                "destination_store_id": destination_id,
                "reason": "Balanceo de stock",
                "items": [{"device_id": device_id, "quantity": 1}],
            },
            headers={**headers, "X-Reason": "Transferencia a revisar"},
        )
        assert transfer.status_code == status.HTTP_201_CREATED
        transfer_id = transfer.json()["id"]

        dispatch = client.post(
            f"/transfers/{transfer_id}/dispatch",
            json={"reason": "Salida a ruta"},
            headers={**headers, "X-Reason": "Despacho en ruta"},
        )
        assert dispatch.status_code == status.HTTP_200_OK
        assert dispatch.json()["status"] == "EN_TRANSITO"

        reject_forbidden = client.post(
            f"/transfers/{transfer_id}/reject",
            json={"reason": "Destino sin permisos"},
            headers={**headers, "X-Reason": "Rechazo no autorizado"},
        )
        assert reject_forbidden.status_code == status.HTTP_403_FORBIDDEN

        enable_receive = client.put(
            f"/stores/{destination_id}/memberships/{user_id}",
            json={
                "user_id": user_id,
                "store_id": destination_id,
                "can_create_transfer": False,
                "can_receive_transfer": True,
            },
            headers=headers,
        )
        assert enable_receive.status_code == status.HTTP_200_OK

        rejection = client.post(
            f"/transfers/{transfer_id}/reject",
            json={"reason": "Mercancia dañada"},
            headers={**headers, "X-Reason": "Rechazo autorizado"},
        )
        assert rejection.status_code == status.HTTP_200_OK
        rejected_payload = rejection.json()
        assert rejected_payload["status"] == "RECHAZADA"
        assert rejected_payload["reason"] == "Mercancia dañada"

        origin_devices = client.get(f"/stores/{origin_id}/devices", headers=headers)
        origin_qty = next(
            item for item in _extract_items(origin_devices.json()) if item["id"] == device_id
        )["quantity"]
        assert origin_qty >= 1

        destination_devices = client.get(f"/stores/{destination_id}/devices", headers=headers)
        assert all(item["quantity"] == 0 for item in _extract_items(destination_devices.json()))
    finally:
        settings.enable_transfers = previous_flag


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
        headers={**headers, "X-Reason": "Transferencia sin permisos"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    settings.enable_transfers = False


def test_transfers_endpoints_return_404_when_feature_flag_disabled(client, db_session):
    settings.enable_transfers = True
    token, _ = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}", "X-Reason": "Verificar feature flag"}

    try:
        settings.enable_transfers = False

        list_response = client.get(
            "/transfers",
            headers=headers,
            params={"limit": 200, "offset": 0},
        )
        assert list_response.status_code == status.HTTP_404_NOT_FOUND

        create_payload = {
            "origin_store_id": 1,
            "destination_store_id": 2,
            "reason": "Motivo corporativo",
            "items": [{"device_id": 1, "quantity": 1}],
        }
        create_response = client.post("/transfers", json=create_payload, headers=headers)
        assert create_response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        settings.enable_transfers = True


def test_transfer_reception_rejects_sold_device(client, db_session):
    previous_flag = settings.enable_transfers
    settings.enable_transfers = True
    try:
        token, _ = _bootstrap_admin(client, db_session)
        headers = {"Authorization": f"Bearer {token}", "X-Reason": "Transferencia IMEI vendida"}

        origin_response = client.post(
            "/stores",
            json={"name": "Almacen Origen", "location": "MX", "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert origin_response.status_code == status.HTTP_201_CREATED
        origin_id = origin_response.json()["id"]

        destination_response = client.post(
            "/stores",
            json={"name": "Almacen Destino", "location": "MX", "timezone": "America/Mexico_City"},
            headers=headers,
        )
        assert destination_response.status_code == status.HTTP_201_CREATED
        destination_id = destination_response.json()["id"]

        user_id = db_session.execute(select(models.User.id)).scalar_one()

        membership_origin_payload = {
            "user_id": user_id,
            "store_id": origin_id,
            "can_create_transfer": True,
            "can_receive_transfer": False,
        }
        membership_origin_response = client.put(
            f"/stores/{origin_id}/memberships/{user_id}",
            json=membership_origin_payload,
            headers=headers,
        )
        assert membership_origin_response.status_code == status.HTTP_200_OK

        membership_destination_payload = {
            "user_id": user_id,
            "store_id": destination_id,
            "can_create_transfer": False,
            "can_receive_transfer": True,
        }
        membership_destination_response = client.put(
            f"/stores/{destination_id}/memberships/{user_id}",
            json=membership_destination_payload,
            headers=headers,
        )
        assert membership_destination_response.status_code == status.HTTP_200_OK

        device_response = client.post(
            f"/stores/{origin_id}/devices",
            json={
                "sku": "IMEI-TRANSFER-01",
                "name": "Telefono Transferencia",
                "quantity": 1,
                "unit_price": 1200.0,
                "costo_unitario": 800.0,
                "margen_porcentaje": 22.0,
                "imei": "356789012345679",
            },
            headers=headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        device_record = db_session.execute(
            select(models.Device).where(models.Device.id == device_id)
        ).scalar_one()
        device_record.estado = "vendido"
        db_session.commit()

        transfer_payload = {
            "origin_store_id": origin_id,
            "destination_store_id": destination_id,
            "reason": "Reubicacion de equipo",
            "items": [{"device_id": device_id, "quantity": 1}],
        }

        transfer_response = client.post("/transfers", json=transfer_payload, headers=headers)
        assert transfer_response.status_code == status.HTTP_201_CREATED
        transfer_id = transfer_response.json()["id"]

        dispatch_response = client.post(
            f"/transfers/{transfer_id}/dispatch",
            json={"reason": "Salida de almacen"},
            headers=headers,
        )
        assert dispatch_response.status_code == status.HTTP_200_OK

        receive_response = client.post(
            f"/transfers/{transfer_id}/receive",
            json={"reason": "Ingreso rechazado"},
            headers=headers,
        )

        assert receive_response.status_code == status.HTTP_409_CONFLICT
        assert (
            receive_response.json()["detail"]
            == "El dispositivo ya fue vendido y no puede transferirse."
        )
    finally:
        settings.enable_transfers = previous_flag
