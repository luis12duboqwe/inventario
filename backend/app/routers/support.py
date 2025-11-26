from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import ADMIN, GERENTE
from ..database import get_db
from ..security import get_current_user, require_roles

router = APIRouter(prefix="/support", tags=["soporte"])


async def _get_optional_user(
    request: Request, db: Session = Depends(get_db)
):
    try:
        return await get_current_user(request=request, token=None, db=db)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_401_UNAUTHORIZED:
            raise
        return None


@router.post(
    "/feedback",
    response_model=schemas.FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    payload: schemas.FeedbackCreate,
    db: Session = Depends(get_db),
    current_user=Depends(_get_optional_user),
) -> schemas.FeedbackResponse:
    user_id = getattr(current_user, "id_usuario", None) if current_user else None
    entry = crud.create_support_feedback(db, payload=payload, user_id=user_id)
    return schemas.FeedbackResponse.model_validate(entry)


@router.patch(
    "/feedback/{tracking_id}",
    response_model=schemas.FeedbackResponse,
    dependencies=[Depends(require_roles(ADMIN, GERENTE))],
)
async def update_feedback_status(
    tracking_id: str,
    payload: schemas.FeedbackStatusUpdate,
    db: Session = Depends(get_db),
) -> schemas.FeedbackResponse:
    entry = crud.update_support_feedback_status(
        db,
        tracking_id=tracking_id,
        status=payload.status,
        resolution_notes=payload.resolution_notes,
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback no encontrado",
        )
    return schemas.FeedbackResponse.model_validate(entry)


@router.get(
    "/feedback/metrics",
    response_model=schemas.FeedbackMetrics,
    dependencies=[Depends(require_roles(ADMIN, GERENTE))],
)
async def feedback_metrics(db: Session = Depends(get_db)) -> schemas.FeedbackMetrics:
    return crud.support_feedback_metrics(db)


__all__ = ["router"]
