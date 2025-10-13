"""Endpoints para la gestión de órdenes de compra."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/purchases", tags=["compras"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionalidad no disponible",
        )


@router.get("/", response_model=list[schemas.PurchaseOrderResponse])
def list_purchase_orders_endpoint(
    limit: int = 50,
    store_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    orders = crud.list_purchase_orders(db, store_id=store_id, limit=limit)
    return orders


@router.post("/", response_model=schemas.PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_order_endpoint(
    payload: schemas.PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.create_purchase_order(db, payload, created_by_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado") from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "purchase_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes incluir artículos en la orden.",
            ) from exc
        if detail == "purchase_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida en la orden.",
            ) from exc
        raise


@router.post("/{order_id}/receive", response_model=schemas.PurchaseOrderResponse)
def receive_purchase_order_endpoint(
    payload: schemas.PurchaseReceiveRequest,
    order_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.receive_purchase_order(
            db,
            order_id,
            payload,
            received_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "purchase_not_receivable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden no puede recibir más artículos.",
            ) from exc
        if detail == "purchase_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar artículos a recibir.",
            ) from exc
        if detail == "purchase_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cantidad a recibir inválida.",
            ) from exc
        raise


@router.post("/{order_id}/cancel", response_model=schemas.PurchaseOrderResponse)
def cancel_purchase_order_endpoint(
    order_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.cancel_purchase_order(
            db,
            order_id,
            cancelled_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada",
        ) from exc
    except ValueError as exc:
        if str(exc) == "purchase_not_cancellable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La orden ya fue cerrada.",
            ) from exc
        raise


@router.post("/{order_id}/returns", response_model=schemas.PurchaseReturnResponse)
def register_purchase_return_endpoint(
    payload: schemas.PurchaseReturnCreate,
    order_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.register_purchase_return(
            db,
            order_id,
            payload,
            processed_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden o artículo no encontrado",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "purchase_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida.",
            ) from exc
        if detail == "purchase_return_exceeds_received":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes devolver más de lo recibido.",
            ) from exc
        if detail == "purchase_return_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para devolver.",
            ) from exc
        raise
