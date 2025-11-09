from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "credits_admin",
        "password": "Creditos123*",
        "full_name": "Admin Créditos",
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


def test_issue_and_redeem_store_credit_flow(client):
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}", "X-Reason": "Operación QA"}

    customer_payload = {
        "name": "Cliente Notas",
        "phone": "+52 55 8888 0000",
        "customer_type": "corporativo",
        "status": "activo",
        "credit_limit": 500.0,
        "history": [],
    }
    create_customer = client.post("/customers", json=customer_payload, headers=auth_headers)
    assert create_customer.status_code == status.HTTP_201_CREATED
    customer_id = create_customer.json()["id"]

    issue_payload = {
        "customer_id": customer_id,
        "amount": 150.0,
        "notes": "Cortesía por devolución",
    }
    issue_response = client.post("/store-credits", json=issue_payload, headers=auth_headers)
    assert issue_response.status_code == status.HTTP_201_CREATED
    credit_data = issue_response.json()
    assert credit_data["customer_id"] == customer_id
    assert credit_data["issued_amount"] == 150.0
    assert credit_data["balance_amount"] == 150.0
    assert credit_data["status"] == "ACTIVO"

    redeem_payload = {
        "store_credit_id": credit_data["id"],
        "amount": 40.0,
        "notes": "Compra accesorios",
    }
    redeem_response = client.post("/store-credits/redeem", json=redeem_payload, headers=auth_headers)
    assert redeem_response.status_code == status.HTTP_200_OK
    redeemed_credit = redeem_response.json()
    assert redeemed_credit["balance_amount"] == 110.0
    assert redeemed_credit["status"] == "PARCIAL"

    list_response = client.get(
        f"/store-credits/by-customer/{customer_id}",
        headers={"Authorization": f"Bearer {token}", "X-Reason": "Consulta notas QA"},
    )
    assert list_response.status_code == status.HTTP_200_OK
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["code"] == credit_data["code"]
    assert items[0]["balance_amount"] == 110.0
    assert len(items[0]["redemptions"]) == 1
