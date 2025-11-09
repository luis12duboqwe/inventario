from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import status

from backend.app import crud, schemas
from backend.app.config import settings
from backend.app.core.roles import ADMIN
from backend.app.models import Device


@pytest.fixture()
def price_list_feature() -> None:
    previous_value = settings.enable_price_lists
    settings.enable_price_lists = True
    try:
        yield
    finally:
        settings.enable_price_lists = previous_value


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "admin_price_lists",
        "password": "ClaveSegura123",
        "full_name": "Admin Listas",
        "roles": [ADMIN],
    }
    bootstrap_response = client.post("/auth/bootstrap", json=payload)
    assert bootstrap_response.status_code == status.HTTP_201_CREATED
"""Pruebas de integración para el módulo de listas de precios."""

from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client) -> str:
    payload = {
        "username": "pricing_admin",
        "password": "Pricing123*",
        "full_name": "Pricing Admin",
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
    return {
        "Authorization": f"Bearer {token}",
        "X-Reason": "Gestion listas de precios",
    }


def _create_store(db_session) -> int:
    store = crud.create_store(
        db_session,
        schemas.StoreCreate(
            name="Sucursal Centro",
            location=None,
            phone=None,
            manager=None,
            status="activa",
            timezone="UTC",
            code=None,
        ),
        performed_by_id=None,
    )
    return store.id


def _create_customer(db_session) -> int:
    customer = crud.create_customer(
        db_session,
        schemas.CustomerCreate(
            name="Cliente Prioritario",
            phone="5512340000",
            contact_name=None,
            email="prioritario@example.com",
            address=None,
            customer_type="minorista",
            status="activo",
            credit_limit=Decimal("0"),
            notes=None,
            outstanding_debt=Decimal("0"),
            history=[],
        ),
        performed_by_id=None,
    )
    return customer.id


def _create_device(db_session, store_id: int, sku: str) -> int:
    device = Device(
        store_id=store_id,
        sku=sku,
        name="Equipo Especial",
        quantity=1,
        unit_price=Decimal("150.00"),
        costo_unitario=Decimal("120.00"),
        margen_porcentaje=Decimal("0"),
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device.id


def test_create_price_list_endpoint(client, db_session, price_list_feature) -> None:
    headers = _auth_headers(client)
    today = date.today()
    payload = {
        "name": "Lista Primavera",
        "description": "Tarifas promocionales",
        "is_active": True,
        "store_id": None,
        "customer_id": None,
        "currency": "MXN",
        "valid_from": today.isoformat(),
        "valid_until": (today + timedelta(days=30)).isoformat(),
    }

    response = client.post("/price-lists", json=payload, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["currency"] == "MXN"
    assert data["is_active"] is True
    assert len(data["items"]) == 0


def test_assign_price_list_item_endpoint(client, db_session, price_list_feature) -> None:
    headers = _auth_headers(client)
    store_id = _create_store(db_session)
    device_id = _create_device(db_session, store_id, sku="SKU-PL-001")

    create_response = client.post(
        "/price-lists",
        json={
            "name": "Lista Asignaciones",
            "description": None,
            "is_active": True,
            "store_id": store_id,
            "customer_id": None,
            "currency": "MXN",
            "valid_from": None,
            "valid_until": None,
        },
        headers=headers,
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    price_list_id = create_response.json()["id"]

    item_response = client.post(
        f"/price-lists/{price_list_id}/items",
        json={
            "device_id": device_id,
            "price": "199.90",
            "discount_percentage": "5.0",
            "notes": "Oferta limitada",
        },
        headers=headers,
    )
    assert item_response.status_code == status.HTTP_201_CREATED
    item_data = item_response.json()
    assert item_data["device_id"] == device_id
    assert pytest.approx(item_data["price"], rel=1e-3) == 199.9
    assert item_data["discount_percentage"] == 5.0

    detail_response = client.get(f"/price-lists/{price_list_id}", headers=headers)
    assert detail_response.status_code == status.HTTP_200_OK
    detail = detail_response.json()
    assert len(detail["items"]) == 1
    assert detail["items"][0]["id"] == item_data["id"]


def test_price_resolution_prioritizes_specific_scope(
    client, db_session, price_list_feature
) -> None:
    headers = _auth_headers(client)
    store_id = _create_store(db_session)
    customer_id = _create_customer(db_session)
    device_id = _create_device(db_session, store_id, sku="SKU-PL-002")

    def _create_list(payload: dict[str, object]) -> dict[str, object]:
        response = client.post("/price-lists", json=payload, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
        return response.json()

    def _attach_item(list_id: int, price: str, discount: str | None) -> None:
        response = client.post(
            f"/price-lists/{list_id}/items",
            json={
                "device_id": device_id,
                "price": price,
                "discount_percentage": discount,
                "notes": None,
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_201_CREATED

    global_list = _create_list(
        {
            "name": "Global",
            "description": "Lista general",
            "is_active": True,
            "store_id": None,
            "customer_id": None,
            "currency": "MXN",
            "valid_from": None,
            "valid_until": None,
        }
    )
    _attach_item(global_list["id"], "220.00", None)

    store_list = _create_list(
        {
            "name": "Sucursal",
            "description": None,
            "is_active": True,
            "store_id": store_id,
            "customer_id": None,
            "currency": "MXN",
            "valid_from": None,
            "valid_until": None,
        }
    )
    _attach_item(store_list["id"], "205.00", None)

    customer_list = _create_list(
        {
            "name": "Cliente",
            "description": None,
            "is_active": True,
            "store_id": None,
            "customer_id": customer_id,
            "currency": "MXN",
            "valid_from": None,
            "valid_until": None,
        }
    )
    _attach_item(customer_list["id"], "198.00", "3.0")

    targeted_list = _create_list(
        {
            "name": "Acuerdo",
            "description": None,
            "is_active": True,
            "store_id": store_id,
            "customer_id": customer_id,
            "currency": "MXN",
            "valid_from": None,
            "valid_until": None,
        }
    )
    _attach_item(targeted_list["id"], "170.00", "10.0")

    resolution_response = client.get(
        "/price-lists/resolve",
        params={
            "device_id": device_id,
            "store_id": store_id,
            "customer_id": customer_id,
        },
        headers=headers,
    )

    assert resolution_response.status_code == status.HTTP_200_OK, resolution_response.json()
    resolution = resolution_response.json()
    assert resolution["price_list_id"] == targeted_list["id"]
    assert resolution["scope"] == "store_customer"
    assert pytest.approx(resolution["final_price"], rel=1e-3) == 153.0
    assert resolution["source"] == "price_list"

    return token_response.json()["access_token"]


def test_price_lists_priority_resolution(client):
    settings.enable_price_lists = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}
        reason_headers = {**auth_headers, "X-Reason": "Configurar listas de precio"}

        store_payload = {"name": "Sucursal Centro", "code": "CENTRO-1"}
        store_response = client.post("/stores", json=store_payload, headers=auth_headers)
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_payload = {
            "sku": "DEV-001",
            "name": "Smartphone X",
            "quantity": 10,
            "unit_price": 1000.0,
        }
        device_response = client.post(
            f"/stores/{store_id}/devices",
            json=device_payload,
            headers=reason_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        global_list_payload = {
            "name": "Lista Global",
            "priority": 100,
            "is_active": True,
        }
        list_response = client.post(
            "/pricing/price-lists",
            json=global_list_payload,
            headers=reason_headers,
        )
        assert list_response.status_code == status.HTTP_201_CREATED
        global_list_id = list_response.json()["id"]

        global_item_response = client.post(
            f"/pricing/price-lists/{global_list_id}/items",
            json={"device_id": device_id, "price": 950.0},
            headers=reason_headers,
        )
        assert global_item_response.status_code == status.HTTP_201_CREATED

        evaluation = client.get(
            "/pricing/price-evaluation",
            params={"device_id": device_id},
            headers=auth_headers,
        )
        assert evaluation.status_code == status.HTTP_200_OK
        assert evaluation.json()["price_list_id"] == global_list_id
        assert evaluation.json()["price"] == 950.0

        store_list_payload = {
            "name": "Lista Sucursal",
            "priority": 50,
            "store_id": store_id,
        }
        store_list_response = client.post(
            "/pricing/price-lists",
            json=store_list_payload,
            headers=reason_headers,
        )
        assert store_list_response.status_code == status.HTTP_201_CREATED
        store_list_id = store_list_response.json()["id"]

        store_item_response = client.post(
            f"/pricing/price-lists/{store_list_id}/items",
            json={"device_id": device_id, "price": 900.0},
            headers=reason_headers,
        )
        assert store_item_response.status_code == status.HTTP_201_CREATED

        evaluation_store = client.get(
            "/pricing/price-evaluation",
            params={"device_id": device_id, "store_id": store_id},
            headers=auth_headers,
        )
        assert evaluation_store.status_code == status.HTTP_200_OK
        assert evaluation_store.json()["price_list_id"] == store_list_id
        assert evaluation_store.json()["price"] == 900.0

        customer_payload = {
            "name": "Cliente Prioritario",
            "phone": "555-0101",
            "customer_type": "corporativo",
            "status": "activo",
            "credit_limit": 0,
            "history": [],
        }
        customer_response = client.post(
            "/customers",
            json=customer_payload,
            headers=reason_headers,
        )
        assert customer_response.status_code == status.HTTP_201_CREATED
        customer_id = customer_response.json()["id"]

        customer_list_payload = {
            "name": "Lista Cliente",
            "priority": 10,
            "store_id": store_id,
            "customer_id": customer_id,
        }
        customer_list_response = client.post(
            "/pricing/price-lists",
            json=customer_list_payload,
            headers=reason_headers,
        )
        assert customer_list_response.status_code == status.HTTP_201_CREATED
        customer_list_id = customer_list_response.json()["id"]

        customer_item_response = client.post(
            f"/pricing/price-lists/{customer_list_id}/items",
            json={"device_id": device_id, "price": 850.0},
            headers=reason_headers,
        )
        assert customer_item_response.status_code == status.HTTP_201_CREATED

        evaluation_customer = client.get(
            "/pricing/price-evaluation",
            params={
                "device_id": device_id,
                "store_id": store_id,
                "customer_id": customer_id,
            },
            headers=auth_headers,
        )
        assert evaluation_customer.status_code == status.HTTP_200_OK
        assert evaluation_customer.json()["price_list_id"] == customer_list_id
        assert evaluation_customer.json()["price"] == 850.0

        evaluation_other_customer = client.get(
            "/pricing/price-evaluation",
            params={
                "device_id": device_id,
                "store_id": store_id,
                "customer_id": customer_id + 1,
            },
            headers=auth_headers,
        )
        assert evaluation_other_customer.status_code == status.HTTP_200_OK
        assert evaluation_other_customer.json()["price_list_id"] == store_list_id
        assert evaluation_other_customer.json()["price"] == 900.0
    finally:
        settings.enable_price_lists = False


def test_price_lists_router_hidden_when_flag_disabled(client):
    settings.enable_price_lists = False

    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/pricing/price-lists", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
