from sqlalchemy import select
from starlette import status

from backend.app import models
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "ajustes_admin",
        "password": "Ajuste123*",
        "full_name": "Ajustes QA",
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


def test_negative_adjustment_blocks_when_stock_is_insufficient(client, db_session):
    token = _bootstrap_admin(client)
    reason = "Ajuste negativo sin stock"
    headers = {"Authorization": f"Bearer {token}", "X-Reason": reason}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Ajustes", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "AJUSTE-001",
            "name": "Dispositivo Ajuste",
            "quantity": 1,
            "unit_price": 500.0,
            "costo_unitario": 320.0,
            "margen_porcentaje": 15.0,
        },
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    movement_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "salida",
        "cantidad": 2,
        "comentario": reason,
    }
    movement_response = client.post(
        f"/inventory/stores/{store_id}/movements", json=movement_payload, headers=headers
    )

    assert movement_response.status_code == status.HTTP_409_CONFLICT, movement_response.json()
    assert (
        movement_response.json()["detail"]
        == "Stock insuficiente para registrar la salida."
    )

    refreshed_device = db_session.execute(
        select(models.Device).where(models.Device.id == device_id)
    ).scalar_one()
    assert refreshed_device.quantity == 1


def test_negative_adjustment_rejects_sold_imei(client, db_session):
    token = _bootstrap_admin(client)
    reason = "Ajuste IMEI vendido"
    headers = {"Authorization": f"Bearer {token}", "X-Reason": reason}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Ajuste IMEI", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "AJUSTE-IMEI-01",
            "name": "Dispositivo IMEI",
            "quantity": 1,
            "unit_price": 700.0,
            "costo_unitario": 480.0,
            "margen_porcentaje": 17.0,
            "imei": "356789012345680",
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

    adjustment_payload = {
        "producto_id": device_id,
        "tipo_movimiento": "ajuste",
        "cantidad": 0,
        "comentario": reason,
    }
    adjustment_response = client.post(
        f"/inventory/stores/{store_id}/movements",
        json=adjustment_payload,
        headers=headers,
    )

    assert adjustment_response.status_code == status.HTTP_409_CONFLICT, adjustment_response.json()
    assert (
        adjustment_response.json()["detail"]
        == "El dispositivo ya fue vendido y no admite ajustes negativos."
    )

    refreshed_device = db_session.execute(
        select(models.Device).where(models.Device.id == device_id)
    ).scalar_one()
    assert refreshed_device.quantity == 1
