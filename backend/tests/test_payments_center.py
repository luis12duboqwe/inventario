from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "payments_admin",
        "password": "Pagos1234*",
        "full_name": "Pagos Admin",
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


def test_payments_center_flow(client):
    previous_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}
        reason_headers = {**auth_headers, "X-Reason": "Centro pagos"}

        store_response = client.post(
            "/stores",
            json={"name": "Sucursal Pagos", "location": "CDMX", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SKU-PAGOS-01",
                "name": "Dispositivo Pagos",
                "quantity": 10,
                "unit_price": 250.0,
                "costo_unitario": 180.0,
                "margen_porcentaje": 10.0,
            },
            headers=auth_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        customer_response = client.post(
            "/customers",
            json={
                "name": "Cliente Pagador",
                "phone": "555-000-0000",
                "customer_type": "corporativo",
                "status": "activo",
                "credit_limit": 2000.0,
            },
            headers=reason_headers,
        )
        assert customer_response.status_code == status.HTTP_201_CREATED
        customer_id = customer_response.json()["id"]

        sale_response = client.post(
            "/sales",
            json={
                "store_id": store_id,
                "customer_id": customer_id,
                "payment_method": "CREDITO",
                "items": [{"device_id": device_id, "quantity": 1}],
                "notes": "Venta centro pagos",
            },
            headers={**auth_headers, "X-Reason": "Venta centro pagos"},
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["id"]

        payment_payload = {
            "customer_id": customer_id,
            "amount": 80.0,
            "method": "CARD",
            "reference": "PAGO-001",
            "sale_id": sale_id,
        }
        payment_response = client.post(
            "/payments/center/payment",
            json=payment_payload,
            headers=reason_headers,
        )
        assert payment_response.status_code == status.HTTP_201_CREATED
        payment_data = payment_response.json()
        assert payment_data["ledger_entry"]["details"]["sale_id"] == sale_id
        assert payment_data["receipt_pdf_base64"]

        refund_payload = {
            "customer_id": customer_id,
            "amount": 30.0,
            "method": "CASH",
            "reason": "DEFECT",
            "note": "Reembolso parcial",
            "sale_id": sale_id,
        }
        refund_response = client.post(
            "/payments/center/refund",
            json=refund_payload,
            headers=reason_headers,
        )
        assert refund_response.status_code == status.HTTP_201_CREATED

        credit_payload = {
            "customer_id": customer_id,
            "lines": [
                {"description": "Ajuste precio", "quantity": 1, "amount": 20.0},
            ],
            "total": 20.0,
            "note": "Nota crédito convenio",
            "sale_id": sale_id,
        }
        credit_response = client.post(
            "/payments/center/credit-note",
            json=credit_payload,
            headers=reason_headers,
        )
        assert credit_response.status_code == status.HTTP_201_CREATED

        overview_response = client.get(
            "/payments/center",
            headers=auth_headers,
        )
        assert overview_response.status_code == status.HTTP_200_OK
        payload = overview_response.json()
        assert payload["summary"]["collections_month"] >= 80.0
        assert payload["summary"]["refunds_month"] >= 30.0
        assert any(tx["type"] == "PAYMENT" for tx in payload["transactions"])
        assert any(tx["type"] == "REFUND" for tx in payload["transactions"])
        assert any(tx["type"] == "CREDIT_NOTE" for tx in payload["transactions"])

        customer_detail = client.get(
            f"/customers/{customer_id}", headers=auth_headers
        )
        assert customer_detail.status_code == status.HTTP_200_OK
        outstanding = customer_detail.json()["outstanding_debt"]
        assert outstanding >= 0
        assert outstanding < sale_response.json()["total_amount"]
    finally:
        settings.enable_purchases_sales = previous_flag

