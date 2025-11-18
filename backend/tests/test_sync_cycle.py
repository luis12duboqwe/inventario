"""Pruebas enfocadas en el ciclo de sincronización híbrida."""

import json

from backend.app import models
from backend.app.services import sync as sync_service


def test_run_sync_cycle_filters_entries_by_store(db_session):
    """Solo procesa entradas coincidentes con la sucursal indicada o globales."""

    matching_store_id = 42
    other_store_id = 99

    entry_matching = models.SyncOutbox(
        entity_type="device",
        entity_id="dev-42",
        operation="update",
        payload=json.dumps({"store_id": matching_store_id}),
        status=models.SyncOutboxStatus.PENDING,
        priority=models.SyncOutboxPriority.HIGH,
    )
    entry_other_store = models.SyncOutbox(
        entity_type="device",
        entity_id="dev-99",
        operation="update",
        payload=json.dumps({"store_id": other_store_id}),
        status=models.SyncOutboxStatus.PENDING,
        priority=models.SyncOutboxPriority.NORMAL,
    )
    entry_global = models.SyncOutbox(
        entity_type="audit",
        entity_id="audit-1",
        operation="insert",
        payload=json.dumps({"event": "global"}),
        status=models.SyncOutboxStatus.PENDING,
        priority=models.SyncOutboxPriority.LOW,
    )
    db_session.add_all([entry_matching, entry_other_store, entry_global])
    db_session.commit()

    result = sync_service.run_sync_cycle(
        db_session,
        store_id=matching_store_id,
        performed_by_id=1,
    )

    assert result["processed"] == 2
    assert result["discrepancies"] == []

    db_session.expire_all()

    updated_matching = db_session.get(models.SyncOutbox, entry_matching.id)
    updated_other = db_session.get(models.SyncOutbox, entry_other_store.id)
    updated_global = db_session.get(models.SyncOutbox, entry_global.id)

    assert updated_matching is not None
    assert updated_matching.status == models.SyncOutboxStatus.SENT
    assert updated_matching.attempt_count == 1

    assert updated_global is not None
    assert updated_global.status == models.SyncOutboxStatus.SENT
    assert updated_global.attempt_count == 1

    assert updated_other is not None
    assert updated_other.status == models.SyncOutboxStatus.PENDING
    assert updated_other.attempt_count == 0


def test_run_sync_cycle_notifies_discrepancies(monkeypatch, db_session):
    entry = models.SyncOutbox(
        entity_type="inventory",
        entity_id="mov-1",
        operation="upsert",
        payload=json.dumps({"store_id": 7}),
        status=models.SyncOutboxStatus.PENDING,
        priority=models.SyncOutboxPriority.HIGH,
    )
    db_session.add(entry)
    db_session.commit()

    fake_discrepancies = [{"sku": "SKU-001", "diferencia": 3}]
    monkeypatch.setattr(
        sync_service,
        "detect_inventory_discrepancies",
        lambda db: fake_discrepancies,
    )

    recorded: dict[str, object] = {}

    def fake_warning(message: str, **extra):
        recorded["message"] = message
        recorded["extra"] = extra

    monkeypatch.setattr(sync_service.logger, "warning", fake_warning)

    logged_payload: dict[str, object] = {}

    def fake_log(db, discrepancies, *, performed_by_id=None):  # noqa: D401 - firma controlada en prueba
        logged_payload["discrepancies"] = list(discrepancies)
        logged_payload["performed_by_id"] = performed_by_id

    monkeypatch.setattr(sync_service.crud, "log_sync_discrepancies", fake_log)

    result = sync_service.run_sync_cycle(db_session, store_id=None, performed_by_id=None)

    assert result == {"processed": 1, "discrepancies": fake_discrepancies}
    assert recorded["message"].startswith("Discrepancias de inventario")
    assert recorded["extra"]["discrepancies"] == fake_discrepancies
    assert logged_payload["discrepancies"] == fake_discrepancies
