from __future__ import annotations

import io

from fastapi import status


def _pdf_starts_with_header(content: bytes) -> bool:
    return content.startswith(b"%PDF")


def _bootstrap_admin(client):
    payload = {
        "username": "labels_admin",
        "password": "Labels123*",
        "full_name": "Labels Admin",
        "roles": ["ADMIN"],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    token = token_response.json()["access_token"]
    return token


def test_device_label_pdf_generation(client):
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}",
               "X-Reason": "Etiqueta dispositivo"}

    # 2) Crear una sucursal
    store_resp = client.post(
        "/stores",
        json={"name": "Sucursal Centro", "code": "SUC-001"},
        headers=headers,
    )
    assert store_resp.status_code == 201
    store_id = store_resp.json()["id"]

    # 3) Crear un dispositivo
    device_resp = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "SKU-100",
            "name": "Telefono Demo",
            "quantity": 5,
            "precio_venta": 199.99,
            "imei": "123456789012345",
            "serial": "SER-0001",
        },
        headers=headers,
    )
    assert device_resp.status_code == 201
    device_id = device_resp.json()["id"]

    # 4) Generar la etiqueta PDF
    label_resp = client.get(
        f"/inventory/stores/{store_id}/devices/{device_id}/label/pdf",
        headers=headers,
    )
    assert label_resp.status_code == 200
    assert label_resp.headers.get(
        "Content-Type", "").startswith("application/pdf")
    content = label_resp.content
    assert _pdf_starts_with_header(content)
