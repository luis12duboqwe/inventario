"""Rutas de auditoría corporativa."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import AUDITORIA_ROLES
from ..database import get_db
from ..security import require_roles
from ..utils import audit as audit_utils

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


__all__ = ["router"]
