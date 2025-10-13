"""Sincronización automática y bajo demanda."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..security import require_roles

router = APIRouter(prefix="/sync", tags=["sincronizacion"])


@router.post("/run", response_model=schemas.SyncSessionResponse)
def trigger_sync(
    payload: schemas.SyncRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
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
    current_user=Depends(require_roles("admin", "manager", "auditor")),
):
    return crud.list_sync_sessions(db, limit=limit)
