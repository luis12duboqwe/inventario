"""Rutas de auditoría corporativa."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import AUDITORIA_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/audit", tags=["auditoría"])


@router.get("/logs", response_model=list[schemas.AuditLogResponse])
def list_audit_logs_endpoint(
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=80),
    performed_by_id: int | None = Query(default=None, ge=1),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*AUDITORIA_ROLES)),
):
    return crud.list_audit_logs(
        db,
        limit=limit,
        action=action,
        entity_type=entity_type,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/logs/export.csv")
def export_audit_logs(
    limit: int = Query(default=1000, ge=1, le=5000),
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=80),
    performed_by_id: int | None = Query(default=None, ge=1),
    date_from: datetime | date | None = Query(default=None),
    date_to: datetime | date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*AUDITORIA_ROLES)),
    _reason: str = Depends(require_reason),
):
    csv_data = crud.export_audit_logs_csv(
        db,
        limit=limit,
        action=action,
        entity_type=entity_type,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
    )
    filename = "bitacora_auditoria.csv"
    return PlainTextResponse(
        csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/reminders", response_model=schemas.AuditReminderSummary)
def list_audit_reminders(
    threshold_minutes: int = Query(default=15, ge=0, le=240),
    min_occurrences: int = Query(default=1, ge=1, le=50),
    lookback_hours: int = Query(default=48, ge=1, le=168),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*AUDITORIA_ROLES)),
):
    reminders = crud.get_persistent_audit_alerts(
        db,
        threshold_minutes=threshold_minutes,
        min_occurrences=min_occurrences,
        lookback_hours=lookback_hours,
        limit=limit,
    )
    pending_count = sum(1 for item in reminders if item.get("status") != "acknowledged")
    acknowledged_count = len(reminders) - pending_count
    entries = [
        schemas.AuditReminderEntry(**item)  # type: ignore[arg-type]
        for item in reminders
    ]
    return schemas.AuditReminderSummary(
        threshold_minutes=threshold_minutes,
        min_occurrences=min_occurrences,
        total=len(reminders),
        pending_count=pending_count,
        acknowledged_count=acknowledged_count,
        persistent=entries,
    )


@router.post(
    "/acknowledgements",
    response_model=schemas.AuditAcknowledgementResponse,
    status_code=status.HTTP_201_CREATED,
)
def acknowledge_audit_alert_endpoint(
    payload: schemas.AuditAcknowledgementCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*AUDITORIA_ROLES)),
    _reason: str = Depends(require_reason),
):
    try:
        acknowledgement = crud.acknowledge_audit_alert(
            db,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            acknowledged_by_id=getattr(current_user, "id", None),
            note=payload.note,
        )
    except crud.AuditAcknowledgementNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except crud.AuditAcknowledgementConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    acknowledged_by_name = None
    if acknowledgement.acknowledged_by is not None:
        acknowledged_by_name = (
            acknowledgement.acknowledged_by.full_name
            or acknowledgement.acknowledged_by.username
        )

    return schemas.AuditAcknowledgementResponse(
        entity_type=acknowledgement.entity_type,
        entity_id=acknowledgement.entity_id,
        acknowledged_at=acknowledgement.acknowledged_at,
        acknowledged_by_id=acknowledgement.acknowledged_by_id,
        acknowledged_by_name=acknowledged_by_name,
        note=acknowledgement.note,
    )


__all__ = ["router"]
