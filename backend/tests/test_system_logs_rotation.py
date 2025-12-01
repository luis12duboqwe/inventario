from datetime import datetime, timedelta, timezone

from backend.app import crud, models


def test_system_logs_rotation_purges_old_info_but_keeps_critical(db_session):
    # Crear 30 logs INFO, 20 antiguos y 10 recientes
    old_cutoff = datetime.now(timezone.utc) - timedelta(days=200)
    recent_time = datetime.now(timezone.utc) - timedelta(days=5)

    info_ids_old = []
    info_ids_recent = []

    for i in range(20):
        audit = crud._log_action(
            db_session,
            action="sale_created",
            entity_type="sale",
            entity_id=f"venta-{i}",
            performed_by_id=None,
            details="Venta de prueba",
        )
        syslog = audit.system_log
        assert syslog is not None
        # Forzar fecha antigua sobre el SystemLog real
        syslog.fecha = old_cutoff
        db_session.add(syslog)
        info_ids_old.append(syslog.id)

    for i in range(10):
        audit = crud._log_action(
            db_session,
            action="purchase_order_created",
            entity_type="purchase_order",
            entity_id=f"compra-{i}",
            performed_by_id=None,
            details="Compra de prueba",
        )
        syslog = audit.system_log
        assert syslog is not None
        # Fecha reciente
        syslog.fecha = recent_time
        db_session.add(syslog)
        info_ids_recent.append(syslog.id)

    # Crear 5 logs CRITICAL antiguos (ej. low_stock_alert)
    critical_ids_old = []
    for i in range(5):
        audit = crud._log_action(
            db_session,
            action="low_stock_alert",
            entity_type="inventory",
            entity_id=f"inv-critico-{i}",
            performed_by_id=None,
            details="Stock bajo",
        )
        syslog = audit.system_log
        assert syslog is not None
        syslog.fecha = old_cutoff
        db_session.add(syslog)
        critical_ids_old.append(syslog.id)

    db_session.commit()

    # Ejecutar purga con retención de 180 días y preservando críticos
    deleted = crud.purge_system_logs(
        db_session, retention_days=180, keep_critical=True)
    assert deleted >= 20  # al menos los INFO antiguos deben eliminarse

    # Verificar que los INFO antiguos fueron eliminados
    remaining_info_old = (
        db_session.query(models.SystemLog)
        .filter(models.SystemLog.id.in_(info_ids_old))
        .all()
    )
    assert remaining_info_old == []

    # Verificar que los INFO recientes permanecen
    remaining_info_recent = (
        db_session.query(models.SystemLog)
        .filter(models.SystemLog.id.in_(info_ids_recent))
        .all()
    )
    assert len(remaining_info_recent) == len(info_ids_recent)

    # Verificar que los CRITICAL antiguos permanecen (por preservación)
    remaining_critical_old = (
        db_session.query(models.SystemLog)
        .filter(models.SystemLog.id.in_(critical_ids_old))
        .all()
    )
    assert len(remaining_critical_old) == len(critical_ids_old)

    # Ejecutar purga sin preservar críticos: ahora deberían eliminarse también si son antiguos
    deleted_all = crud.purge_system_logs(
        db_session, retention_days=180, keep_critical=False)
    assert deleted_all >= len(critical_ids_old)
    remaining_critical_after_force = (
        db_session.query(models.SystemLog)
        .filter(models.SystemLog.id.in_(critical_ids_old))
        .all()
    )
    assert remaining_critical_after_force == []
