from fastapi import status

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _bootstrap_admin(client) -> str:
    payload = {
        "username": "sync_admin",
        "password": "SyncFull123*",
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


def test_full_sync_outbox_for_sales_and_repairs(client, db_session):
    original_hybrid = settings.enable_hybrid_prep
    original_sales = settings.enable_purchases_sales
    settings.enable_hybrid_prep = True
    settings.enable_purchases_sales = True

    try:
        token = _bootstrap_admin(client)
        auth_headers = {"Authorization": f"Bearer {token}"}
        reason_headers = {**auth_headers, "X-Reason": "Sincronizacion Integral"}

        store_response = client.post(
            "/stores",
            json={"name": "Sync Completo", "location": "CDMX", "timezone": "America/Mexico_City"},
            headers=auth_headers,
        )
        assert store_response.status_code == status.HTTP_201_CREATED
        store_id = store_response.json()["id"]

        sale_device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SYNC-VENTA-001",
                "name": "Telefono Sync Venta",
                "quantity": 6,
                "unit_price": 350.0,
                "costo_unitario": 200.0,
                "margen_porcentaje": 15.0,
            },
            headers=auth_headers,
        )
        assert sale_device_response.status_code == status.HTTP_201_CREATED
        sale_device_id = sale_device_response.json()["id"]

        part_device_response = client.post(
            f"/stores/{store_id}/devices",
            json={
                "sku": "SYNC-REPARA-001",
                "name": "Pantalla Sync",
                "quantity": 8,
                "unit_price": 250.0,
                "costo_unitario": 120.0,
            },
            headers=auth_headers,
        )
        assert part_device_response.status_code == status.HTTP_201_CREATED
        part_device_id = part_device_response.json()["id"]

        customer_payload = {
            "name": "Cliente Sync",
            "email": "sync@example.com",
            "phone": "555-222-3333",
        }
        customer_response = client.post(
            "/customers",
            json=customer_payload,
            headers=reason_headers,
        )
        assert customer_response.status_code == status.HTTP_201_CREATED
        customer_id = customer_response.json()["id"]

        config_payload = {
            "store_id": store_id,
            "tax_rate": 16.0,
            "invoice_prefix": "SYNCFULL",
            "printer_name": "IMP-SYNC",
            "printer_profile": "USB",
            "quick_product_ids": [sale_device_id],
        }
        config_response = client.put(
            "/pos/config",
            json=config_payload,
            headers=reason_headers,
        )
        assert config_response.status_code == status.HTTP_200_OK

        sale_payload = {
            "store_id": store_id,
            "customer_id": customer_id,
            "payment_method": "EFECTIVO",
            "items": [{"device_id": sale_device_id, "quantity": 1}],
            "confirm": True,
            "notes": "Venta sincronizada",
        }
        sale_response = client.post(
            "/pos/sale",
            json=sale_payload,
            headers=reason_headers,
        )
        assert sale_response.status_code == status.HTTP_201_CREATED
        sale_id = sale_response.json()["sale"]["id"]

        repair_payload = {
            "store_id": store_id,
            "customer_id": customer_id,
            "technician_name": "Tecnico Sync",
            "damage_type": "Pantalla rota",
            "device_description": "Telefono azul",
            "labor_cost": 220.0,
            "parts": [{"device_id": part_device_id, "quantity": 2, "unit_cost": 125.0}],
        }
        repair_response = client.post(
            "/repairs",
            json=repair_payload,
            headers=reason_headers,
        )
        assert repair_response.status_code == status.HTTP_201_CREATED
        repair_id = repair_response.json()["id"]

        sync_response = client.post(
            "/sync/run",
            json={"store_id": store_id},
            headers=auth_headers,
        )
        assert sync_response.status_code == status.HTTP_200_OK

        db_session.expire_all()
        entries = db_session.query(models.SyncOutbox).all()
        assert entries, "Se esperaban eventos en la cola híbrida"

        by_type = {}
        for entry in entries:
            by_type.setdefault(entry.entity_type, []).append(entry)
            assert entry.status == models.SyncOutboxStatus.PENDING

        assert "customer" in by_type
        assert "pos_config" in by_type
        assert "sale" in by_type
        assert "repair_order" in by_type

        outbox_response = client.get("/sync/outbox", headers=auth_headers)
        assert outbox_response.status_code == status.HTTP_200_OK
        outbox_data = outbox_response.json()
        assert any(item["entity_type"] == "sale" for item in outbox_data)

        target_entry = by_type["sale"][0]
        retry_without_reason = client.post(
            "/sync/outbox/retry",
            json={"ids": [target_entry.id]},
            headers=auth_headers,
        )
        assert retry_without_reason.status_code == status.HTTP_400_BAD_REQUEST

        retry_response = client.post(
            "/sync/outbox/retry",
            json={"ids": [target_entry.id, by_type["repair_order"][0].id]},
            headers=reason_headers,
        )
        assert retry_response.status_code == status.HTTP_200_OK
        retried_ids = {entry["id"] for entry in retry_response.json()}
        assert target_entry.id in retried_ids
        assert by_type["repair_order"][0].id in retried_ids

        history_response = client.get("/sync/history", headers=auth_headers)
        assert history_response.status_code == status.HTTP_200_OK
        history_data = history_response.json()
        assert any(item["store_id"] == store_id for item in history_data)
    finally:
        settings.enable_hybrid_prep = original_hybrid
        settings.enable_purchases_sales = original_sales
