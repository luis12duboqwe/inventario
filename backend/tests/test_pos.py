from sqlalchemy import select

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client, db_session):
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

    user = db_session.execute(
        select(models.User).where(models.User.username == payload["username"])
    ).scalar_one()
    return token, user.id


def test_pos_sale_with_receipt_and_config(client, db_session):
    settings.enable_purchases_sales = True
    token, user_id = _bootstrap_admin(client, db_session)
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
