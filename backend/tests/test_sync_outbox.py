from fastapi import status

from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client):
    payload = {
        "username": "sync_admin",
        "password": "Sync123*",
        "full_name": "Sync Admin",
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


def test_sync_outbox_list_and_retry(client):
    settings.enable_hybrid_prep = True
    settings.enable_purchases_sales = True
    token = _bootstrap_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal Sync", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_resp = client.post(
        f"/stores/{store_id}/devices",
        json={
            "sku": "SYNC-001",
            "name": "Router Sync",
            "quantity": 5,
            "unit_price": 800.0,
            "costo_unitario": 500.0,
            "margen_porcentaje": 15.0,
        },
        headers=headers,
    )
    assert device_resp.status_code == status.HTTP_201_CREATED
    device_id = device_resp.json()["id"]

    sale_resp = client.post(
        "/sales",
        json={"store_id": store_id, "payment_method": "EFECTIVO", "items": [{"device_id": device_id, "quantity": 1}]},
        headers={**headers, "X-Reason": "Venta sincronizacion"},
    )
    assert sale_resp.status_code == status.HTTP_201_CREATED

    outbox_response = client.get(
        "/sync/outbox",
        headers=headers,
        params={"limit": 200, "offset": 0},
    )
    assert outbox_response.status_code == status.HTTP_200_OK
    entries = outbox_response.json()
    assert entries
    entry_id = entries[0]["id"]
    assert entries[0]["priority"] == "HIGH"

    retry_response = client.post(
        "/sync/outbox/retry",
        json={"ids": [entry_id]},
        headers={**headers, "X-Reason": "Reintento local"},
    )
    assert retry_response.status_code == status.HTTP_200_OK
    assert retry_response.json()[0]["attempt_count"] == 0

    stats_response = client.get(
        "/sync/outbox/stats",
        headers=headers,
        params={"limit": 200, "offset": 0},
    )
    assert stats_response.status_code == status.HTTP_200_OK
    stats = stats_response.json()
    assert any(item["priority"] == "HIGH" for item in stats)
    assert all("conflicts" in item for item in stats)

    settings.enable_hybrid_prep = False
    settings.enable_purchases_sales = False
