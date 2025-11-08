from __future__ import annotations
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
