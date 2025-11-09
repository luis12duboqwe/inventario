"""Endpoints de administración y resolución de listas de precios."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from .. import schemas
from ..config import settings
from ..core.roles import GESTION_ROLES, MOVEMENT_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import pricing

router = APIRouter(prefix="/price-lists", tags=["listas de precios"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_price_lists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionalidad no disponible",
        )


def _raise_lookup(exc: LookupError) -> NoReturn:
    message = str(exc)
    detail = "Recurso no encontrado"
    if message == "price_list_not_found":
        detail = "La lista de precios solicitada no existe."
    elif message == "price_list_item_not_found":
        detail = "El elemento de la lista de precios no existe."
    elif message == "store_not_found":
        detail = "La sucursal indicada no existe."
    elif message == "customer_not_found":
        detail = "El cliente indicado no existe."
    elif message == "device_not_found":
        detail = "El dispositivo indicado no existe."
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc


def _raise_value_error(exc: ValueError) -> NoReturn:
    message = str(exc)
    if message in {"price_list_conflict", "price_list_item_conflict"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un registro con los mismos criterios.",
        ) from exc
    if message in {"price_list_item_price_invalid", "price_list_item_discount_invalid"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los valores numéricos proporcionados no son válidos.",
        ) from exc
    raise exc


@router.get(
    "",
    response_model=list[schemas.PriceListResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def list_price_lists_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    is_active: bool | None = Query(default=None),
    include_items: bool = Query(default=False),
    include_inactive: bool = Query(default=False),
    include_global: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.PriceListResponse]:
    _ensure_feature_enabled()
    price_lists = pricing.list_price_lists(
        db,
        store_id=store_id,
        customer_id=customer_id,
        is_active=is_active,
        include_items=include_items,
    )
    if not include_inactive:
        price_lists = [pl for pl in price_lists if pl.is_active]
    if not include_global:
        price_lists = [
            pl
            for pl in price_lists
            if pl.store_id is not None or pl.customer_id is not None
        ]
    return price_lists


@router.get(
    "/resolve",
    response_model=schemas.PriceResolution | None,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def resolve_device_price_endpoint(
    device_id: int = Query(ge=1),
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    reference_date: date | None = Query(default=None),
    default_price: Decimal | None = Query(default=None, gt=Decimal("0")),
    default_currency: str = Query(default="MXN", min_length=3, max_length=8),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.PriceResolution | None:
    _ensure_feature_enabled()
    try:
        resolution = pricing.resolve_device_price(
            db,
            device_id=device_id,
            store_id=store_id,
            customer_id=customer_id,
            reference_date=reference_date,
            default_price=default_price,
            default_currency=default_currency,
        )
    except LookupError as exc:
        _raise_lookup(exc)
    return resolution


@router.get(
    "/{price_list_id}",
    response_model=schemas.PriceListResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_price_list_endpoint(
    price_list_id: int = Path(ge=1),
    include_items: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListResponse:
    _ensure_feature_enabled()
    try:
        return pricing.get_price_list(
            db,
            price_list_id,
            include_items=include_items,
        )
    except LookupError as exc:
        _raise_lookup(exc)


@router.post(
    "",
    response_model=schemas.PriceListResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def create_price_list_endpoint(
    payload: schemas.PriceListCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListResponse:
    _ensure_feature_enabled()
    try:
        return pricing.create_price_list(
            db,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except ValueError as exc:
        _raise_value_error(exc)


@router.put(
    "/{price_list_id}",
    response_model=schemas.PriceListResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def update_price_list_endpoint(
    payload: schemas.PriceListUpdate,
    price_list_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListResponse:
    _ensure_feature_enabled()
    try:
        return pricing.update_price_list(
            db,
            price_list_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup(exc)
    except ValueError as exc:
        _raise_value_error(exc)


@router.delete(
    "/{price_list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_price_list_endpoint(
    price_list_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> Response:
    _ensure_feature_enabled()
    try:
        pricing.delete_price_list(
            db,
            price_list_id,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/items/{item_id}",
    response_model=schemas.PriceListItemResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_price_list_item_endpoint(
    item_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListItemResponse:
    _ensure_feature_enabled()
    try:
        return pricing.get_price_list_item(db, item_id)
    except LookupError as exc:
        _raise_lookup(exc)


@router.post(
    "/{price_list_id}/items",
    response_model=schemas.PriceListItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def create_price_list_item_endpoint(
    payload: schemas.PriceListItemCreate,
    price_list_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListItemResponse:
    _ensure_feature_enabled()
    try:
        return pricing.create_price_list_item(
            db,
            price_list_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup(exc)
    except ValueError as exc:
        _raise_value_error(exc)


@router.put(
    "/items/{item_id}",
    response_model=schemas.PriceListItemResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def update_price_list_item_endpoint(
    payload: schemas.PriceListItemUpdate,
    item_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListItemResponse:
    _ensure_feature_enabled()
    try:
        return pricing.update_price_list_item(
            db,
            item_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup(exc)
    except ValueError as exc:
        _raise_value_error(exc)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_price_list_item_endpoint(
    item_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> Response:
    _ensure_feature_enabled()
    try:
        pricing.delete_price_list_item(
            db,
            item_id,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
