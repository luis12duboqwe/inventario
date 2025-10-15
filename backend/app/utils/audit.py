"""Utilidades para clasificar y resumir eventos de auditoría."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Literal, TypedDict

from ..models import AuditLog

AuditSeverity = Literal["info", "warning", "critical"]


_CRITICAL_KEYWORDS = (
    "fail",
    "denied",
    "block",
    "lock",
    "intrusion",
    "breach",
    "error",
)
_WARNING_KEYWORDS = (
    "password",
    "totp",
    "2fa",
    "deactivate",
    "retry",
    "cancel",
    "sync",
)


def classify_severity(action: str, details: str | None = None) -> AuditSeverity:
    """Deriva la severidad de un evento según acción/detalle."""

    haystack = f"{action} {details or ''}".lower()
    if any(keyword in haystack for keyword in _CRITICAL_KEYWORDS):
        return "critical"
    if any(keyword in haystack for keyword in _WARNING_KEYWORDS):
        return "warning"
    return "info"


def severity_label(severity: AuditSeverity) -> str:
    """Texto visible para cada severidad."""

    if severity == "critical":
        return "Crítica"
    if severity == "warning":
        return "Preventiva"
    return "Informativa"


class HighlightEntry(TypedDict):
    id: int
    action: str
    created_at: datetime
    severity: AuditSeverity
    entity_type: str
    entity_id: str


@dataclass(slots=True)
class AuditAlertSummary:
    total: int
    critical: int
    warning: int
    info: int
    highlights: list[HighlightEntry]

    @property
    def has_alerts(self) -> bool:
        return self.critical > 0 or self.warning > 0


class PersistentAlert(TypedDict):
    """Estructura serializable para recordatorios persistentes."""

    entity_type: str
    entity_id: str
    first_seen: datetime
    last_seen: datetime
    occurrences: int
    latest_action: str
    latest_details: str | None


def summarize_alerts(logs: Iterable[AuditLog], *, max_highlights: int = 5) -> AuditAlertSummary:
    """Calcula totales de severidad y eventos destacados."""

    critical = warning = info = 0
    highlights: list[HighlightEntry] = []
    for log in logs:
        severity = classify_severity(log.action or "", log.details)
        if severity == "critical":
            critical += 1
        elif severity == "warning":
            warning += 1
        else:
            info += 1
        if severity != "info" and len(highlights) < max_highlights:
            highlights.append(
                HighlightEntry(
                    id=log.id,
                    action=log.action,
                    created_at=log.created_at,
                    severity=severity,
                    entity_type=log.entity_type,
                    entity_id=log.entity_id,
                )
            )
    total = critical + warning + info
    return AuditAlertSummary(
        total=total,
        critical=critical,
        warning=warning,
        info=info,
        highlights=highlights,
    )


def serialize_log(log: AuditLog) -> dict[str, object]:
    """Convierte el modelo en un diccionario listo para exponer vía API."""

    severity = classify_severity(log.action or "", log.details)
    return {
        "id": log.id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "details": log.details,
        "performed_by_id": log.performed_by_id,
        "created_at": log.created_at,
        "severity": severity,
        "severity_label": severity_label(severity),
    }


def identify_persistent_critical_alerts(
    logs: Iterable[AuditLog],
    *,
    threshold_minutes: int = 15,
    min_occurrences: int = 1,
    limit: int | None = None,
    reference_time: datetime | None = None,
) -> list[PersistentAlert]:
    """Detecta alertas críticas que persisten más allá del umbral definido.

    Se agrupan por entidad para consolidar ocurrencias múltiples y se devuelven en
    orden descendente según la última aparición registrada.
    """

    if threshold_minutes < 0:
        raise ValueError("threshold_minutes must be non-negative")
    if min_occurrences < 1:
        raise ValueError("min_occurrences must be >= 1")

    now = reference_time or datetime.utcnow()
    threshold = now - timedelta(minutes=threshold_minutes)

    grouped: dict[tuple[str, str], PersistentAlert] = {}

    for log in sorted(logs, key=lambda item: item.created_at):
        severity = classify_severity(log.action or "", log.details)
        if severity != "critical":
            continue
        if threshold_minutes > 0 and log.created_at > threshold:
            continue

        key = (log.entity_type, log.entity_id)
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = PersistentAlert(
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                first_seen=log.created_at,
                last_seen=log.created_at,
                occurrences=1,
                latest_action=log.action,
                latest_details=log.details,
            )
        else:
            existing["occurrences"] += 1
            if log.created_at < existing["first_seen"]:
                existing["first_seen"] = log.created_at
            if log.created_at >= existing["last_seen"]:
                existing["last_seen"] = log.created_at
                existing["latest_action"] = log.action
                existing["latest_details"] = log.details

    alerts = [alert for alert in grouped.values() if alert["occurrences"] >= min_occurrences]
    alerts.sort(key=lambda alert: alert["last_seen"], reverse=True)
    if limit is not None:
        alerts = alerts[:limit]
    return alerts
