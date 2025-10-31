"""Servicios para la cola híbrida de sincronización."""
# // [PACK35-backend]

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

import httpx
from sqlalchemy.orm import Session

from backend.core.logging import logger as core_logger

from .. import crud, models, schemas
from ..config import settings

logger = core_logger.bind(component=__name__)


# // [PACK35-backend]
MODULE_LABELS: dict[str, str] = {
    "inventory": "Inventario",
    "pos": "Ventas POS",
    "sales": "Ventas",
    "purchases": "Compras",
    "transfers": "Transferencias",
    "repairs": "Reparaciones",
    "customers": "Clientes",
    "suppliers": "Proveedores",
    "security": "Seguridad",
    "audit": "Auditoría",
}



def _retry_delay_seconds(attempt_number: int) -> int:
    base = max(5, settings.sync_retry_interval_seconds // 2)
    exponent = max(0, attempt_number - 1)
    return min(base * (2**exponent), settings.sync_retry_interval_seconds * 4)


def _normalize_dt(value: datetime | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _extract_module_key(raw: str | None) -> str:
    if not raw:
        return "general"
    candidate = raw.split(".")[0].split(":")[0].strip().lower()
    return candidate or "general"


def _friendly_module_label(module: str) -> str:
    base = MODULE_LABELS.get(module)
    if base:
        return base
    sanitized = module.replace("_", " ").replace("-", " ").strip()
    return sanitized.title() if sanitized else "General"


def _should_attempt(entry: models.SyncQueue, now: datetime) -> bool:
    if (
        entry.status is models.SyncQueueStatus.FAILED
        and entry.attempts >= max(1, settings.sync_max_attempts)
    ):
        return False
    if entry.status is models.SyncQueueStatus.PENDING and entry.attempts == 0:
        return True
    reference = _normalize_dt(entry.updated_at or entry.created_at)
    delay_seconds = _retry_delay_seconds(max(1, entry.attempts))
    return now >= reference + timedelta(seconds=delay_seconds)


def _dispatch_remote(entry: models.SyncQueue) -> tuple[bool, str | None]:
    target_url = (settings.sync_remote_url or "").strip()
    if not target_url:
        return True, None

    payload = {
        "event_type": entry.event_type,
        "payload": entry.payload,
        "idempotency_key": entry.idempotency_key,
    }
    try:
        response = httpx.post(target_url, json=payload, timeout=15.0)
        response.raise_for_status()
        return True, None
    except httpx.HTTPError as exc:  # pragma: no cover - depende de red externa
        logger.warning("Error al despachar evento remoto", error=str(exc))
        return False, str(exc)


def dispatch_pending_events(
    db: Session,
    *,
    limit: int = 25,
) -> schemas.SyncQueueDispatchResult:
    candidates = crud.fetch_sync_queue_candidates(db, limit=limit)
    now = datetime.utcnow()
    processed = 0
    sent = 0
    failed = 0
    retried = 0

    for entry in candidates:
        if not _should_attempt(entry, now):
            continue

        processed += 1
        success, error_message = _dispatch_remote(entry)

        next_status = models.SyncQueueStatus.SENT if success else models.SyncQueueStatus.PENDING
        next_attempt_number = entry.attempts + 1

        if not success and next_attempt_number >= max(1, settings.sync_max_attempts):
            next_status = models.SyncQueueStatus.FAILED

        updated_entry = crud.update_sync_queue_entry(
            db,
            entry,
            status=next_status,
            error_message=error_message,
            increment_attempt=True,
        )
        crud.record_sync_attempt(
            db,
            queue_entry=updated_entry,
            success=success,
            error_message=error_message,
        )

        if success:
            sent += 1
        else:
            retried += 1
            if next_status is models.SyncQueueStatus.FAILED:
                failed += 1

    return schemas.SyncQueueDispatchResult(
        processed=processed,
        sent=sent,
        failed=failed,
        retried=retried,
    )


def mark_entry_resolved(db: Session, entry_id: int) -> schemas.SyncQueueEntryResponse:
    entry = crud.get_sync_queue_entry(db, entry_id)
    resolved = crud.resolve_sync_queue_entry(db, entry)
    crud.record_sync_attempt(db, queue_entry=resolved, success=True, error_message=None)
    return schemas.SyncQueueEntryResponse.model_validate(resolved)


def list_queue_status(
    db: Session,
    *,
    limit: int = 50,
    statuses: Iterable[models.SyncQueueStatus] | None = None,
) -> list[schemas.SyncQueueEntryResponse]:
    entries = crud.list_sync_queue_entries(db, statuses=statuses, limit=limit, offset=0)
    return [schemas.SyncQueueEntryResponse.model_validate(item) for item in entries]


# // [PACK35-backend]
def queue_progress_summary(db: Session) -> schemas.SyncQueueProgressSummary:
    totals = crud.summarize_sync_queue_statuses(db)
    total = sum(totals.values())
    processed = totals.get(models.SyncQueueStatus.SENT, 0)
    pending = totals.get(models.SyncQueueStatus.PENDING, 0)
    failed = totals.get(models.SyncQueueStatus.FAILED, 0)
    percent = 100.0 if total == 0 else round((processed / max(total, 1)) * 100, 2)
    last_updated = crud.get_latest_sync_queue_update(db)
    oldest_pending = crud.get_oldest_pending_sync_queue_update(db)

    return schemas.SyncQueueProgressSummary(
        percent=percent,
        total=total,
        processed=processed,
        pending=pending,
        failed=failed,
        last_updated=_normalize_dt(last_updated) if last_updated else None,
        oldest_pending=_normalize_dt(oldest_pending) if oldest_pending else None,
    )


# // [PACK35-backend]
def calculate_hybrid_progress(db: Session) -> schemas.SyncHybridProgressSummary:
    queue_totals = crud.summarize_sync_queue_statuses(db)
    queue_total = sum(queue_totals.values())
    queue_processed = queue_totals.get(models.SyncQueueStatus.SENT, 0)
    queue_pending = queue_totals.get(models.SyncQueueStatus.PENDING, 0)
    queue_failed = queue_totals.get(models.SyncQueueStatus.FAILED, 0)
    queue_latest = crud.get_latest_sync_queue_update(db)
    queue_oldest_pending = crud.get_oldest_pending_sync_queue_update(db)

    outbox_totals = crud.summarize_sync_outbox_statuses(db)
    outbox_total = sum(outbox_totals.values())
    outbox_processed = outbox_totals.get(models.SyncOutboxStatus.SENT, 0)
    outbox_pending = outbox_totals.get(models.SyncOutboxStatus.PENDING, 0)
    outbox_failed = outbox_totals.get(models.SyncOutboxStatus.FAILED, 0)
    outbox_latest = crud.get_latest_sync_outbox_update(db)
    outbox_oldest_pending = crud.get_oldest_pending_sync_outbox_update(db)

    queue_component = schemas.SyncHybridComponentSummary(
        total=queue_total,
        processed=queue_processed,
        pending=queue_pending,
        failed=queue_failed,
        latest_update=_normalize_dt(queue_latest) if queue_latest else None,
        oldest_pending=_normalize_dt(queue_oldest_pending) if queue_oldest_pending else None,
    )
    outbox_component = schemas.SyncHybridComponentSummary(
        total=outbox_total,
        processed=outbox_processed,
        pending=outbox_pending,
        failed=outbox_failed,
        latest_update=_normalize_dt(outbox_latest) if outbox_latest else None,
        oldest_pending=_normalize_dt(outbox_oldest_pending) if outbox_oldest_pending else None,
    )

    combined_total = queue_component.total + outbox_component.total
    combined_processed = queue_component.processed + outbox_component.processed
    combined_pending = queue_component.pending + outbox_component.pending
    combined_failed = queue_component.failed + outbox_component.failed
    percent = (
        100.0
        if combined_total == 0
        else round((combined_processed / max(combined_total, 1)) * 100, 2)
    )

    return schemas.SyncHybridProgressSummary(
        percent=percent,
        total=combined_total,
        processed=combined_processed,
        pending=combined_pending,
        failed=combined_failed,
        components=schemas.SyncHybridProgressComponents(
            queue=queue_component,
            outbox=outbox_component,
        ),
    )


# // [PACK35-backend]
def calculate_hybrid_forecast(
    db: Session,
    *,
    lookback_minutes: int = 60,
) -> schemas.SyncHybridForecast:
    """Estima el tiempo restante para completar la cola híbrida."""

    normalized_window = max(5, lookback_minutes)
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=normalized_window)

    queue_totals = crud.summarize_sync_queue_statuses(db)
    outbox_totals = crud.summarize_sync_outbox_statuses(db)

    queue_processed_recent = crud.count_sync_queue_processed_since(db, window_start)
    outbox_processed_recent = crud.count_sync_outbox_processed_since(db, window_start)
    processed_recent = queue_processed_recent + outbox_processed_recent

    attempts_total, attempts_successful = crud.count_sync_attempts_since(db, window_start)

    raw_events_per_minute = (
        processed_recent / normalized_window if normalized_window > 0 else 0.0
    )
    events_per_minute = round(raw_events_per_minute, 2)

    success_rate = (
        round((attempts_successful / attempts_total) * 100, 2)
        if attempts_total
        else 0.0
    )

    backlog_pending = (
        queue_totals.get(models.SyncQueueStatus.PENDING, 0)
        + outbox_totals.get(models.SyncOutboxStatus.PENDING, 0)
    )
    backlog_failed = (
        queue_totals.get(models.SyncQueueStatus.FAILED, 0)
        + outbox_totals.get(models.SyncOutboxStatus.FAILED, 0)
    )
    backlog_total = backlog_pending + backlog_failed

    estimated_minutes_remaining: float | None = None
    estimated_completion: datetime | None = None
    if raw_events_per_minute > 0 and backlog_total > 0:
        estimated_minutes_remaining = round(backlog_total / raw_events_per_minute, 2)
        estimated_completion = now + timedelta(minutes=estimated_minutes_remaining)

    progress_summary = calculate_hybrid_progress(db)

    return schemas.SyncHybridForecast(
        lookback_minutes=normalized_window,
        processed_recent=processed_recent,
        processed_queue=queue_processed_recent,
        processed_outbox=outbox_processed_recent,
        attempts_total=attempts_total,
        attempts_successful=attempts_successful,
        success_rate=success_rate,
        events_per_minute=events_per_minute,
        backlog_pending=backlog_pending,
        backlog_failed=backlog_failed,
        backlog_total=backlog_total,
        estimated_minutes_remaining=estimated_minutes_remaining,
        estimated_completion=estimated_completion,
        generated_at=now,
        progress=progress_summary,
    )


# // [PACK35-backend]
def calculate_hybrid_breakdown(
    db: Session,
) -> list[schemas.SyncHybridModuleBreakdownItem]:
    """Construye un desglose por módulo con porcentajes de finalización."""

    queue_by_event = crud.summarize_sync_queue_by_event_type(db)
    outbox_by_entity = crud.summarize_sync_outbox_by_entity_type(db)

    modules: dict[str, dict[str, dict[object, int]]] = {}

    for event_type, totals in queue_by_event.items():
        module_key = _extract_module_key(event_type)
        module_bucket = modules.setdefault(
            module_key,
            {
                "queue": {status: 0 for status in models.SyncQueueStatus},
                "outbox": {status: 0 for status in models.SyncOutboxStatus},
            },
        )
        for status, amount in totals.items():
            if isinstance(status, models.SyncQueueStatus):
                module_bucket["queue"][status] = module_bucket["queue"].get(status, 0) + int(
                    amount or 0
                )

    for entity_type, totals in outbox_by_entity.items():
        module_key = _extract_module_key(entity_type)
        module_bucket = modules.setdefault(
            module_key,
            {
                "queue": {status: 0 for status in models.SyncQueueStatus},
                "outbox": {status: 0 for status in models.SyncOutboxStatus},
            },
        )
        for status, amount in totals.items():
            if isinstance(status, models.SyncOutboxStatus):
                module_bucket["outbox"][status] = module_bucket["outbox"].get(status, 0) + int(
                    amount or 0
                )

    breakdown: list[schemas.SyncHybridModuleBreakdownItem] = []
    for module_key, data in modules.items():
        queue_counts = data["queue"]
        outbox_counts = data["outbox"]

        queue_total = sum(queue_counts.values())
        queue_processed = queue_counts.get(models.SyncQueueStatus.SENT, 0)
        queue_pending = queue_counts.get(models.SyncQueueStatus.PENDING, 0)
        queue_failed = queue_counts.get(models.SyncQueueStatus.FAILED, 0)

        outbox_total = sum(outbox_counts.values())
        outbox_processed = outbox_counts.get(models.SyncOutboxStatus.SENT, 0)
        outbox_pending = outbox_counts.get(models.SyncOutboxStatus.PENDING, 0)
        outbox_failed = outbox_counts.get(models.SyncOutboxStatus.FAILED, 0)

        total = queue_total + outbox_total
        processed = queue_processed + outbox_processed
        pending = queue_pending + outbox_pending
        failed = queue_failed + outbox_failed
        percent = 100.0 if total == 0 else round((processed / max(total, 1)) * 100, 2)

        queue_component = schemas.SyncHybridModuleBreakdownComponent(
            total=queue_total,
            processed=queue_processed,
            pending=queue_pending,
            failed=queue_failed,
        )
        outbox_component = schemas.SyncHybridModuleBreakdownComponent(
            total=outbox_total,
            processed=outbox_processed,
            pending=outbox_pending,
            failed=outbox_failed,
        )

        breakdown.append(
            schemas.SyncHybridModuleBreakdownItem(
                module=module_key,
                label=_friendly_module_label(module_key),
                total=total,
                processed=processed,
                pending=pending,
                failed=failed,
                percent=percent,
                queue=queue_component,
                outbox=outbox_component,
            )
        )

    breakdown.sort(
        key=lambda item: (
            -(item.pending + item.failed),
            item.percent,
            item.label.lower(),
        )
    )
    return breakdown


# // [PACK35-backend]
def calculate_hybrid_overview(db: Session) -> schemas.SyncHybridOverview:
    """Consolida el estado híbrido destacando el porcentaje total para finalizar."""

    queue_summary = queue_progress_summary(db)
    forecast = calculate_hybrid_forecast(db)
    progress = forecast.progress
    breakdown = calculate_hybrid_breakdown(db)

    queue_component = progress.components.queue
    outbox_component = progress.components.outbox

    remaining = schemas.SyncHybridRemainingBreakdown(
        total=progress.pending + progress.failed,
        pending=progress.pending,
        failed=progress.failed,
        remote_pending=queue_component.pending,
        remote_failed=queue_component.failed,
        outbox_pending=outbox_component.pending,
        outbox_failed=outbox_component.failed,
        estimated_minutes_remaining=forecast.estimated_minutes_remaining,
        estimated_completion=forecast.estimated_completion,
    )

    return schemas.SyncHybridOverview(
        generated_at=forecast.generated_at,
        percent=progress.percent,
        total=progress.total,
        processed=progress.processed,
        pending=progress.pending,
        failed=progress.failed,
        remaining=remaining,
        queue_summary=queue_summary,
        progress=progress,
        forecast=forecast,
        breakdown=breakdown,
    )
