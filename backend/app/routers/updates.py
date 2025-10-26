"""Rutas para consultar el estado de actualizaciones del sistema."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .. import schemas
from ..core.roles import ADMIN
from ..security import require_roles
from ..services import updates as update_services

router = APIRouter(prefix="/updates", tags=["actualizaciones"])


@router.get("/status", response_model=schemas.UpdateStatus, dependencies=[Depends(require_roles(ADMIN))])
def read_update_status(current_user=Depends(require_roles(ADMIN))):
    """Devuelve la versión actual y la última disponible en el feed oficial."""

    return update_services.get_update_status()


@router.get("/history", response_model=list[schemas.ReleaseInfo], dependencies=[Depends(require_roles(ADMIN))])
def read_release_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_roles(ADMIN)),
):
    """Lista las versiones publicadas del producto ordenadas de la más reciente a la más antigua."""

    return update_services.get_release_history(limit=limit, offset=offset)

