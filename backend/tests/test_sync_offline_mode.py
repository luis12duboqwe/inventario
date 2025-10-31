from datetime import datetime, timedelta

from backend.app import models
from backend.app.config import settings
from backend.app.core.roles import ADMIN
from backend.app.models import SyncOutboxStatus
from backend.app.services.sync import requeue_failed_outbox_entries
from sqlalchemy.orm import Session


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "offline_admin",
        "password": "Offline123*",
        "full_name": "Offline Admin",
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
    return {"Authorization": f"Bearer {token}", "X-Reason": "Prueba offline"}


def test_hybrid_retry_queue_and_history(client, db_session: Session) -> None:
    original_hybrid = settings.enable_hybrid_prep
    original_sales = settings.enable_purchases_sales
    settings.enable_hybrid_prep = True
    settings.enable_purchases_sales = True
    headers = _auth_headers(client)

    try:
        store_ids: list[int] = []
        for index in range(1, 4):
            store_payload = {
                "name": f"Sucursal Offline {index}",
                "location": "CDMX",
                "timezone": "America/Mexico_City",
            }
            store_response = client.post("/stores", json=store_payload, headers=headers)
            assert store_response.status_code == 201
            store_ids.append(store_response.json()["id"])

        device_ids: list[int] = []
        for store_id in store_ids:
            device_payload = {
                "sku": f"OFF-{store_id}",
                "name": "Router Híbrido",
                "quantity": 5,
                "unit_price": 9500.0,
                "costo_unitario": 7000.0,
            }
            device_response = client.post(f"/stores/{store_id}/devices", json=device_payload, headers=headers)
            assert device_response.status_code == 201
            device_ids.append(device_response.json()["id"])

        for store_id, device_id in zip(store_ids, device_ids):
            sale_payload = {
                "store_id": store_id,
                "payment_method": "EFECTIVO",
                "items": [{"device_id": device_id, "quantity": 1}],
            }
            sale_response = client.post("/sales", json=sale_payload, headers=headers)
            assert sale_response.status_code == 201

        entries = db_session.query(models.SyncOutbox).all()
        assert entries
        retry_ids: list[int] = []
        for entry in entries:
            entry.status = SyncOutboxStatus.FAILED
            entry.attempt_count = 2
            entry.error_message = "offline"
            entry.last_attempt_at = datetime.utcnow() - timedelta(
                seconds=settings.sync_retry_interval_seconds + 10
            )
            retry_ids.append(entry.id)
        db_session.commit()

        requeued = requeue_failed_outbox_entries(db_session)
        assert {entry.id for entry in requeued} == set(retry_ids)

        refreshed = (
            db_session.query(models.SyncOutbox)
            .filter(models.SyncOutbox.id.in_(retry_ids))
            .all()
        )
        for item in refreshed:
            assert item.status == SyncOutboxStatus.PENDING
            assert item.attempt_count == 0
            assert item.error_message is None

        for store_id in store_ids:
            sync_response = client.post("/sync/run", json={"store_id": store_id}, headers=headers)
            assert sync_response.status_code == 200

        history_headers = {k: v for k, v in headers.items() if k != "X-Reason"}
        history_response = client.get("/sync/history", headers=history_headers)
        assert history_response.status_code == 200
        history = history_response.json()
        assert history
        covered_stores = {entry["store_id"] for entry in history}
        for store_id in store_ids:
            assert store_id in covered_stores
        assert any(
            session["status"] == "exitoso"
            for entry in history
            for session in entry["sessions"]
        )
    finally:
        settings.enable_hybrid_prep = original_hybrid
        settings.enable_purchases_sales = original_sales
