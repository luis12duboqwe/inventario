"""Sincronización automática y bajo demanda."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES, REPORTE_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

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

    session = crud.record_sync_session(
        db,
        store_id=store_id,
        mode=models.SyncMode.MANUAL,
        status=models.SyncStatus.SUCCESS,
        triggered_by_id=current_user.id if current_user else None,
    )
    return session


@router.get("/sessions", response_model=list[schemas.SyncSessionResponse])
def list_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    return crud.list_sync_sessions(db, limit=limit)


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
    )
    if not entries:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entradas no encontradas")
    return entries
