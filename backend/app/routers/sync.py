"""Sincronización automática y bajo demanda."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.core.logging import logger as core_logger

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import ADMIN, GESTION_ROLES
from ..core.transactions import transactional_session
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import sync as sync_service
from ..services import sync_conflict_reports
from ..services import sync_queue

logger = core_logger.bind(component=__name__)

router = APIRouter(prefix="/sync", tags=["sincronizacion"])


def _ensure_hybrid_enabled() -> None:
    if not settings.enable_hybrid_prep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")


@router.post("/run", response_model=schemas.SyncSessionResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def trigger_sync(
    payload: schemas.SyncRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    store_id = payload.store_id
    if store_id is not None:
        try:
            crud.get_store(db, store_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Sucursal no encontrada") from exc

    status = models.SyncStatus.SUCCESS
    error_message: str | None = None
    processed_events = 0
    differences_count = 0
    try:
        with transactional_session(db):
            requeued = sync_service.requeue_failed_outbox_entries(db)
            if requeued:
                logger.info(
                    f"Cola híbrida: {len(requeued)} eventos listos para reintentar"
                )
            result = sync_service.run_sync_cycle(
                db,
                store_id=store_id,
                performed_by_id=current_user.id if current_user else None,
            )
            processed_events = int(result.get("processed", 0))
            discrepancies = result.get("discrepancies", [])
            differences_count = (
                len(discrepancies) if isinstance(discrepancies, list) else 0
            )
    except Exception as exc:
        status = models.SyncStatus.FAILED
        error_message = str(exc)
        logger.exception(
            f"No fue posible completar la sincronización manual: {exc}"
        )

    session = crud.record_sync_session(
        db,
        store_id=store_id,
        mode=models.SyncMode.MANUAL,
        status=status,
        triggered_by_id=current_user.id if current_user else None,
        error_message=error_message,
        processed_events=processed_events,
        differences_detected=differences_count,
    )
    if status is models.SyncStatus.FAILED:
        raise HTTPException(status_code=500, detail="No fue posible completar la sincronización")
    return session


# // [PACK35-backend]
@router.post(
    "/events",
    response_model=schemas.SyncQueueEnqueueResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def enqueue_queue_events(
    payload: schemas.SyncQueueEnqueueRequest,
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    queued, reused = crud.enqueue_sync_queue_events(db, payload.events)
    return schemas.SyncQueueEnqueueResponse(
        queued=[schemas.SyncQueueEntryResponse.model_validate(item) for item in queued],
        reused=[schemas.SyncQueueEntryResponse.model_validate(item) for item in reused],
    )


# // [PACK35-backend]
@router.post(
    "/dispatch",
    response_model=schemas.SyncQueueDispatchResult,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def dispatch_queue_events(
    limit: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    return sync_queue.dispatch_pending_events(db, limit=limit)


# // [PACK35-backend]
@router.get(
    "/status",
    response_model=list[schemas.SyncQueueEntryResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def list_queue_status(
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: models.SyncQueueStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    statuses: tuple[models.SyncQueueStatus, ...] | None = (
        (status_filter,)
        if status_filter is not None
        else None
    )
    return sync_queue.list_queue_status(db, limit=limit, statuses=statuses)


# // [PACK35-backend]
@router.get(
    "/status/summary",
    response_model=schemas.SyncQueueProgressSummary,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def queue_progress_summary(
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    return sync_queue.queue_progress_summary(db)


# // [PACK35-backend]
@router.get(
    "/status/hybrid",
    response_model=schemas.SyncHybridProgressSummary,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def hybrid_progress_summary(
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    return sync_queue.calculate_hybrid_progress(db)


# // [PACK35-backend]
@router.get(
    "/status/forecast",
    response_model=schemas.SyncHybridForecast,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def hybrid_progress_forecast(
    lookback_minutes: int = Query(default=60, ge=5, le=360),
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    return sync_queue.calculate_hybrid_forecast(db, lookback_minutes=lookback_minutes)


# // [PACK35-backend]
@router.get(
    "/status/breakdown",
    response_model=list[schemas.SyncHybridModuleBreakdownItem],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def hybrid_progress_breakdown(
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    return sync_queue.calculate_hybrid_breakdown(db)


# // [PACK35-backend]
@router.get(
    "/status/overview",
    response_model=schemas.SyncHybridOverview,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def hybrid_progress_overview(
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    return sync_queue.calculate_hybrid_overview(db)


# // [PACK35-backend]
@router.post(
    "/resolve/{queue_id}",
    response_model=schemas.SyncQueueEntryResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def resolve_queue_entry(
    queue_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    try:
        return sync_queue.mark_entry_resolved(db, queue_id)
    except LookupError as exc:  # pragma: no cover - protección extra
        raise HTTPException(status_code=404, detail="Evento no encontrado") from exc


@router.get("/sessions", response_model=list[schemas.SyncSessionResponse], dependencies=[Depends(require_roles(ADMIN))])
def list_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.list_sync_sessions(db, limit=limit, offset=offset)


@router.get("/overview", response_model=list[schemas.SyncBranchOverview], dependencies=[Depends(require_roles(ADMIN))])
def sync_overview(
    store_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    data = crud.get_store_sync_overview(
        db, store_id=store_id, limit=limit, offset=offset
    )
    return [schemas.SyncBranchOverview(**entry) for entry in data]


def _prepare_conflict_report(
    db: Session,
    *,
    store_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    severity: schemas.SyncBranchHealth | None,
) -> schemas.SyncConflictReport:
    conflicts = crud.list_sync_conflicts(
        db,
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
        limit=500,
        offset=0,
    )
    filters = schemas.SyncConflictReportFilters(
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
    )
    return sync_conflict_reports.build_conflict_report(conflicts, filters)


@router.get("/conflicts", response_model=list[schemas.SyncConflictLog], dependencies=[Depends(require_roles(ADMIN))])
def list_conflicts(
    store_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    severity: schemas.SyncBranchHealth | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.list_sync_conflicts(
        db,
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
        limit=limit,
        offset=offset,
    )


@router.get("/conflicts/export/pdf", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def export_conflicts_pdf(
    store_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    severity: schemas.SyncBranchHealth | None = Query(default=None),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
):
    report = _prepare_conflict_report(
        db,
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
    )
    pdf_bytes = sync_conflict_reports.render_conflict_report_pdf(report)
    metadata = schemas.BinaryFileResponse(
        filename=f"conflictos_sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/conflicts/export/xlsx", response_model=schemas.BinaryFileResponse, dependencies=[Depends(require_roles(ADMIN))])
def export_conflicts_excel(
    store_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    severity: schemas.SyncBranchHealth | None = Query(default=None),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
):
    report = _prepare_conflict_report(
        db,
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
    )
    excel_bytes = sync_conflict_reports.render_conflict_report_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename=f"conflictos_sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/outbox", response_model=list[schemas.SyncOutboxEntryResponse], dependencies=[Depends(require_roles(*GESTION_ROLES))])
def list_outbox_entries(
    status_filter: models.SyncOutboxStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    statuses = [status_filter] if status_filter else None
    entries = crud.list_sync_outbox(db, statuses=statuses, limit=limit, offset=offset)
    return entries


@router.post(
    "/outbox/retry",
    response_model=list[schemas.SyncOutboxEntryResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def retry_outbox_entries(
    payload: schemas.SyncOutboxReplayRequest,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    reason: str = Depends(require_reason),
):
    _ensure_hybrid_enabled()
    entries = crud.reset_outbox_entries(
        db,
        payload.ids,
        performed_by_id=current_user.id if current_user else None,
        reason=reason,
        limit=limit,
        offset=offset,
    )
    if not entries:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entradas no encontradas")
    return entries


@router.get("/outbox/stats", response_model=list[schemas.SyncOutboxStatsEntry], dependencies=[Depends(require_roles(*GESTION_ROLES))])
def outbox_statistics(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    stats = crud.get_sync_outbox_statistics(db, limit=limit, offset=offset)
    return [schemas.SyncOutboxStatsEntry(**item) for item in stats]


@router.get("/history", response_model=list[schemas.SyncStoreHistory], dependencies=[Depends(require_roles(ADMIN))])
def list_sync_history(
    limit_per_store: int = Query(default=5, ge=1, le=20),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    history = crud.list_sync_history_by_store(
        db, limit_per_store=limit_per_store, limit=limit, offset=offset
    )
    results: list[schemas.SyncStoreHistory] = []
    for item in history:
        sessions = [
            schemas.SyncSessionCompact(**session)
            if not isinstance(session, models.SyncSession)
            else schemas.SyncSessionCompact(
                id=session.id,
                mode=session.mode,
                status=session.status,
                started_at=session.started_at,
                finished_at=session.finished_at,
                error_message=session.error_message,
            )
            for session in item["sessions"]
        ]
        results.append(
            schemas.SyncStoreHistory(
                store_id=item["store_id"],
                store_name=item["store_name"],
                sessions=sessions,
            )
        )
    return results
