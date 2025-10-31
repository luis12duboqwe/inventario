"""Pruebas de la cola híbrida de sincronización."""
# // [PACK35-backend]

from datetime import datetime, timedelta
import json

import pytest
from fastapi import status

from backend.app import crud, models, schemas
from backend.app.config import settings
from backend.app.core.roles import ADMIN, GESTION_ROLES


def _bootstrap_manager(client):
    payload = {
        "username": "sync_queue_admin",
        "password": "SyncQueue123*",
        "full_name": "Sync Queue Admin",
        "roles": list({*GESTION_ROLES, ADMIN}),
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code in {status.HTTP_201_CREATED, status.HTTP_409_CONFLICT}
    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    return token_response.json()["access_token"]


def test_sync_queue_lifecycle(client):
    original_hybrid = settings.enable_hybrid_prep
    original_remote = settings.sync_remote_url
    settings.enable_hybrid_prep = True
    settings.sync_remote_url = None

    try:
        token = _bootstrap_manager(client)
        headers = {"Authorization": f"Bearer {token}"}
        secure_headers = {**headers, "X-Reason": "Motivo QA"}

        enqueue_response = client.post(
            "/sync/events",
            json={
                "events": [
                    {
                        "event_type": "inventory.adjustment",
                        "payload": {"store_id": 1, "delta": -2},
                        "idempotency_key": "inventory-adjustment-1",
                    }
                ]
            },
            headers=secure_headers,
        )
        assert enqueue_response.status_code == status.HTTP_200_OK
        payload = enqueue_response.json()
        assert payload["queued"]
        queue_id = payload["queued"][0]["id"]

        # idempotencia: reusar el mismo evento conserva el registro
        second_enqueue = client.post(
            "/sync/events",
            json={
                "events": [
                    {
                        "event_type": "inventory.adjustment",
                        "payload": {"store_id": 1, "delta": -3},
                        "idempotency_key": "inventory-adjustment-1",
                    }
                ]
            },
            headers=secure_headers,
        )
        assert second_enqueue.status_code == status.HTTP_200_OK
        assert second_enqueue.json()["reused"][0]["id"] == queue_id

        status_response = client.get(
            "/sync/status",
            headers=headers,
            params={"limit": 10},
        )
        assert status_response.status_code == status.HTTP_200_OK
        queue_items = status_response.json()
        assert any(item["id"] == queue_id for item in queue_items)

        summary_response = client.get(
            "/sync/status/summary",
            headers=headers,
        )
        assert summary_response.status_code == status.HTTP_200_OK
        summary_payload = summary_response.json()
        assert summary_payload["total"] >= 1
        assert summary_payload["pending"] >= 1

        dispatch_response = client.post(
            "/sync/dispatch",
            headers=secure_headers,
            params={"limit": 5},
        )
        assert dispatch_response.status_code == status.HTTP_200_OK
        summary = dispatch_response.json()
        assert summary["processed"] >= 1
        assert summary["sent"] >= 1

        refreshed_summary = client.get(
            "/sync/status/summary",
            headers=headers,
        )
        assert refreshed_summary.status_code == status.HTTP_200_OK
        refreshed_payload = refreshed_summary.json()
        assert refreshed_payload["processed"] >= summary_payload["processed"]
        assert refreshed_payload["percent"] >= summary_payload["percent"]

        resolved_status = client.get(
            "/sync/status",
            headers=headers,
            params={"limit": 10, "status_filter": "SENT"},
        )
        assert resolved_status.status_code == status.HTTP_200_OK
        assert any(item["id"] == queue_id for item in resolved_status.json())

        # Permite resolución manual
        manual_enqueue = client.post(
            "/sync/events",
            json={
                "events": [
                    {
                        "event_type": "pos.sale",
                        "payload": {"store_id": 2, "ticket": "ABC-1"},
                    }
                ]
            },
            headers=secure_headers,
        )
        assert manual_enqueue.status_code == status.HTTP_200_OK
        pending_id = manual_enqueue.json()["queued"][0]["id"]

        resolve_response = client.post(
            f"/sync/resolve/{pending_id}", headers=secure_headers
        )
        assert resolve_response.status_code == status.HTTP_200_OK
        assert resolve_response.json()["status"] == "SENT"
    finally:
        settings.enable_hybrid_prep = original_hybrid
        settings.sync_remote_url = original_remote


# // [PACK35-backend]
def test_sync_hybrid_progress_combines_outbox_and_queue(client, db_session):
    original_hybrid = settings.enable_hybrid_prep
    original_remote = settings.sync_remote_url
    settings.enable_hybrid_prep = True
    settings.sync_remote_url = None

    try:
        now = datetime.utcnow()
        events = [
            schemas.SyncQueueEvent(event_type="inventory.update", payload={"sku": "SKU-1"}),
            schemas.SyncQueueEvent(event_type="inventory.update", payload={"sku": "SKU-2"}),
            schemas.SyncQueueEvent(event_type="pos.sale", payload={"ticket": "A-1"}),
        ]
        queued, _ = crud.enqueue_sync_queue_events(db_session, events)
        statuses = (
            models.SyncQueueStatus.SENT,
            models.SyncQueueStatus.PENDING,
            models.SyncQueueStatus.FAILED,
        )
        for index, (entry, status_value) in enumerate(zip(queued, statuses, strict=True)):
            entry.status = status_value
            entry.attempts = 1
            entry.updated_at = now - timedelta(minutes=index * 5)
            entry.last_error = "Fallo controlado" if status_value is models.SyncQueueStatus.FAILED else None
            db_session.add(entry)
        db_session.commit()

        outbox_entries = []
        for index, status_value in enumerate(statuses):
            entry = models.SyncOutbox(
                entity_type="inventory",
                entity_id=f"INV-{index}",
                operation="update",
                payload=json.dumps({"sku": f"SKU-{index}"}, ensure_ascii=False),
                status=status_value,
                priority=models.SyncOutboxPriority.NORMAL,
                updated_at=now - timedelta(hours=2 - index),
                created_at=now - timedelta(hours=3 - index),
            )
            if status_value is models.SyncOutboxStatus.FAILED:
                entry.error_message = "Error controlado"
            outbox_entries.append(entry)
        db_session.add_all(outbox_entries)
        db_session.commit()

        token = _bootstrap_manager(client)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/sync/status/hybrid", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["total"] == 6
        assert payload["processed"] == 2
        assert payload["pending"] == 2
        assert payload["failed"] == 2
        assert payload["components"]["queue"]["pending"] == 1
        assert payload["components"]["outbox"]["failed"] == 1
        assert payload["percent"] >= 33.0
    finally:
        settings.enable_hybrid_prep = original_hybrid
        settings.sync_remote_url = original_remote


# // [PACK35-backend]
def test_sync_hybrid_breakdown_by_module(client, db_session):
    original_hybrid = settings.enable_hybrid_prep
    settings.enable_hybrid_prep = True

    try:
        now = datetime.utcnow()
        queue_entries = [
            models.SyncQueue(
                event_type="inventory.adjustment",
                payload={"sku": "INV-1"},
                idempotency_key="queue-inventory-1",
                status=models.SyncQueueStatus.SENT,
                attempts=1,
                created_at=now,
                updated_at=now,
            ),
            models.SyncQueue(
                event_type="inventory.restock",
                payload={"sku": "INV-2"},
                idempotency_key="queue-inventory-2",
                status=models.SyncQueueStatus.PENDING,
                created_at=now,
                updated_at=now,
            ),
            models.SyncQueue(
                event_type="pos.sale",
                payload={"ticket": "POS-1"},
                idempotency_key="queue-pos-1",
                status=models.SyncQueueStatus.FAILED,
                attempts=2,
                last_error="network error",
                created_at=now,
                updated_at=now,
            ),
        ]
        db_session.add_all(queue_entries)

        outbox_entries = [
            models.SyncOutbox(
                entity_type="inventory.device",
                entity_id="100",
                operation="update",
                payload=json.dumps({"id": 100}),
                status=models.SyncOutboxStatus.PENDING,
                created_at=now,
                updated_at=now,
            ),
            models.SyncOutbox(
                entity_type="sales.order",
                entity_id="200",
                operation="create",
                payload=json.dumps({"id": 200}),
                status=models.SyncOutboxStatus.SENT,
                created_at=now,
                updated_at=now,
            ),
            models.SyncOutbox(
                entity_type="customers.profile",
                entity_id="300",
                operation="update",
                payload=json.dumps({"id": 300}),
                status=models.SyncOutboxStatus.FAILED,
                created_at=now,
                updated_at=now,
            ),
        ]
        db_session.add_all(outbox_entries)
        db_session.commit()

        token = _bootstrap_manager(client)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/sync/status/breakdown", headers=headers)
        assert response.status_code == status.HTTP_200_OK

        payload = response.json()
        assert isinstance(payload, list)
        modules = {item["module"]: item for item in payload}

        inventory = modules.get("inventory")
        assert inventory is not None
        assert inventory["total"] == 3
        assert inventory["pending"] == 2
        assert inventory["queue"]["pending"] == 1
        assert inventory["outbox"]["pending"] == 1
        assert pytest.approx(inventory["percent"], rel=1e-3) == 33.33

        pos_module = modules.get("pos")
        assert pos_module is not None
        assert pos_module["failed"] == 1
        assert pos_module["percent"] == 0.0

        sales_module = modules.get("sales")
        assert sales_module is not None
        assert sales_module["processed"] == 1
        assert sales_module["percent"] == 100.0

        customers_module = modules.get("customers")
        assert customers_module is not None
        assert customers_module["failed"] == 1
        assert customers_module["percent"] == 0.0
    finally:
        settings.enable_hybrid_prep = original_hybrid
        db_session.query(models.SyncQueue).delete()
        db_session.query(models.SyncOutbox).delete()
        db_session.commit()

# // [PACK35-backend]
def test_sync_hybrid_forecast_estimates_completion(client, db_session):
    original_hybrid = settings.enable_hybrid_prep
    original_remote = settings.sync_remote_url
    settings.enable_hybrid_prep = True
    settings.sync_remote_url = None

    try:
        now = datetime.utcnow()
        events = [
            schemas.SyncQueueEvent(event_type="inventory.update", payload={"sku": "SKU-1"}),
            schemas.SyncQueueEvent(event_type="inventory.update", payload={"sku": "SKU-2"}),
            schemas.SyncQueueEvent(event_type="pos.sale", payload={"ticket": "A-1"}),
            schemas.SyncQueueEvent(event_type="inventory.adjustment", payload={"sku": "SKU-3"}),
        ]
        queued, _ = crud.enqueue_sync_queue_events(db_session, events)
        queue_statuses = (
            (models.SyncQueueStatus.SENT, 5),
            (models.SyncQueueStatus.SENT, 30),
            (models.SyncQueueStatus.PENDING, 12),
            (models.SyncQueueStatus.FAILED, 20),
        )
        for entry, (status_value, minutes_ago) in zip(queued, queue_statuses, strict=True):
            entry.status = status_value
            entry.attempts = 1
            entry.updated_at = now - timedelta(minutes=minutes_ago)
            entry.created_at = now - timedelta(minutes=minutes_ago + 5)
            if status_value is models.SyncQueueStatus.FAILED:
                entry.last_error = "Fallo controlado"
            db_session.add(entry)
        db_session.commit()

        outbox_entries: list[models.SyncOutbox] = []
        outbox_statuses = (
            (models.SyncOutboxStatus.SENT, 18),
            (models.SyncOutboxStatus.PENDING, 22),
            (models.SyncOutboxStatus.FAILED, 28),
        )
        for index, (status_value, minutes_ago) in enumerate(outbox_statuses):
            entry = models.SyncOutbox(
                entity_type="inventory",
                entity_id=f"INV-{index}",
                operation="update",
                payload=json.dumps({"sku": f"SKU-{index}"}, ensure_ascii=False),
                status=status_value,
                priority=models.SyncOutboxPriority.NORMAL,
                updated_at=now - timedelta(minutes=minutes_ago),
                created_at=now - timedelta(minutes=minutes_ago + 5),
            )
            if status_value is models.SyncOutboxStatus.FAILED:
                entry.error_message = "Error controlado"
            outbox_entries.append(entry)
        db_session.add_all(outbox_entries)
        db_session.commit()

        attempts = [
            models.SyncAttempt(
                queue_id=queued[0].id,
                success=True,
                attempted_at=now - timedelta(minutes=15),
            ),
            models.SyncAttempt(
                queue_id=queued[1].id,
                success=False,
                attempted_at=now - timedelta(minutes=8),
            ),
            models.SyncAttempt(
                queue_id=queued[2].id,
                success=True,
                attempted_at=now - timedelta(minutes=90),
            ),
        ]
        db_session.add_all(attempts)
        db_session.commit()

        token = _bootstrap_manager(client)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get(
            "/sync/status/forecast",
            headers=headers,
            params={"lookback_minutes": 45},
        )
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["lookback_minutes"] == 45
        assert payload["processed_queue"] == 2
        assert payload["processed_outbox"] == 1
        assert payload["processed_recent"] == 3
        assert payload["attempts_total"] == 2
        assert payload["attempts_successful"] == 1
        assert payload["success_rate"] == 50.0
        assert payload["backlog_pending"] == 2
        assert payload["backlog_failed"] == 2
        assert payload["backlog_total"] == 4
        assert payload["events_per_minute"] > 0
        assert payload["estimated_minutes_remaining"] is not None
        assert payload["estimated_completion"] is not None
        assert payload["progress"]["total"] == 7
        assert payload["progress"]["pending"] == 2
        assert payload["progress"]["failed"] == 2
    finally:
        settings.enable_hybrid_prep = original_hybrid
        settings.sync_remote_url = original_remote
