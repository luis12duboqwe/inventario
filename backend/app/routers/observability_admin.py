"""Endpoint administrativo para observabilidad consolidada."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..core.roles import ADMIN
from ..database import get_db
from ..security import require_roles
from ..services import observability

router = APIRouter(prefix="/admin/observability", tags=["observabilidad"])


@router.get(
    "",
    response_model=schemas.ObservabilitySnapshot,
    dependencies=[Depends(require_roles(ADMIN))],
)
def get_observability_snapshot(
    db: Session = Depends(get_db),
) -> schemas.ObservabilitySnapshot:
    """Devuelve logs y métricas clave para el monitoreo técnico."""

    return observability.build_observability_snapshot(db)


__all__ = ["router"]
