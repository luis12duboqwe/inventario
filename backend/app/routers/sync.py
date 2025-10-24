"""Sincronización automática y bajo demanda."""
from __future__ import annotations

import logging

from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES, REPORTE_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import sync as sync_service
from ..services import sync_conflict_reports

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sincronizacion"])


def _ensure_hybrid_enabled() -> None:
    if not settings.enable_hybrid_prep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")


@router.post("/run", response_model=schemas.SyncSessionResponse)
def trigger_sync(
    payload: schemas.SyncRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
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
        result = sync_service.run_sync_cycle(
            db,
            store_id=store_id,
            performed_by_id=current_user.id if current_user else None,
        )
        processed_events = int(result.get("processed", 0))
        discrepancies = result.get("discrepancies", [])
        differences_count = len(discrepancies) if isinstance(discrepancies, list) else 0
    except Exception as exc:
        db.rollback()
        status = models.SyncStatus.FAILED
        error_message = str(exc)
        logger.exception("No fue posible completar la sincronización manual: %s", exc)

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


@router.get("/sessions", response_model=list[schemas.SyncSessionResponse])
def list_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    return crud.list_sync_sessions(db, limit=limit)


@router.get("/overview", response_model=list[schemas.SyncBranchOverview])
def sync_overview(
    store_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    data = crud.get_store_sync_overview(db, store_id=store_id)
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
    )
    filters = schemas.SyncConflictReportFilters(
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
    )
    return sync_conflict_reports.build_conflict_report(conflicts, filters)


@router.get("/conflicts", response_model=list[schemas.SyncConflictLog])
def list_conflicts(
    store_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    severity: schemas.SyncBranchHealth | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    return crud.list_sync_conflicts(
        db,
        store_id=store_id,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
        limit=limit,
    )


@router.get("/conflicts/export/pdf", response_model=schemas.BinaryFileResponse)
def export_conflicts_pdf(
    store_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    severity: schemas.SyncBranchHealth | None = Query(default=None),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
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


@router.get("/conflicts/export/xlsx", response_model=schemas.BinaryFileResponse)
def export_conflicts_excel(
    store_id: int | None = Query(default=None, ge=1),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    severity: schemas.SyncBranchHealth | None = Query(default=None),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
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


@router.get("/outbox", response_model=list[schemas.SyncOutboxEntryResponse])
def list_outbox_entries(
    status_filter: models.SyncOutboxStatus | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    statuses = [status_filter] if status_filter else None
    entries = crud.list_sync_outbox(db, statuses=statuses)
    return entries


@router.post("/outbox/retry", response_model=list[schemas.SyncOutboxEntryResponse])
def retry_outbox_entries(
    payload: schemas.SyncOutboxReplayRequest,
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
    )
    if not entries:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entradas no encontradas")
    return entries


@router.get("/outbox/stats", response_model=list[schemas.SyncOutboxStatsEntry])
def outbox_statistics(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_hybrid_enabled()
    stats = crud.get_sync_outbox_statistics(db)
    return [schemas.SyncOutboxStatsEntry(**item) for item in stats]


@router.get("/history", response_model=list[schemas.SyncStoreHistory])
def list_sync_history(
    limit_per_store: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    history = crud.list_sync_history_by_store(db, limit_per_store=limit_per_store)
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
