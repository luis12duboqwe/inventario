"""Pruebas de integración para variantes de producto y combos."""
from __future__ import annotations

from decimal import Decimal
from datetime import date

import pytest
from fastapi import status

from backend.app import crud, schemas
from backend.app.config import settings
from backend.app.core.roles import ADMIN


@pytest.fixture()
def variants_feature() -> None:
    previous_variants = settings.enable_variants
    previous_bundles = settings.enable_bundles
    settings.enable_variants = True
    settings.enable_bundles = True
    try:
        yield
    finally:
        settings.enable_variants = previous_variants
        settings.enable_bundles = previous_bundles


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "variants_admin",
        "password": "Seguro123*",
        "full_name": "Gestor Variantes",
        "roles": [ADMIN],
    }
    bootstrap_response = client.post("/auth/bootstrap", json=payload)
    assert bootstrap_response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    token = token_response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Reason": "Gestión corporativa",
    }


def _create_store(db_session) -> int:
    store = crud.create_store(
        db_session,
        schemas.StoreCreate(
            name="Sucursal Variantes",
            location="Centro",
            phone=None,
            manager=None,
            status="activa",
            timezone="UTC",
            code=None,
        ),
        performed_by_id=None,
    )
    return store.id


def _create_device(db_session, store_id: int, sku: str) -> int:
    device = crud.create_device(
        db_session,
        store_id,
        schemas.DeviceCreate(
            sku=sku,
            name="Dispositivo de prueba",
            quantity=10,
            unit_price=Decimal("199.99"),
            costo_unitario=Decimal("120.00"),
            margen_porcentaje=Decimal("0"),
            garantia_meses=0,
            fecha_compra=date.today(),
        ),
        performed_by_id=None,
    )
    return device.id


def test_product_variant_crud_flow(client, db_session, variants_feature) -> None:
    headers = _auth_headers(client)
    store_id = _create_store(db_session)
    device_id = _create_device(db_session, store_id, sku="SKU-VAR-001")

    create_response = client.post(
        f"/inventory/devices/{device_id}/variants",
        json={
            "name": "Color azul",
            "variant_sku": "SKU-VAR-001-AZ",
            "barcode": "1234567890123",
            "unit_price_override": "209.99",
            "is_default": True,
        },
        headers=headers,
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    variant_data = create_response.json()
    assert variant_data["device_id"] == device_id
    assert variant_data["is_default"] is True

    list_response = client.get(
        f"/inventory/variants?store_id={store_id}",
        headers={k: v for k, v in headers.items() if k != "X-Reason"},
    )
    assert list_response.status_code == status.HTTP_200_OK
    listed = list_response.json()
    assert any(entry["variant_sku"] == "SKU-VAR-001-AZ" for entry in listed)

    update_response = client.patch(
        f"/inventory/variants/{variant_data['id']}",
        json={"barcode": "1234567890999", "is_active": True},
        headers=headers,
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated = update_response.json()
    assert updated["barcode"] == "1234567890999"

    archive_response = client.delete(
        f"/inventory/variants/{variant_data['id']}",
        headers=headers,
    )
    assert archive_response.status_code == status.HTTP_200_OK
    archived = archive_response.json()
    assert archived["is_active"] is False


def test_product_bundle_crud_flow(client, db_session, variants_feature) -> None:
    headers = _auth_headers(client)
    store_id = _create_store(db_session)
    device_id = _create_device(db_session, store_id, sku="SKU-BUNDLE-001")

    variant_response = client.post(
        f"/inventory/devices/{device_id}/variants",
        json={
            "name": "128 GB",
            "variant_sku": "SKU-BUNDLE-001-128",
            "is_default": False,
        },
        headers=headers,
    )
    assert variant_response.status_code == status.HTTP_201_CREATED
    variant_id = variant_response.json()["id"]

    create_bundle = client.post(
        "/inventory/bundles",
        json={
            "store_id": store_id,
            "name": "Combo lanzamiento",
            "bundle_sku": "COMBO-001",
            "base_price": "349.90",
            "items": [
                {
                    "device_id": device_id,
                    "variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
        headers=headers,
    )
    assert create_bundle.status_code == status.HTTP_201_CREATED
    bundle_data = create_bundle.json()
    assert bundle_data["store_id"] == store_id
    assert len(bundle_data["items"]) == 1

    list_bundles = client.get(
        f"/inventory/bundles?store_id={store_id}",
        headers={k: v for k, v in headers.items() if k != "X-Reason"},
    )
    assert list_bundles.status_code == status.HTTP_200_OK
    assert list_bundles.json()[0]["bundle_sku"] == "COMBO-001"

    update_bundle = client.patch(
        f"/inventory/bundles/{bundle_data['id']}",
        json={
            "name": "Combo especial",
            "items": [
                {
                    "device_id": device_id,
                    "variant_id": variant_id,
                    "quantity": 2,
                }
            ],
        },
        headers=headers,
    )
    assert update_bundle.status_code == status.HTTP_200_OK
    assert update_bundle.json()["name"] == "Combo especial"
    assert update_bundle.json()["items"][0]["quantity"] == 2

    archive_bundle = client.delete(
        f"/inventory/bundles/{bundle_data['id']}",
        headers=headers,
    )
    assert archive_bundle.status_code == status.HTTP_200_OK
    assert archive_bundle.json()["is_active"] is False


def test_create_bundle_requires_reason_header(client, db_session, variants_feature) -> None:
    store_id = _create_store(db_session)
    device_id = _create_device(db_session, store_id, sku="SKU-NO-REASON")
    headers = _auth_headers(client)

    missing_reason = {k: v for k, v in headers.items() if k != "X-Reason"}
    response = client.post(
        "/inventory/bundles",
        json={
            "store_id": store_id,
            "name": "Combo sin motivo",
            "bundle_sku": "COMBO-NO-REASON",
            "items": [{"device_id": device_id, "quantity": 1}],
        },
        headers=missing_reason,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
