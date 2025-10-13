"""Rutas de auditoría corporativa."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import AUDITORIA_ROLES
from ..database import get_db
from ..security import require_roles

router = APIRouter(prefix="/audit", tags=["auditoría"])


@router.get("/logs", response_model=list[schemas.AuditLogResponse])
def list_audit_logs_endpoint(
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = None,
    entity_type: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*AUDITORIA_ROLES)),
):
    return crud.list_audit_logs(db, limit=limit, action=action, entity_type=entity_type)


__all__ = ["router"]
