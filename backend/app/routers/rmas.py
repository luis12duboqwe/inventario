from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..config import settings
from ..core.roles import MOVEMENT_ROLES
from ..database import get_db
from ..security import require_roles
from ..routers.dependencies import require_reason
from ..services import rma as rma_service

router = APIRouter(prefix="/returns/rma", tags=["rma"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(status_code=404, detail="Funcionalidad no disponible")


@router.post(
    "",
    response_model=schemas.RMARecord,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES)), Depends(require_reason)],
)
def create_rma_endpoint(
    payload: schemas.RMACreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.RMARecord:
    _ensure_feature_enabled()
    return rma_service.create_rma(db, payload, created_by_id=current_user.id)


@router.get(
    "/{rma_id}",
    response_model=schemas.RMARecord,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def get_rma_endpoint(
    rma_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.RMARecord:
    _ensure_feature_enabled()
    return rma_service.get_rma(db, rma_id)


@router.post(
    "/{rma_id}/authorize",
    response_model=schemas.RMARecord,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES)), Depends(require_reason)],
)
def authorize_rma_endpoint(
    rma_id: int,
    payload: schemas.RMAUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.RMARecord:
    _ensure_feature_enabled()
    return rma_service.authorize_rma(
        db,
        rma_id,
        notes=payload.notes,
        actor_id=current_user.id,
    )


@router.post(
    "/{rma_id}/process",
    response_model=schemas.RMARecord,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES)), Depends(require_reason)],
)
def process_rma_endpoint(
    rma_id: int,
    payload: schemas.RMAUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.RMARecord:
    _ensure_feature_enabled()
    return rma_service.process_rma(
        db,
        rma_id,
        payload=payload,
        actor_id=current_user.id,
    )


@router.post(
    "/{rma_id}/close",
    response_model=schemas.RMARecord,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES)), Depends(require_reason)],
)
def close_rma_endpoint(
    rma_id: int,
    payload: schemas.RMAUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.RMARecord:
    _ensure_feature_enabled()
    return rma_service.close_rma(
        db,
        rma_id,
        payload=payload,
        actor_id=current_user.id,
    )


__all__ = ["router"]
