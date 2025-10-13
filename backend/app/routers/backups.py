"""Gestión de respaldos y descargas empresariales."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import ADMIN, REPORTE_ROLES
from ..database import get_db
from ..security import require_roles
from ..services import backups as backup_services

router = APIRouter(prefix="/backups", tags=["respaldos"])


@router.post("/run", response_model=schemas.BackupJobResponse, status_code=status.HTTP_201_CREATED)
def run_backup(
    payload: schemas.BackupRunRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    notes = payload.nota or "Respaldo manual"
    job = backup_services.generate_backup(
        db,
        base_dir=settings.backup_directory,
        mode=models.BackupMode.MANUAL,
        triggered_by_id=current_user.id if current_user else None,
        notes=notes,
    )
    return job


@router.get("/history", response_model=list[schemas.BackupJobResponse])
def backup_history(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    return crud.list_backup_jobs(db, limit=100)
