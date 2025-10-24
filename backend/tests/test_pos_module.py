from fastapi import status
import pytest

from backend.app.core.roles import ADMIN


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "pos_mod_admin",
        "password": "PosMod123*",
        "full_name": "Admin POS Mod",
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
    return {"Authorization": f"Bearer {token}", "X-Reason": "Operacion POS"}


def test_pos_sales_with_multi_payments(client) -> None:
    headers = _auth_headers(client)

    store_response = client.post(
        "/stores",
        json={"name": "POS Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    sale_response = client.post("/pos/sales", json={"store_id": store_id, "notes": "Venta mostrador"}, headers=headers)
    assert sale_response.status_code == status.HTTP_201_CREATED
    sale = sale_response.json()
    assert sale["status"] == "OPEN"
    sale_id = sale["id"]

    items_payload = {
        "items": [
            {
                "description": "Smartphone",
                "quantity": 2,
                "unit_price": 50.0,
                "discount_amount": 5.0,
                "tax_rate": 10.0,
            },
            {
                "description": "Protector",
                "quantity": 1,
                "unit_price": 30.0,
            },
        ]
    }
    items_response = client.post(f"/pos/sales/{sale_id}/items", json=items_payload, headers=headers)
    assert items_response.status_code == status.HTTP_201_CREATED
    sale_with_items = items_response.json()
    assert len(sale_with_items["items"]) == 2

    hold_response = client.post(f"/pos/sales/{sale_id}/hold", json={"reason": "Esperar cliente"}, headers=headers)
    assert hold_response.status_code == status.HTTP_200_OK
    assert hold_response.json()["status"] == "HELD"

    resume_response = client.post(f"/pos/sales/{sale_id}/resume", headers=headers)
    assert resume_response.status_code == status.HTTP_200_OK
    assert resume_response.json()["status"] == "OPEN"

    checkout_payload = {
        "payments": [
            {"method": "CASH", "amount": 80.0},
            {"method": "CARD", "amount": 54.5, "reference": "TARJ-001"},
        ]
    }
    checkout_response = client.post(f"/pos/sales/{sale_id}/checkout", json=checkout_payload, headers=headers)
    assert checkout_response.status_code == status.HTTP_200_OK
    completed = checkout_response.json()
    assert completed["status"] == "COMPLETED"
    assert completed["total_amount"] == pytest.approx(134.5)
    assert len(completed["payments"]) == 2

    receipt_response = client.get(f"/pos/receipt/{sale_id}", headers=headers)
    assert receipt_response.status_code == status.HTTP_200_OK
    receipt = receipt_response.json()
    assert receipt["status"] == "COMPLETED"
    assert receipt["total_amount"] == pytest.approx(completed["total_amount"])
    assert receipt["payments"][0]["method"] in {"CASH", "CARD"}

    void_sale_response = client.post(f"/pos/sales/{sale_id}/void", json={"reason": "No procede"}, headers=headers)
    assert void_sale_response.status_code == status.HTTP_409_CONFLICT

    second_sale = client.post("/pos/sales", json={"store_id": store_id}, headers=headers)
    assert second_sale.status_code == status.HTTP_201_CREATED
    second_id = second_sale.json()["id"]
    void_response = client.post(f"/pos/sales/{second_id}/void", json={"reason": "Cancelada"}, headers=headers)
    assert void_response.status_code == status.HTTP_200_OK
    assert void_response.json()["status"] == "VOID"
