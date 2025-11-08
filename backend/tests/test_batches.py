from datetime import datetime

from fastapi import status

from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "batch_admin",
        "password": "BatchSecure123*",
        "full_name": "Batch Admin",
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


def test_purchase_and_sale_batch_flow(client):
    token = _bootstrap_admin(client)
    auth_headers = {"Authorization": f"Bearer {token}"}
    reason_headers = {**auth_headers, "X-Reason": "Control de lotes"}

    # Crear sucursal y dispositivo de prueba
    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Lotes", "location": "CDMX", "timezone": "America/Mexico_City"},
        headers=auth_headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_response = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "LOT-001",
            "name": "Smartphone Lote",
            "quantity": 10,
            "unit_price": 1500,
            "costo_unitario": 900,
            "margen_porcentaje": 20,
        },
        headers=reason_headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED
    device_id = device_response.json()["id"]

    supplier_payload = {
        "name": "Proveedor Lotes",
        "contact_name": "Laura Lotes",
        "email": "lotes@proveedor.com",
    }
    supplier_response = client.post(
        "/suppliers",
        json=supplier_payload,
        headers=reason_headers,
    )
    assert supplier_response.status_code == status.HTTP_201_CREATED
    supplier_id = supplier_response.json()["id"]

    order_payload = {
        "store_id": store_id,
        "supplier": supplier_payload["name"],
        "items": [
            {"device_id": device_id, "quantity_ordered": 5, "unit_cost": 800},
        ],
    }
    order_response = client.post(
        "/purchases",
        json=order_payload,
        headers=reason_headers,
    )
    assert order_response.status_code == status.HTTP_201_CREATED
    order_id = order_response.json()["id"]

    batch_code = f"LOT-{datetime.utcnow().year}"
    receive_response = client.post(
        f"/purchases/{order_id}/receive",
        json={"items": [{"device_id": device_id, "quantity": 5, "batch_code": batch_code}]},
        headers=reason_headers,
    )
    assert receive_response.status_code == status.HTTP_200_OK

    batches_response = client.get(
        f"/suppliers/{supplier_id}/batches",
        headers=auth_headers,
        params={"limit": 10, "offset": 0},
    )
    assert batches_response.status_code == status.HTTP_200_OK
    batches = batches_response.json()
    assert len(batches) == 1
    assert batches[0]["batch_code"] == batch_code
    assert batches[0]["quantity"] == 5

    sale_payload = {
        "store_id": store_id,
        "payment_method": "EFECTIVO",
        "items": [
            {"device_id": device_id, "quantity": 2, "batch_code": batch_code},
        ],
    }
    sale_response = client.post(
        "/sales",
        json=sale_payload,
        headers={**auth_headers, "X-Reason": "Venta lote"},
    )
    assert sale_response.status_code == status.HTTP_201_CREATED

    batches_after_sale = client.get(
        f"/suppliers/{supplier_id}/batches",
        headers=auth_headers,
        params={"limit": 10, "offset": 0},
    )
    assert batches_after_sale.status_code == status.HTTP_200_OK
    updated_batch = batches_after_sale.json()[0]
    assert updated_batch["quantity"] == 3

    oversell_response = client.post(
        "/sales",
        json={
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [
                {"device_id": device_id, "quantity": 4, "batch_code": batch_code},
            ],
        },
        headers={**auth_headers, "X-Reason": "Venta lote"},
    )
    assert oversell_response.status_code == status.HTTP_409_CONFLICT

    missing_batch_response = client.post(
        "/sales",
        json={
            "store_id": store_id,
            "payment_method": "EFECTIVO",
            "items": [
                {"device_id": device_id, "quantity": 1, "batch_code": "LOTE-DESCONOCIDO"},
            ],
        },
        headers={**auth_headers, "X-Reason": "Venta lote"},
    )
    assert missing_batch_response.status_code == status.HTTP_404_NOT_FOUND

    final_batches = client.get(
        f"/suppliers/{supplier_id}/batches",
        headers=auth_headers,
        params={"limit": 10, "offset": 0},
    )
    assert final_batches.status_code == status.HTTP_200_OK
    assert final_batches.json()[0]["quantity"] == 3
