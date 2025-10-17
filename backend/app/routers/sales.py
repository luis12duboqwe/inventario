"""Endpoints para ventas y devoluciones."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/sales", tags=["ventas"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")


@router.get("/", response_model=list[schemas.SaleResponse])
def list_sales_endpoint(
    limit: int = 50,
    store_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    return crud.list_sales(db, store_id=store_id, limit=limit)


@router.post("/", response_model=schemas.SaleResponse, status_code=status.HTTP_201_CREATED)
def create_sale_endpoint(
    payload: schemas.SaleCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.create_sale(
            db,
            payload,
            performed_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso no encontrado",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "sale_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes agregar artículos a la venta.",
            ) from exc
        if detail == "sale_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida en la venta.",
            ) from exc
        if detail == "sale_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para la venta.",
            ) from exc
        if detail == "sale_device_already_sold":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El dispositivo ya fue vendido y no está disponible.",
            ) from exc
        if detail == "sale_requires_single_unit":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Los dispositivos con IMEI o serie se venden por unidad.",
            ) from exc
        raise


@router.post("/returns", response_model=list[schemas.SaleReturnResponse])
def register_sale_return_endpoint(
    payload: schemas.SaleReturnCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.register_sale_return(
            db,
            payload,
            processed_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta o artículo no encontrado",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "sale_return_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar artículos a devolver.",
            ) from exc
        if detail == "sale_return_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cantidad de devolución inválida.",
            ) from exc
        raise


@router.put("/{sale_id}", response_model=schemas.SaleResponse)
def update_sale_endpoint(
    payload: schemas.SaleUpdate,
    sale_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.update_sale(
            db,
            sale_id,
            payload,
            performed_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        ) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "sale_items_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes agregar artículos a la venta.",
            ) from exc
        if detail == "sale_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cantidad inválida en la venta.",
            ) from exc
        if detail == "sale_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventario insuficiente para la venta.",
            ) from exc
        if detail == "sale_device_already_sold":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El dispositivo ya fue vendido y no está disponible.",
            ) from exc
        if detail == "sale_requires_single_unit":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Los dispositivos con IMEI o serie se venden por unidad.",
            ) from exc
        if detail == "sale_has_returns":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes editar una venta con devoluciones registradas.",
            ) from exc
        if detail == "sale_already_cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La venta ya se encuentra anulada.",
            ) from exc
        raise


@router.post("/{sale_id}/cancel", response_model=schemas.SaleResponse)
def cancel_sale_endpoint(
    sale_id: int,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.cancel_sale(
            db,
            sale_id,
            performed_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venta no encontrada",
        ) from exc
    except ValueError as exc:
        if str(exc) == "sale_already_cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La venta ya se encuentra anulada.",
            ) from exc
        raise
