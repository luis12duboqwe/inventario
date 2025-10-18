"""Gestión de respaldos y descargas empresariales."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import ADMIN
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
        components=payload.componentes,
    )
    return job


@router.get("/history", response_model=list[schemas.BackupJobResponse])
def backup_history(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.list_backup_jobs(db, limit=100)


@router.post("/{job_id}/restore", response_model=schemas.BackupRestoreResponse)
def restore_backup(
    job_id: int,
    payload: schemas.BackupRestoreRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    job = crud.get_backup_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Respaldo no encontrado")

    return backup_services.restore_backup(
        db,
        job=job,
        components=payload.componentes,
        target_directory=payload.destino,
        apply_database=payload.aplicar_base_datos,
        triggered_by_id=current_user.id if current_user else None,
    )
