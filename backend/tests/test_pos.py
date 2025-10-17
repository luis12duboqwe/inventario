from fastapi import status
from sqlalchemy import select

from backend.app.config import settings
from backend.app.core.roles import ADMIN, OPERADOR


def _bootstrap_admin(client):
    payload = {
        "username": "pos_admin",
        "password": "PosAdmin123*",
        "full_name": "POS Admin",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == 201

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    return token


def _bootstrap_operator(client, admin_token: str | None = None) -> str:
    if admin_token is None:
        admin_token = _bootstrap_admin(client)

    payload = {
        "username": "pos_operator",
        "password": "PosOperador123*",
        "full_name": "Operador POS",
        "roles": [OPERADOR],
    }
    response = client.post(
        "/users",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def test_pos_sale_with_receipt_and_config(client, db_session):
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "POS Centro", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == 201
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "POS-001",
        "name": "Smartphone POS",
        "quantity": 2,
        "unit_price": 100.0,
        "costo_unitario": 70.0,
        "margen_porcentaje": 10.0,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=auth_headers,
    )
    assert device_response.status_code == 201
    device_id = device_response.json()["id"]

    draft_payload = {
        "store_id": store_id,
        "payment_method": "EFECTIVO",
        "items": [{"device_id": device_id, "quantity": 1}],
        "confirm": False,
        "save_as_draft": True,
    }
    draft_response = client.post(
        "/pos/sale",
        json=draft_payload,
        headers={**auth_headers, "X-Reason": "Preparar venta POS"},
    )
    assert draft_response.status_code == 201
    draft_data = draft_response.json()
    assert draft_data["status"] == "draft"
    draft_id = draft_data["draft"]["id"]

    config_response = client.get(
        f"/pos/config?store_id={store_id}",
        headers=auth_headers,
    )
    assert config_response.status_code == 200
    default_config = config_response.json()
    assert default_config["store_id"] == store_id

    update_payload = {
        "store_id": store_id,
        "tax_rate": 16.0,
        "invoice_prefix": "POSCDMX",
        "printer_name": "TM-88V",
        "printer_profile": "USB",
        "quick_product_ids": [device_id],
    }
    update_response = client.put(
        "/pos/config",
        json=update_payload,
        headers={**auth_headers, "X-Reason": "Configurar POS"},
    )
    assert update_response.status_code == 200
    updated_config = update_response.json()
    assert updated_config["tax_rate"] == 16.0
    assert updated_config["invoice_prefix"] == "POSCDMX"

    sale_payload = {
        "store_id": store_id,
        "payment_method": "TARJETA",
        "discount_percent": 5.0,
        "customer_name": "Cliente POS",
        "items": [{"device_id": device_id, "quantity": 1, "discount_percent": 5.0}],
        "confirm": True,
        "draft_id": draft_id,
        "notes": "Venta mostrador",
    }
    sale_response = client.post(
        "/pos/sale",
        json=sale_payload,
        headers={**auth_headers, "X-Reason": "Finalizar venta POS"},
    )
    assert sale_response.status_code == 201
    sale_data = sale_response.json()
    assert sale_data["status"] == "registered"
    sale_info = sale_data["sale"]
    assert sale_info["payment_method"] == "TARJETA"
    assert sale_info["subtotal_amount"] == 95.0
    assert sale_info["tax_amount"] == 15.2
    assert sale_info["total_amount"] == 110.2
    assert any("Stock bajo" in message for message in sale_data["warnings"])

    receipt_response = client.get(
        f"/pos/receipt/{sale_info['id']}",
        headers=auth_headers,
    )
    assert receipt_response.status_code == 200
    assert receipt_response.headers["content-type"].startswith("application/pdf")
    assert len(receipt_response.content) > 100

    devices_after = client.get(f"/stores/{store_id}/devices", headers=auth_headers)
    assert devices_after.status_code == 200
    remaining = next(item for item in devices_after.json() if item["id"] == device_id)
    assert remaining["quantity"] == 1

    settings.enable_purchases_sales = False


def test_pos_cash_sessions_and_credit_sales(client, db_session):
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**auth_headers, "X-Reason": "Operacion POS"}

    store_response = client.post(
        "/stores",
        json={"name": "POS Sur", "location": "MTY", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == 201
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "POS-CR-001",
            "name": "Laptop Servicio",
            "quantity": 3,
            "unit_price": 200.0,
            "costo_unitario": 120.0,
        },
        headers=reason_headers,
    )
    assert device_response.status_code == 201
    device_id = device_response.json()["id"]

    customer_response = client.post(
        "/customers",
        json={
            "name": "Cliente Crédito",
            "email": "credito@example.com",
            "phone": "555-500-5000",
        },
        headers=reason_headers,
    )
    assert customer_response.status_code == 201
    customer_id = customer_response.json()["id"]

    open_response = client.post(
        "/pos/cash/open",
        json={"store_id": store_id, "opening_amount": 500.0, "notes": "Apertura"},
        headers=reason_headers,
    )
    assert open_response.status_code == 201
    session_id = open_response.json()["id"]

    sale_payload = {
        "store_id": store_id,
        "customer_id": customer_id,
        "payment_method": "CREDITO",
        "items": [{"device_id": device_id, "quantity": 1}],
        "confirm": True,
        "cash_session_id": session_id,
        "payment_breakdown": {"CREDITO": 200.0},
    }
    sale_response = client.post(
        "/pos/sale",
        json=sale_payload,
        headers=reason_headers,
    )
    assert sale_response.status_code == 201
    sale_data = sale_response.json()
    assert sale_data["sale"]["customer_id"] == customer_id
    assert sale_data["cash_session_id"] == session_id
    assert sale_data["payment_breakdown"]["CREDITO"] == 200.0

    customer_details = client.get(
        f"/customers/{customer_id}", headers=auth_headers
    )
    assert customer_details.status_code == 200
    assert customer_details.json()["outstanding_debt"] == 200.0

    close_response = client.post(
        "/pos/cash/close",
        json={
            "session_id": session_id,
            "closing_amount": 500.0,
            "payment_breakdown": {"CREDITO": 200.0},
            "notes": "Cierre turno",
        },
        headers=reason_headers,
    )
    assert close_response.status_code == 200
    session_data = close_response.json()
    assert session_data["status"] == "CERRADO"
    assert session_data["difference_amount"] == 0.0
    assert session_data["payment_breakdown"]["CREDITO"] == 200.0

    history_response = client.get(
        f"/pos/cash/history?store_id={store_id}", headers=auth_headers
    )
    assert history_response.status_code == 200
    assert any(item["id"] == session_id for item in history_response.json())

    settings.enable_purchases_sales = False


def test_pos_requires_auth_reason_and_roles(client):
    original_flag = settings.enable_purchases_sales
    settings.enable_purchases_sales = True
    try:
        sale_payload = {
            "store_id": 1,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": 1, "quantity": 1}],
            "confirm": True,
        }

        unauth_response = client.post("/pos/sale", json=sale_payload)
        assert unauth_response.status_code == status.HTTP_400_BAD_REQUEST

        admin_token = _bootstrap_admin(client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        store_response = client.post(
            "/stores",
            json={"name": "POS Validaciones", "location": "MX", "timezone": "America/Mexico_City"},
            headers=admin_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "POS-VALIDA-001",
                "name": "Impresora POS",
                "quantity": 5,
                "unit_price": 50.0,
                "costo_unitario": 25.0,
            },
            headers=admin_headers,
        )
        assert device_response.status_code == status.HTTP_201_CREATED
        device_id = device_response.json()["id"]

        payload = {
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": device_id, "quantity": 1}],
            "confirm": True,
        }

        missing_reason_response = client.post(
            "/pos/sale",
            json=payload,
            headers=admin_headers,
        )
        assert missing_reason_response.status_code == status.HTTP_400_BAD_REQUEST

        operator_token = _bootstrap_operator(client, admin_token)
        operator_headers = {
            "Authorization": f"Bearer {operator_token}",
            "X-Reason": "Intento POS",
        }

        forbidden_response = client.post(
            "/pos/sale",
            json=payload,
            headers=operator_headers,
        )
        assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN

        valid_headers = {**admin_headers, "X-Reason": "Venta Validada"}
        success_response = client.post(
            "/pos/sale",
            json=payload,
            headers=valid_headers,
        )
        assert success_response.status_code == status.HTTP_201_CREATED
    finally:
        settings.enable_purchases_sales = original_flag
