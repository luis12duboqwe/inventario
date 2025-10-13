"""Reportes consolidados y bitácoras."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..security import require_roles

router = APIRouter(prefix="/reports", tags=["reportes"])


@router.get("/audit", response_model=list[schemas.AuditLogResponse])
def audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "auditor")),
):
    return crud.list_audit_logs(db, limit=limit)
