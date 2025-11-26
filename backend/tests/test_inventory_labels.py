from __future__ import annotations

import io
from decimal import Decimal

from fastapi import status

from backend.app import crud, models, schemas
from backend.app.services import inventory_labels


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


def test_device_label_deduplicates_identifiers(db_session):
    store = crud.create_store(
        db_session,
        schemas.StoreCreate(name="Sucursal Duplicada", timezone="UTC"),
    )
    device = crud.create_device(
        db_session,
        store_id=store.id,
        payload=schemas.DeviceCreate(
            sku="SKU-DEDUP",
            name="Equipo Duplicado",
            quantity=1,
            unit_price=Decimal("999.99"),
            costo_unitario=Decimal("699.99"),
            marca="Marca Test",
            modelo="Modelo Test",
            color="Negro",
            imei="111222333444555",
            serial="SER-12345",
            completo=True,
        ),
    )

    crud.upsert_device_identifier(
        db_session,
        store_id=store.id,
        device_id=device.id,
        payload=schemas.DeviceIdentifierRequest(
            imei_1="111222333444555",
            imei_2="666777888999000",
            numero_serie="SER-12345",
            estado_tecnico=None,
            observaciones=None,
        ),
    )

    db_session.expire_all()
    device_with_identifiers = db_session.get(models.Device, device.id)
    assert device_with_identifiers is not None

    lines = inventory_labels._collect_identifier_lines(device_with_identifiers)
    assert lines == [
        "IMEI: 111222333444555",
        "SERIE: SER-12345",
        "IMEI 2: 666777888999000",
    ]

    pdf_bytes, filename = inventory_labels.render_device_label_pdf(
        db_session,
        store_id=store.id,
        device_id=device.id,
    )

    assert _pdf_starts_with_header(pdf_bytes)
    assert filename == f"etiqueta_{store.id}_{device.sku}.pdf"
