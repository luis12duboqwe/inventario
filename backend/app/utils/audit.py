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
    "stock bajo",
    "stock-bajo",
    "stockout",
)
_WARNING_KEYWORDS = (
    "password",
    "totp",
    "2fa",
    "deactivate",
    "retry",
    "cancel",
    "sync",
    "ajuste manual",
    "inconsistencia",
    "fiscal",
    "config",
)


def severity_keywords() -> dict[AuditSeverity, tuple[str, ...]]:
    """Exponer palabras clave de severidad para filtros avanzados."""

    return {
        "critical": _CRITICAL_KEYWORDS,
        "warning": _WARNING_KEYWORDS,
        "info": (),
    }


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


class HighlightEntry(TypedDict, total=False):
    """Evento destacado dentro del resumen de auditoría."""

    id: int
    action: str
    created_at: datetime
    severity: AuditSeverity
    entity_type: str
    entity_id: str
    status: Literal["pending", "acknowledged"]
    acknowledged_at: datetime | None
    acknowledged_by_id: int | None
    acknowledged_by_name: str | None
    acknowledged_note: str | None


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
    threshold_minutes: int,
    min_occurrences: int,
    limit: int,
    reference_time: datetime | None = None,
) -> list[dict[str, object]]:
    """Detecta alertas críticas recurrentes para alimentar recordatorios."""

    reference_time = reference_time or datetime.utcnow()
    threshold_delta = timedelta(minutes=threshold_minutes)

    aggregates: dict[tuple[str, str], dict[str, object]] = {}
    for log in logs:
        severity = classify_severity(log.action or "", log.details)
        if severity != "critical":
            continue
        key = (log.entity_type, log.entity_id)
        entry = aggregates.get(key)
        if entry is None:
            entry = {
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "first_seen": log.created_at,
                "last_seen": log.created_at,
                "occurrences": 0,
                "latest_action": log.action,
                "latest_details": log.details,
            }
            aggregates[key] = entry
        entry["occurrences"] += 1
        if log.created_at > entry["last_seen"]:
            entry["last_seen"] = log.created_at
            entry["latest_action"] = log.action
            entry["latest_details"] = log.details

    candidates: list[dict[str, object]] = []
    for entry in aggregates.values():
        if entry["occurrences"] < min_occurrences:
            continue
        if threshold_minutes > 0 and reference_time - entry["last_seen"] > threshold_delta:
            continue
        candidates.append(entry)

    candidates.sort(key=lambda item: item["last_seen"], reverse=True)
    return candidates[:limit]


__all__ = [
    "AuditAlertSummary",
    "AuditSeverity",
    "HighlightEntry",
    "identify_persistent_critical_alerts",
    "summarize_alerts",
    "classify_severity",
    "severity_label",
    "severity_keywords",
    "serialize_log",
]
