"""Servicios para construir la vista consolidada de observabilidad."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from math import ceil, floor
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from . import observability_alerts
from . import sync_queue

_SYNC_FAILURE_WARNING_THRESHOLD = 3
_SYNC_FAILURE_CRITICAL_THRESHOLD = 5
_DTE_FAILURE_THRESHOLD = 3
_DTE_CRITICAL_THRESHOLD = 5
_DTE_REJECTION_WINDOW = timedelta(hours=6)


def _round_seconds(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    normalized = sorted(values)
    if len(normalized) == 1:
        return normalized[0]
    index = percentile * (len(normalized) - 1)
    lower = floor(index)
    upper = ceil(index)
    lower_value = normalized[lower]
    upper_value = normalized[upper]
    if lower == upper:
        return lower_value
    fraction = index - lower
    return lower_value + (upper_value - lower_value) * fraction


def _extend_latency_samples(
    stats: Iterable[schemas.SyncOutboxStatsEntry],
    reference: datetime,
) -> tuple[list[schemas.ObservabilityLatencySample], list[float]]:
    samples: list[schemas.ObservabilityLatencySample] = []
    values: list[float] = []
    for stat in stats:
        oldest_seconds: float | None = None
        if stat.oldest_pending is not None:
            delta = reference - stat.oldest_pending
            oldest_seconds = max(delta.total_seconds(), 0.0)
        samples.append(
            schemas.ObservabilityLatencySample(
                entity_type=stat.entity_type,
                pending=stat.pending,
                failed=stat.failed,
                oldest_pending_seconds=_round_seconds(oldest_seconds),
                latest_update=stat.latest_update,
            )
        )
        if oldest_seconds is not None and stat.pending > 0:
            values.extend([oldest_seconds] * stat.pending)
    return samples, values


def _resolve_sync_notifications(
    stats: Iterable[schemas.SyncOutboxStatsEntry],
) -> list[schemas.ObservabilityNotification]:
    notifications: list[schemas.ObservabilityNotification] = []
    for stat in stats:
        if stat.failed < _SYNC_FAILURE_WARNING_THRESHOLD:
            continue
        if stat.failed >= _SYNC_FAILURE_CRITICAL_THRESHOLD:
            severity = schemas.SystemLogLevel.CRITICAL
        else:
            severity = schemas.SystemLogLevel.ERROR
        notifications.append(
            schemas.ObservabilityNotification(
                id=f"sync-outbox-{stat.entity_type}",
                title="Fallas en sincronización híbrida",
                message=(
                    f"{stat.failed} eventos fallidos en sync_outbox para "
                    f"{stat.entity_type}."
                ),
                severity=severity,
                occurred_at=stat.latest_update,
                reference=stat.entity_type,
            )
        )
    return notifications


def _resolve_dte_notifications(db: Session, reference: datetime) -> list[schemas.ObservabilityNotification]:
    notifications: list[schemas.ObservabilityNotification] = []

    failed_dispatch_rows = list(
        db.scalars(
            select(models.DTEDispatchQueue)
            .where(models.DTEDispatchQueue.status == models.DTEDispatchStatus.FAILED)
            .order_by(models.DTEDispatchQueue.updated_at.desc())
        )
    )
    failed_dispatch_count = len(failed_dispatch_rows)
    if failed_dispatch_count >= _DTE_FAILURE_THRESHOLD:
        top_entry = failed_dispatch_rows[0]
        severity = (
            schemas.SystemLogLevel.CRITICAL
            if failed_dispatch_count >= _DTE_CRITICAL_THRESHOLD
            else schemas.SystemLogLevel.ERROR
        )
        notifications.append(
            schemas.ObservabilityNotification(
                id="dte-dispatch-failures",
                title="Reintentos fallidos de DTE",
                message=(
                    f"{failed_dispatch_count} documentos con envíos fallidos en la cola DTE."
                ),
                severity=severity,
                occurred_at=top_entry.updated_at,
                reference=str(top_entry.document_id),
            )
        )

    window_start = reference - _DTE_REJECTION_WINDOW
    rejected_stmt = select(func.count(models.DTEDocument.id)).where(
        models.DTEDocument.status == models.DTEStatus.RECHAZADO,
        models.DTEDocument.updated_at >= window_start,
    )
    rejected_count = int(db.execute(rejected_stmt).scalar_one() or 0)
    if rejected_count >= _DTE_FAILURE_THRESHOLD:
        latest_rejected_stmt = select(func.max(models.DTEDocument.updated_at)).where(
            models.DTEDocument.status == models.DTEStatus.RECHAZADO
        )
        latest_rejected = db.execute(latest_rejected_stmt).scalar_one()
        notifications.append(
            schemas.ObservabilityNotification(
                id="dte-rejections",
                title="Documentos DTE rechazados",
                message=(
                    f"{rejected_count} documentos fueron rechazados por Hacienda en las últimas "
                    f"{int(_DTE_REJECTION_WINDOW.total_seconds() // 3600)} horas."
                ),
                severity=schemas.SystemLogLevel.WARNING,
                occurred_at=latest_rejected,
                reference="dte",
            )
        )

    return notifications


def build_observability_snapshot(db: Session) -> schemas.ObservabilitySnapshot:
    """Compila logs, métricas y alertas técnicas para el panel TI."""

    overview = crud.build_global_report_overview(db)
    raw_stats = crud.get_sync_outbox_statistics(db)
    outbox_stats = [
        schemas.SyncOutboxStatsEntry.model_validate(item) for item in raw_stats
    ]

    now = datetime.utcnow()
    latency_samples, latency_values = _extend_latency_samples(outbox_stats, now)
    average_latency = (
        sum(latency_values) / len(latency_values) if latency_values else None
    )
    latency_summary = schemas.ObservabilityLatencySummary(
        average_seconds=_round_seconds(average_latency),
        percentile_95_seconds=_round_seconds(_percentile(latency_values, 0.95)),
        max_seconds=_round_seconds(max(latency_values) if latency_values else None),
        samples=latency_samples,
    )

    latest_error_at = None
    if overview.recent_errors:
        latest_error_at = max(error.fecha for error in overview.recent_errors)
    error_summary = schemas.ObservabilityErrorSummary(
        total_logs=overview.totals.logs,
        total_errors=overview.totals.errors,
        info=overview.totals.info,
        warning=overview.totals.warning,
        error=overview.totals.error,
        critical=overview.totals.critical,
        latest_error_at=latest_error_at,
    )

    total_pending = sum(stat.pending for stat in outbox_stats)
    total_failed = sum(stat.failed for stat in outbox_stats)

    dte_failed_count = int(
        db.execute(
            select(func.count(models.DTEDispatchQueue.id)).where(
                models.DTEDispatchQueue.status == models.DTEDispatchStatus.FAILED
            )
        ).scalar_one()
        or 0
    )
    total_failed += dte_failed_count
    try:
        hybrid_progress = sync_queue.calculate_hybrid_progress(db)
    except Exception:  # pragma: no cover - defensivo ante esquemas parciales
        hybrid_progress = None
    sync_summary = schemas.ObservabilitySyncSummary(
        outbox_stats=outbox_stats,
        total_pending=total_pending,
        total_failed=total_failed,
        hybrid_progress=hybrid_progress,
    )

    notifications: list[schemas.ObservabilityNotification] = []
    notifications.extend(_resolve_sync_notifications(outbox_stats))
    notifications.extend(_resolve_dte_notifications(db, now))

    operational_alerts = observability_alerts.collect_operational_notifications(db)
    notifications.extend(operational_alerts.notifications)
    if operational_alerts.newly_logged:
        observability_alerts.dispatch_external_notifications(
            operational_alerts.newly_logged
        )

    snapshot = schemas.ObservabilitySnapshot(
        generated_at=now,
        latency=latency_summary,
        errors=error_summary,
        sync=sync_summary,
        logs=overview.recent_logs,
        system_errors=overview.recent_errors,
        alerts=overview.alerts,
        notifications=notifications,
    )
    return snapshot


__all__ = ["build_observability_snapshot"]
