"""Endpoints para gestionar garantías vinculadas a ventas."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/warranties", tags=["warranties"])


@router.get(
    "/",
    response_model=list[schemas.WarrantyAssignmentResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def list_warranties_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    expiring_before: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    status_enum: models.WarrantyStatus | None = None
    if status_filter:
        try:
            status_enum = models.WarrantyStatus(status_filter.upper())
        except ValueError as exc:  # pragma: no cover - FastAPI transforma la excepción
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Estado de garantía inválido",
            ) from exc
    return crud.list_warranty_assignments(
        db,
        store_id=store_id,
        status=status_enum,
        query=q,
        expiring_before=expiring_before,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/metrics",
    response_model=schemas.WarrantyMetrics,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_warranty_metrics_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    horizon_days: int = Query(default=30, ge=0, le=365),
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    return crud.get_warranty_metrics(
        db,
        store_id=store_id,
        horizon_days=horizon_days,
    )


@router.get(
    "/{assignment_id}",
    response_model=schemas.WarrantyAssignmentResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_warranty_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_warranty_assignment(db, assignment_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garantía no encontrada",
        ) from exc


@router.post(
    "/{assignment_id}/claims",
    response_model=schemas.WarrantyAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def create_warranty_claim_endpoint(
    assignment_id: int,
    payload: schemas.WarrantyClaimCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.register_warranty_claim(
            db,
            assignment_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garantía no encontrada",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "warranty_expired":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La garantía ya se encuentra vencida.",
            ) from exc
        raise


@router.patch(
    "/claims/{claim_id}",
    response_model=schemas.WarrantyAssignmentResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def update_warranty_claim_endpoint(
    claim_id: int,
    payload: schemas.WarrantyClaimStatusUpdate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        claim = crud.update_warranty_claim_status(
            db,
            claim_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reclamo no encontrado",
        ) from exc

    return crud.get_warranty_assignment(db, claim.assignment_id)
