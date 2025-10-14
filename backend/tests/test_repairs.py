from __future__ import annotations

from sqlalchemy import select
from starlette import status

from backend.app import models
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client, db_session):
    payload = {
        "username": "repair_admin",
        "password": "Repair123*",
        "full_name": "Repair Admin",
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


def test_repair_crud_flow(client, db_session):
    token, _ = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Taller Central", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    payload = {
        "store_id": store_id,
        "cliente": "María López",
        "dispositivo": "iPhone 14 Pro",
        "tipo_dano": "Pantalla rota",
        "tecnico": "Luis Pérez",
        "estado": "PENDIENTE",
        "costo": 2500.0,
        "piezas_usadas": ["Display OLED"],
        "fecha_inicio": "2024-01-10",
        "notas": "Ingresó con protector dañado",
    }
    create_response = client.post(
        "/repairs",
        json=payload,
        headers={**headers, "X-Reason": "Ingreso taller"},
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    repair_id = create_response.json()["id"]
    assert create_response.json()["estado"] == "PENDIENTE"

    pdf_response = client.get(f"/repairs/{repair_id}/pdf", headers=headers)
    assert pdf_response.status_code == status.HTTP_200_OK
    assert pdf_response.headers["content-type"] == "application/pdf"

    list_response = client.get(
        "/repairs",
        params={"store_id": store_id},
        headers=headers,
    )
    assert list_response.status_code == status.HTTP_200_OK
    assert any(item["id"] == repair_id for item in list_response.json())

    update_response = client.patch(
        f"/repairs/{repair_id}",
        json={"estado": "EN_REPARACION", "costo": 3200.0, "piezas_usadas": ["Display OLED", "Batería"]},
        headers={**headers, "X-Reason": "Actualizacion taller"},
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["estado"] == "EN_REPARACION"
    assert update_response.json()["piezas_usadas"] == ["Display OLED", "Batería"]

    delete_response = client.delete(
        f"/repairs/{repair_id}",
        headers={**headers, "X-Reason": "Cierre orden"},
    )
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    not_found = client.get(f"/repairs/{repair_id}", headers=headers)
    assert not_found.status_code == status.HTTP_404_NOT_FOUND


def test_repair_requires_reason_header(client, db_session):
    token, _ = _bootstrap_admin(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Taller", "location": "GDL", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    payload = {
        "store_id": store_id,
        "cliente": "Carlos Díaz",
        "dispositivo": "Samsung Galaxy S23",
        "tipo_dano": "Batería inflada",
        "tecnico": "Ana Romero",
        "costo": 1800.0,
        "piezas_usadas": ["Batería OEM"],
        "fecha_inicio": "2024-02-02",
    }

    missing_reason = client.post("/repairs", json=payload, headers=headers)
    assert missing_reason.status_code == status.HTTP_400_BAD_REQUEST
