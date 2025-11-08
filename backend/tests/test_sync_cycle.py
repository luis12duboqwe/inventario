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
