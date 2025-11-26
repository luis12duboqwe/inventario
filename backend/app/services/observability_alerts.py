"""Alertas operativas derivadas de auditoría y monitoreo interno."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Mapping

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificationBundle:
    """Agrupa las alertas encontradas y las que ameritan salida externa."""

    notifications: list[schemas.ObservabilityNotification]
    newly_logged: list[schemas.ObservabilityNotification]


def _register_audit_alert(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    details: Mapping[str, object] | str | None = None,
    lookback_minutes: int,
) -> bool:
    """Registra el evento en auditoría evitando duplicados en la ventana dada."""

    window_start = datetime.utcnow() - timedelta(minutes=lookback_minutes)
    existing = (
        db.execute(
            select(func.count(models.AuditLog.id)).where(
                models.AuditLog.action == action,
                models.AuditLog.entity_type == entity_type,
                models.AuditLog.entity_id == entity_id,
                models.AuditLog.created_at >= window_start,
            )
        ).scalar_one()
        or 0
    )
    if existing > 0:
        return False

    crud.log_audit_event(
        db,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by_id=None,
        details=details,
    )
    return True


def _collect_login_alerts(db: Session, window_minutes: int) -> NotificationBundle:
    """Detecta intentos de inicio de sesión repetidos en la ventana activa."""

    start = datetime.utcnow() - timedelta(minutes=window_minutes)
    attempts_stmt = (
        select(models.AuditLog.entity_id, func.count(models.AuditLog.id))
        .where(
            models.AuditLog.action == "auth_login_failed",
            models.AuditLog.created_at >= start,
        )
        .group_by(models.AuditLog.entity_id)
    )
    rows = db.execute(attempts_stmt).all()

    notifications: list[schemas.ObservabilityNotification] = []
    newly_logged: list[schemas.ObservabilityNotification] = []

    for entity_id, attempts in rows:
        safe_entity = str(entity_id or "desconocido")
        if attempts < settings.security_login_alert_threshold:
            continue

        occurred_at = db.execute(
            select(func.max(models.AuditLog.created_at)).where(
                models.AuditLog.action == "auth_login_failed",
                models.AuditLog.entity_id == entity_id,
            )
        ).scalar_one()

        notification = schemas.ObservabilityNotification(
            id=f"login-alert-{safe_entity}",
            title="Intentos de inicio de sesión anómalos",
            message=(
                f"{attempts} intentos fallidos para {safe_entity} en la última hora. "
                "Verifica bloqueo y restablece credenciales si corresponde."
            ),
            severity=models.SystemLogLevel.CRITICAL,
            occurred_at=occurred_at,
            reference="login",
        )
        notifications.append(notification)

        logged = _register_audit_alert(
            db,
            action="security_alert_login_threshold",
            entity_type="auth",
            entity_id=safe_entity,
            details=json.dumps(
                {
                    "attempts": attempts,
                    "observed_since": start.isoformat(),
                    "actor": safe_entity,
                },
                ensure_ascii=False,
            ),
            lookback_minutes=window_minutes,
        )
        if logged:
            newly_logged.append(notification)

    return NotificationBundle(notifications, newly_logged)


def _collect_stockout_alerts(db: Session, window_minutes: int) -> NotificationBundle:
    """Genera alertas cuando existen productos con stock en cero o negativo."""

    zero_stmt = (
        select(models.Device, models.Store)
        .join(models.Store, models.Device.store_id == models.Store.id)
        .where(models.Device.quantity <= 0)
        .limit(5)
    )
    records = db.execute(zero_stmt).all()
    if not records:
        return NotificationBundle([], [])

    total_zero = len(records)
    store_names = {store.name for _, store in records if store and store.name}
    affected = ", ".join(sorted(store_names)) or "sucursales"
    first_device = records[0][0]
    occurred_at = getattr(first_device, "updated_at", None)

    notification = schemas.ObservabilityNotification(
        id="stockout-global",
        title="Productos sin inventario",
        message=(
            f"Se detectaron {total_zero} SKU con stock en 0/negativo en {affected}. "
            "Revisa reposiciones o bloquea ventas hasta reabastecer."
        ),
        severity=models.SystemLogLevel.CRITICAL,
        occurred_at=occurred_at,
        reference="inventory",
    )

    logged = _register_audit_alert(
        db,
        action="inventory_stockout_detected",
        entity_type="inventory",
        entity_id="global",
        details=json.dumps(
            {
                "total_zero": total_zero,
                "stores": list(store_names),
                "observed_since": (datetime.utcnow() - timedelta(minutes=window_minutes)).isoformat(),
            },
            ensure_ascii=False,
        ),
        lookback_minutes=window_minutes,
    )

    newly_logged = [notification] if logged else []
    return NotificationBundle([notification], newly_logged)


def _collect_task_failure_alerts(db: Session, window_minutes: int) -> NotificationBundle:
    """Construye alertas a partir de fallos recientes de tareas programadas."""

    start = datetime.utcnow() - timedelta(minutes=window_minutes)
    sessions_stmt = (
        select(models.SyncSession)
        .where(
            models.SyncSession.status == models.SyncStatus.FAILED,
            models.SyncSession.finished_at >= start,
        )
        .order_by(models.SyncSession.finished_at.desc())
        .limit(5)
    )
    sessions = list(db.scalars(sessions_stmt).unique())
    if not sessions:
        return NotificationBundle([], [])

    notifications: list[schemas.ObservabilityNotification] = []
    newly_logged: list[schemas.ObservabilityNotification] = []

    for session in sessions:
        store_hint = session.store.name if session.store else "sin sucursal"
        reference = session.error_message or "Tarea en estado fallido"
        notification = schemas.ObservabilityNotification(
            id=f"task-failure-{session.id}",
            title="Fallo en tarea programada",
            message=(
                f"La sincronización automática de {store_hint} falló. "
                f"Detalle: {reference}"
            ),
            severity=models.SystemLogLevel.ERROR,
            occurred_at=session.finished_at,
            reference="scheduler",
        )
        notifications.append(notification)

        logged = _register_audit_alert(
            db,
            action="scheduler_task_failed",
            entity_type="sync_session",
            entity_id=str(session.id),
            details=json.dumps(
                {
                    "store": store_hint,
                    "error": reference,
                    "mode": session.mode.value,
                },
                ensure_ascii=False,
            ),
            lookback_minutes=window_minutes,
        )
        if logged:
            newly_logged.append(notification)

    return NotificationBundle(notifications, newly_logged)


def collect_operational_notifications(db: Session) -> NotificationBundle:
    """Reúne alertas críticas internas basadas en auditoría y fallos."""

    window_minutes = settings.security_alert_window_minutes
    bundles = [
        _collect_login_alerts(db, window_minutes),
        _collect_stockout_alerts(db, window_minutes),
        _collect_task_failure_alerts(db, window_minutes),
    ]

    notifications: list[schemas.ObservabilityNotification] = []
    newly_logged: list[schemas.ObservabilityNotification] = []
    for bundle in bundles:
        notifications.extend(bundle.notifications)
        newly_logged.extend(bundle.newly_logged)

    return NotificationBundle(notifications, newly_logged)


def dispatch_external_notifications(
    alerts: Iterable[schemas.ObservabilityNotification], *, timeout_seconds: float = 5
) -> set[str]:
    """Envía las alertas críticas al proveedor externo configurado."""

    webhook = settings.monitoring_alert_webhook_url
    if not webhook:
        return set()

    critical_alerts = [
        alert
        for alert in alerts
        if alert.severity in {models.SystemLogLevel.CRITICAL, models.SystemLogLevel.ERROR}
    ]
    if not critical_alerts:
        return set()

    payload = {
        "source": "softmobile-observability",
        "generated_at": datetime.utcnow().isoformat(),
        "alerts": [alert.model_dump() for alert in critical_alerts],
    }

    headers: dict[str, str] = {"User-Agent": "softmobile-observability"}
    if settings.monitoring_alert_token:
        headers["Authorization"] = f"Bearer {settings.monitoring_alert_token}"

    try:
        response = httpx.post(webhook, json=payload, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        return {"webhook"}
    except Exception:  # pragma: no cover - defensivo ante integraciones externas
        logger.exception("No se pudo entregar la alerta crítica al webhook externo")
        return set()


__all__ = [
    "NotificationBundle",
    "collect_operational_notifications",
    "dispatch_external_notifications",
]
