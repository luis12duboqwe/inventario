"""Endpoints para auditar devoluciones de compras y ventas."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..config import settings
from ..core.roles import MOVEMENT_ROLES
from ..database import get_db
from ..security import require_roles
from ..services import returns as returns_service

router = APIRouter(prefix="/returns", tags=["devoluciones"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(
            status_code=404,
            detail="Funcionalidad no disponible",
        )


@router.get(
    "",
    response_model=schemas.ReturnsOverview,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def list_returns_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    return_type: schemas.ReturnRecordType | None = Query(default=None, alias="type"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.ReturnsOverview:
    _ensure_feature_enabled()
    return returns_service.list_returns(
        db,
        store_id=store_id,
        kind=return_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


__all__ = ["router"]
