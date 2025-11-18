from fastapi import status

from backend.app.config import settings


def _bootstrap_admin(client):
    payload = {
        "username": "lealtad_admin",
        "password": "Lealtad123*",
        "full_name": "Admin Lealtad",
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


def test_loyalty_account_earn_and_redeem_flow(client):
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_resp = client.post(
        "/stores",
        json={"name": "Sucursal Lealtad", "location": "HQ"},
        headers=auth_headers,
    )
    assert store_resp.status_code == status.HTTP_201_CREATED
    store_id = store_resp.json()["id"]

    device_resp = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "LOY-001",
            "name": "Dispositivo Lealtad",
            "quantity": 10,
            "unit_price": 50.0,
            "costo_unitario": 30.0,
            "margen_porcentaje": 20.0,
        },
        headers=auth_headers,
    )
    assert device_resp.status_code == status.HTTP_201_CREATED
    device_id = device_resp.json()["id"]

    customer_resp = client.post(
        "/customers",
        json={"name": "Cliente Leal", "email": "leal@example.com", "phone": "555-9999"},
        headers={**auth_headers, "X-Reason": "Alta cliente lealtad"},
    )
    assert customer_resp.status_code == status.HTTP_201_CREATED
    customer_id = customer_resp.json()["id"]

    first_sale_payload = {
        "store_id": store_id,
        "customer_id": customer_id,
        "payment_method": "EFECTIVO",
        "confirm": True,
        "apply_taxes": False,
        "items": [
            {"device_id": device_id, "quantity": 2},
        ],
    }
    first_sale = client.post(
        "/pos/sale",
        json=first_sale_payload,
        headers={**auth_headers, "X-Reason": "Venta con puntos"},
    )
    assert first_sale.status_code == status.HTTP_201_CREATED
    first_data = first_sale.json()
    assert first_data["status"] == "registered"
    loyalty_summary = first_data["loyalty_summary"]
    assert loyalty_summary is not None
    assert loyalty_summary["earned_points"] == 100.0
    assert loyalty_summary["balance_points"] == 100.0

    account_resp = client.get(
        f"/loyalty/accounts/{customer_id}",
        headers={**auth_headers, "X-Reason": "Revisar saldo"},
    )
    assert account_resp.status_code == status.HTTP_200_OK
    account_data = account_resp.json()
    assert account_data["balance_points"] == 100.0

    second_sale_payload = {
        "store_id": store_id,
        "customer_id": customer_id,
        "payment_method": "EFECTIVO",
        "confirm": True,
        "apply_taxes": False,
        "items": [
            {"device_id": device_id, "quantity": 1},
        ],
        "payments": [
            {"method": "PUNTOS", "amount": 40},
            {"method": "EFECTIVO", "amount": 10},
        ],
    }
    second_sale = client.post(
        "/pos/sale",
        json=second_sale_payload,
        headers={**auth_headers, "X-Reason": "Canjear puntos"},
    )
    assert second_sale.status_code == status.HTTP_201_CREATED
    second_data = second_sale.json()
    loyalty_summary_2 = second_data["loyalty_summary"]
    assert loyalty_summary_2 is not None
    assert loyalty_summary_2["redeemed_points"] == 40.0
    assert loyalty_summary_2["balance_points"] == 110.0

    report_resp = client.get(
        "/loyalty/reports/summary",
        headers={**auth_headers, "X-Reason": "Resumen lealtad"},
    )
    assert report_resp.status_code == status.HTTP_200_OK
    report_data = report_resp.json()
    assert report_data["total_accounts"] == 1
    assert report_data["active_accounts"] == 1
    assert report_data["total_balance"] == 110.0
    assert report_data["total_redeemed"] == 40.0
    assert report_data["total_earned"] == 150.0

    update_resp = client.put(
        f"/loyalty/accounts/{customer_id}",
        json={"accrual_rate": 1.5, "expiration_days": 180},
        headers={**auth_headers, "X-Reason": "Actualizar reglas"},
    )
    assert update_resp.status_code == status.HTTP_200_OK
    updated = update_resp.json()
    assert updated["accrual_rate"] == 1.5
    assert updated["expiration_days"] == 180
