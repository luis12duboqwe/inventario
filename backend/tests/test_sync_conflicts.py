from backend.app import crud, models


def test_sync_outbox_conflict_detection_and_version_increment(db_session):
    # Primera inserción sin conflicto
    entry1 = crud.enqueue_sync_outbox(
        db_session,
        entity_type="device",
        entity_id="DEV-100",
        operation="create",
        payload={"name": "Telefono X", "quantity": 5},
    )
    assert entry1.version == 1
    assert entry1.conflict_flag is False

    # Segunda inserción misma entidad con cambios en payload => conflicto
    entry2 = crud.enqueue_sync_outbox(
        db_session,
        entity_type="device",
        entity_id="DEV-100",
        operation="update",
        payload={"name": "Telefono X", "quantity": 7},
    )
    assert entry2.conflict_flag is True
    assert entry2.version == 2

    # Tercera inserción mismo payload exacto (no debería incrementar versión)
    entry3 = crud.enqueue_sync_outbox(
        db_session,
        entity_type="device",
        entity_id="DEV-100",
        operation="update",
        payload={"name": "Telefono X", "quantity": 7},
    )
    # No nuevo conflicto (payload igual y misma operación)
    assert entry3.conflict_flag is True  # se mantiene la marca previa
    assert entry3.version == 2

    # Cuarta inserción cambiando nuevamente el payload => incrementa versión
    entry4 = crud.enqueue_sync_outbox(
        db_session,
        entity_type="device",
        entity_id="DEV-100",
        operation="update",
        payload={"name": "Telefono X", "quantity": 9},
    )
    assert entry4.conflict_flag is True
    assert entry4.version == 3

    # Verificar que existe auditoría de conflicto
    audit_logs = crud.list_system_logs(
        db_session, modulo="inventario", limit=50)
    assert any(log.accion == "sync_conflict_potential" for log in audit_logs)


def test_sync_outbox_conflict_resolution(db_session):
    first = crud.enqueue_sync_outbox(
        db_session,
        entity_type="device",
        entity_id="DEV-200",
        operation="create",
        payload={"name": "Telefono Z", "quantity": 3},
    )
    assert first.version == 1
    conflicting = crud.enqueue_sync_outbox(
        db_session,
        entity_type="device",
        entity_id="DEV-200",
        operation="update",
        payload={"name": "Telefono Z", "quantity": 6},
    )
    assert conflicting.conflict_flag is True

    resolved = crud.resolve_outbox_conflicts(
        db_session,
        [conflicting.id],
        performed_by_id=None,
        reason="Resolución manual",
    )
    assert resolved
    resolved_entry = resolved[0]
    assert resolved_entry.conflict_flag is False
    assert resolved_entry.version == conflicting.version + 1
    audit_logs = crud.list_system_logs(db_session, modulo="inventario", limit=50)
    assert any(log.accion == "sync_conflict_resolved" for log in audit_logs)
