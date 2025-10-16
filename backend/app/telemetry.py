"""Métricas corporativas para monitoreo Prometheus."""
from __future__ import annotations

from typing import Iterable, Mapping

from prometheus_client import CollectorRegistry, Counter, Gauge

REGISTRY = CollectorRegistry()

_AUDIT_ACK_COUNTER = Counter(
    "softmobile_audit_acknowledgements_total",
    "Acuses manuales registrados desde Seguridad.",
    ["entity_type", "event"],
    registry=REGISTRY,
)

_AUDIT_ACK_FAILURE_COUNTER = Counter(
    "softmobile_audit_acknowledgement_failures_total",
    "Errores al registrar acuses manuales en Seguridad.",
    ["entity_type", "reason"],
    registry=REGISTRY,
)

_AUDIT_REMINDER_CACHE_EVENTS = Counter(
    "softmobile_audit_reminder_cache_events_total",
    "Eventos de la cache TTL de recordatorios críticos.",
    ["event"],
    registry=REGISTRY,
)

_AUDIT_REMINDER_CACHE_SNAPSHOT = Gauge(
    "softmobile_audit_reminder_cache_entries",
    "Cantidad de recordatorios críticos almacenados en cache.",
    ["state"],
    registry=REGISTRY,
)


def _normalize_entity(entity_type: str | None) -> str:
    if not entity_type:
        return "unknown"
    normalized = entity_type.strip()
    return normalized or "unknown"


def _update_reminder_snapshot(entries: Iterable[Mapping[str, object]]) -> None:
    total = 0
    acknowledged = 0
    for entry in entries:
        total += 1
        status = str(entry.get("status", ""))
        if status.lower() == "acknowledged":
            acknowledged += 1
    pending = total - acknowledged
    _AUDIT_REMINDER_CACHE_SNAPSHOT.labels(state="total").set(float(total))
    _AUDIT_REMINDER_CACHE_SNAPSHOT.labels(state="pending").set(float(pending))
    _AUDIT_REMINDER_CACHE_SNAPSHOT.labels(state="acknowledged").set(float(acknowledged))


def record_audit_acknowledgement(entity_type: str, event: str) -> None:
    """Registra un acuse exitoso (creado/actualizado)."""

    _AUDIT_ACK_COUNTER.labels(entity_type=_normalize_entity(entity_type), event=event).inc()


def record_audit_acknowledgement_failure(entity_type: str, reason: str) -> None:
    """Incrementa el contador de fallos al registrar acuses."""

    _AUDIT_ACK_FAILURE_COUNTER.labels(
        entity_type=_normalize_entity(entity_type),
        reason=reason,
    ).inc()


def record_reminder_cache_hit(entries: Iterable[Mapping[str, object]]) -> None:
    """Registra un acceso exitoso a la cache TTL de recordatorios."""

    _AUDIT_REMINDER_CACHE_EVENTS.labels(event="hit").inc()
    _update_reminder_snapshot(entries)


def record_reminder_cache_miss(entries: Iterable[Mapping[str, object]]) -> None:
    """Registra un cálculo nuevo de recordatorios críticos."""

    _AUDIT_REMINDER_CACHE_EVENTS.labels(event="miss").inc()
    _update_reminder_snapshot(entries)


def record_reminder_cache_invalidation() -> None:
    """Registra la limpieza manual de la cache TTL de recordatorios."""

    _AUDIT_REMINDER_CACHE_EVENTS.labels(event="invalidated").inc()
    _AUDIT_REMINDER_CACHE_SNAPSHOT.labels(state="total").set(0.0)
    _AUDIT_REMINDER_CACHE_SNAPSHOT.labels(state="pending").set(0.0)
    _AUDIT_REMINDER_CACHE_SNAPSHOT.labels(state="acknowledged").set(0.0)


def get_metric_value(metric_name: str, labels: Mapping[str, str] | None = None) -> float | None:
    """Obtiene el valor actual de una métrica registrada."""

    if labels is None:
        labels = {}
    return REGISTRY.get_sample_value(metric_name, labels=labels)


__all__ = [
    "REGISTRY",
    "get_metric_value",
    "record_audit_acknowledgement",
    "record_audit_acknowledgement_failure",
    "record_reminder_cache_hit",
    "record_reminder_cache_invalidation",
    "record_reminder_cache_miss",
]
