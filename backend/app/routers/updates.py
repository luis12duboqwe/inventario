"""Rutas para consultar el estado de actualizaciones del sistema."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from .. import schemas
from ..core.roles import REPORTE_ROLES
from ..security import require_roles
from ..services import updates as update_services

router = APIRouter(prefix="/updates", tags=["actualizaciones"])


@router.get("/status", response_model=schemas.UpdateStatus)
def read_update_status(current_user=Depends(require_roles(*REPORTE_ROLES))):
    """Devuelve la versión actual y la última disponible en el feed oficial."""

    return update_services.get_update_status()


@router.get("/history", response_model=list[schemas.ReleaseInfo])
def read_release_history(
    limit: int = Query(default=10, ge=1, le=50),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    """Lista las versiones publicadas del producto ordenadas de la más reciente a la más antigua."""

    return update_services.get_release_history(limit=limit)

