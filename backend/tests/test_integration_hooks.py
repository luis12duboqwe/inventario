import pytest

from backend.app import crud, models
from backend.app.services.integrations import integration_registry


@pytest.fixture()
def integration_token() -> tuple[str, str]:
    record, token = integration_registry.rotate_token("zapier")
    return record.slug, token


def _enqueue_outbox_event(db_session, entity_type: str = "sale"):
    return crud.enqueue_sync_outbox(
        db_session,
        entity_type=entity_type,
        entity_id="9001",
        operation="UPSERT",
        payload={"total": 120.5, "store_id": 1},
    )


def test_public_webhook_lists_and_acknowledges(client, db_session, integration_token):
    slug, token = integration_token
    entry = _enqueue_outbox_event(db_session)

    headers = {"X-Integration-Token": token, "X-Reason": "Sincronizacion contable"}
    response = client.get(f"/integrations/hooks/{slug}/events", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert any(item["id"] == entry.id for item in payload)

    ack_response = client.post(
        f"/integrations/hooks/{slug}/events/{entry.id}/ack",
        json={"status": "sent"},
        headers=headers,
    )

    assert ack_response.status_code == 200
    ack_payload = ack_response.json()
    assert ack_payload["status"] == models.SyncOutboxStatus.SENT.value

    refreshed = crud.get_sync_outbox_entry(
        db_session, entry_id=entry.id, entity_types=("sale",)
    )
    assert refreshed is not None
    assert refreshed.status == models.SyncOutboxStatus.SENT


def test_public_webhook_marks_failure(client, db_session):
    record, token = integration_registry.rotate_token("erp_sync")
    entry = _enqueue_outbox_event(db_session, entity_type="transfer_order")

    headers = {"X-Integration-Token": token, "X-Reason": "Reporte remoto"}
    response = client.post(
        f"/integrations/hooks/{record.slug}/events/{entry.id}/ack",
        json={"status": "failed", "error_message": "timeout remoto"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == models.SyncOutboxStatus.FAILED.value

    refreshed = crud.get_sync_outbox_entry(
        db_session, entry_id=entry.id, entity_types=("transfer_order",)
    )
    assert refreshed is not None
    assert refreshed.status == models.SyncOutboxStatus.FAILED
    assert "timeout" in (refreshed.error_message or "")


def test_public_webhook_rejects_invalid_token(client):
    response = client.get(
        "/integrations/hooks/zapier/events",
        headers={"X-Integration-Token": "invalid", "X-Reason": "Consulta"},
    )

    assert response.status_code == 401
