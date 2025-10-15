"""Endpoints transversales del módulo Operaciones."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/operations", tags=["operaciones"])


def _user_name(user: models.User | None) -> str | None:
    if user is None:
        return None
    return user.full_name or user.username


def _serialize_template(template: models.RecurringOrder) -> schemas.RecurringOrderResponse:
    return schemas.RecurringOrderResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        order_type=template.order_type,
        store_id=template.store_id,
        store_name=template.store.name if template.store else None,
        payload=template.payload,
        created_by_id=template.created_by_id,
        created_by_name=_user_name(template.created_by),
        last_used_by_id=template.last_used_by_id,
        last_used_by_name=_user_name(template.last_used_by),
        created_at=template.created_at,
        updated_at=template.updated_at,
        last_used_at=template.last_used_at,
    )


@router.get("/recurring-orders", response_model=list[schemas.RecurringOrderResponse])
def list_recurring_orders_endpoint(
    order_type: models.RecurringOrderType | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.RecurringOrderResponse]:
    templates = crud.list_recurring_orders(db, order_type=order_type)
    return [_serialize_template(template) for template in templates]


@router.post(
    "/recurring-orders",
    response_model=schemas.RecurringOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recurring_order_endpoint(
    payload: schemas.RecurringOrderCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.RecurringOrderResponse:
    try:
        template = crud.create_recurring_order(
            db,
            payload,
            created_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso relacionado no encontrado",
        ) from exc
    return _serialize_template(template)


@router.post(
    "/recurring-orders/{template_id}/execute",
    response_model=schemas.RecurringOrderExecutionResult,
)
def execute_recurring_order_endpoint(
    template_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.RecurringOrderExecutionResult:
    try:
        return crud.execute_recurring_order(
            db,
            template_id,
            performed_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada",
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No cuentas con permisos suficientes para ejecutar la plantilla.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("/history", response_model=schemas.OperationsHistoryResponse)
def get_operations_history_endpoint(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_id: int | None = Query(default=None),
    technician_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.OperationsHistoryResponse:
    start_dt = (
        datetime.combine(start_date, datetime.min.time()) if start_date is not None else None
    )
    end_dt = (
        datetime.combine(end_date, datetime.max.time()) if end_date is not None else None
    )
    return crud.list_operations_history(
        db,
        start=start_dt,
        end=end_dt,
        store_id=store_id,
        technician_id=technician_id,
    )
