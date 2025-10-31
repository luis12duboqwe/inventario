"""Pruebas de sincronización multi-sucursal para inventario, ventas y compras."""
from __future__ import annotations

import json

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "sync_replica",
        "password": "Replica123*",
        "full_name": "Sync Replica",
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
    return {"Authorization": f"Bearer {token}", "X-Reason": "Sincronizacion QA"}


def _load_payload_store_id(entry: models.SyncOutbox) -> int | None:
    try:
        payload = json.loads(entry.payload)
    except (TypeError, json.JSONDecodeError):  # pragma: no cover - defensivo
        return None
    candidate = payload.get("store_id")
    if candidate is None:
        candidate = payload.get("origin_store_id")
    if candidate is None:
        candidate = payload.get("destination_store_id")
    try:
        return int(candidate)
    except (TypeError, ValueError):
        return None


def test_sync_replication_processes_inventory_purchases_and_logs(client, db_session) -> None:
    original_hybrid = settings.enable_hybrid_prep
    original_purchases = settings.enable_purchases_sales
    settings.enable_hybrid_prep = True
    settings.enable_purchases_sales = True

    headers = _auth_headers(client)
    basic_headers = {k: v for k, v in headers.items() if k != "X-Reason"}

    try:
        store_payload = {
            "name": "Sucursal Centro",
            "location": "CDMX",
            "timezone": "America/Mexico_City",
        }
        store_response = client.post("/stores", json=store_payload, headers=basic_headers)
        assert store_response.status_code == 201
        store_id = store_response.json()["id"]

        store_payload["name"] = "Sucursal Norte"
        north_response = client.post("/stores", json=store_payload, headers=basic_headers)
        assert north_response.status_code == 201
        north_id = north_response.json()["id"]

        device_payload = {
            "sku": "SYNC-100",
            "name": "Router Empresarial",
            "quantity": 8,
            "unit_price": 9500.0,
            "costo_unitario": 7200.0,
        }
        device_response = client.post(
            f"/stores/{store_id}/devices",
            json=device_payload,
            headers=basic_headers,
        )
        assert device_response.status_code == 201
        device_id = device_response.json()["id"]

        device_payload["quantity"] = 3
        other_device_response = client.post(
            f"/stores/{north_id}/devices",
            json=device_payload,
            headers=basic_headers,
        )
        assert other_device_response.status_code == 201

        movement_payload = {
            "producto_id": device_id,
            "tipo_movimiento": "entrada",
            "cantidad": 2,
            "comentario": headers["X-Reason"],
        }
        movement_response = client.post(
            f"/inventory/stores/{store_id}/movements",
            json=movement_payload,
            headers=headers,
        )
        assert movement_response.status_code == 201
        movement_id = movement_response.json()["id"]

        purchase_payload = {
            "store_id": store_id,
            "supplier": "Proveedor Sync",
            "items": [
                {"device_id": device_id, "quantity_ordered": 2, "unit_cost": 7000.0},
            ],
        }
        purchase_response = client.post(
            "/purchases/",
            json=purchase_payload,
            headers=headers,
        )
        assert purchase_response.status_code == 201
        order_id = purchase_response.json()["id"]

        receive_payload = {
            "items": [
                {"device_id": device_id, "quantity": 1},
            ]
        }
        receive_response = client.post(
            f"/purchases/{order_id}/receive",
            json=receive_payload,
            headers=headers,
        )
        assert receive_response.status_code == 200

        db_session.expire_all()
        device_entry = (
            db_session.query(models.SyncOutbox)
            .filter(models.SyncOutbox.entity_type == "device", models.SyncOutbox.entity_id == str(device_id))
            .one()
        )
        inventory_entry = (
            db_session.query(models.SyncOutbox)
            .filter(models.SyncOutbox.entity_type == "inventory", models.SyncOutbox.entity_id == str(movement_id))
            .one()
        )
        purchase_entry = (
            db_session.query(models.SyncOutbox)
            .filter(models.SyncOutbox.entity_type == "purchase_order", models.SyncOutbox.entity_id == str(order_id))
            .one()
        )

        assert _load_payload_store_id(device_entry) == store_id
        assert _load_payload_store_id(inventory_entry) == store_id
        assert _load_payload_store_id(purchase_entry) == store_id

        sync_response = client.post("/sync/run", json={"store_id": store_id}, headers=headers)
        assert sync_response.status_code == 200

        db_session.expire_all()
        device_entry = (
            db_session.query(models.SyncOutbox)
            .filter(models.SyncOutbox.entity_type == "device", models.SyncOutbox.entity_id == str(device_id))
            .one()
        )
        inventory_entry = (
            db_session.query(models.SyncOutbox)
            .filter(models.SyncOutbox.entity_type == "inventory", models.SyncOutbox.entity_id == str(movement_id))
            .one()
        )
        purchase_entry = (
            db_session.query(models.SyncOutbox)
            .filter(models.SyncOutbox.entity_type == "purchase_order", models.SyncOutbox.entity_id == str(order_id))
            .one()
        )

        assert device_entry.status == models.SyncOutboxStatus.SENT
        assert inventory_entry.status == models.SyncOutboxStatus.SENT
        assert purchase_entry.status == models.SyncOutboxStatus.SENT

        discrepancy_logs = (
            db_session.query(models.AuditLog)
            .filter(models.AuditLog.action == "sync_discrepancy", models.AuditLog.entity_id == "SYNC-100")
            .all()
        )
        assert discrepancy_logs, "Se esperaba al menos una discrepancia registrada"
    finally:
        settings.enable_hybrid_prep = original_hybrid
        settings.enable_purchases_sales = original_purchases
