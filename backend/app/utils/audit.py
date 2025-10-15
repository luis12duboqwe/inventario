"""Utilidades para clasificar y resumir eventos de auditoría."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
