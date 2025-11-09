"""Endpoints protegidos para la administración de listas de precios."""

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

router = APIRouter(tags=["precios", "inventario"])


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


def _performed_by_id(user) -> int | None:
    return getattr(user, "id", None)


@router.get(
    "/pricing/price-lists",
    response_model=list[schemas.PriceListResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def list_price_lists_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    include_inactive: bool = Query(default=False),
    include_global: bool = Query(default=True),
    is_active: bool | None = Query(default=None),
    include_items: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.PriceListResponse]:
    _ensure_feature_enabled()
    price_lists = pricing.list_price_lists(
        db,
        store_id=store_id,
        customer_id=customer_id,
        include_inactive=include_inactive or (is_active is False),
        include_global=include_global,
    )
    if is_active is not None:
        price_lists = [pl for pl in price_lists if pl.is_active is is_active]
    if not include_items:
        return [pl.model_copy(update={"items": []}) for pl in price_lists]
    return price_lists


@router.get(
    "/pricing/price-lists/{price_list_id}",
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
        return pricing.get_price_list(db, price_list_id, include_items=include_items)
    except LookupError as exc:
        _raise_lookup(exc)


@router.post(
    "/pricing/price-lists",
    response_model=schemas.PriceListResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def create_price_list_endpoint(
    payload: schemas.PriceListCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListResponse:
    _ensure_feature_enabled()
    try:
        return pricing.create_price_list(
            db,
            payload,
            performed_by_id=_performed_by_id(current_user),
            include_items=True,
        )
    except LookupError as exc:
        _raise_lookup(exc)
    except ValueError as exc:
        _raise_value_error(exc)


@router.put(
    "/pricing/price-lists/{price_list_id}",
    response_model=schemas.PriceListResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def update_price_list_endpoint(
    payload: schemas.PriceListUpdate,
    price_list_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListResponse:
    _ensure_feature_enabled()
    try:
        return pricing.update_price_list(
            db,
            price_list_id,
            payload,
            performed_by_id=_performed_by_id(current_user),
            include_items=True,
        )
    except LookupError as exc:
        _raise_lookup(exc)
    except ValueError as exc:
        _raise_value_error(exc)


@router.delete(
    "/pricing/price-lists/{price_list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_price_list_endpoint(
    price_list_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> Response:
    _ensure_feature_enabled()
    try:
        pricing.delete_price_list(
            db,
            price_list_id,
            performed_by_id=_performed_by_id(current_user),
        )
    except LookupError as exc:
        _raise_lookup(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/pricing/price-lists/items/{item_id}",
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
    "/pricing/price-lists/{price_list_id}/items",
    response_model=schemas.PriceListItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def create_price_list_item_endpoint(
    payload: schemas.PriceListItemCreate,
    price_list_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListItemResponse:
    _ensure_feature_enabled()
    try:
        return pricing.create_price_list_item(
            db,
            price_list_id,
            payload,
            performed_by_id=_performed_by_id(current_user),
        )
    except LookupError as exc:
        _raise_lookup(exc)
    except ValueError as exc:
        _raise_value_error(exc)


@router.put(
    "/pricing/price-lists/items/{item_id}",
    response_model=schemas.PriceListItemResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def update_price_list_item_endpoint(
    payload: schemas.PriceListItemUpdate,
    item_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListItemResponse:
    _ensure_feature_enabled()
    try:
        return pricing.update_price_list_item(
            db,
            item_id,
            payload,
            performed_by_id=_performed_by_id(current_user),
        )
    except LookupError as exc:
        _raise_lookup(exc)
    except ValueError as exc:
        _raise_value_error(exc)


@router.delete(
    "/pricing/price-lists/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_price_list_item_endpoint(
    item_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> Response:
    _ensure_feature_enabled()
    try:
        pricing.delete_price_list_item(
            db,
            item_id,
            performed_by_id=_performed_by_id(current_user),
        )
    except LookupError as exc:
        _raise_lookup(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/pricing/price-lists/resolve",
    response_model=schemas.PriceResolution,
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
) -> schemas.PriceResolution:
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

    if resolution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró un precio aplicable.",
        )
    return resolution


@router.get(
    "/pricing/price-evaluation",
    response_model=schemas.PriceEvaluationResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def evaluate_device_price_endpoint(
    device_id: int = Query(ge=1),
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    reference_date: date | None = Query(default=None),
    default_price: Decimal | None = Query(default=None, gt=Decimal("0")),
    default_currency: str = Query(default="MXN", min_length=3, max_length=8),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceEvaluationResponse:
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

    if resolution is None:
        return schemas.PriceEvaluationResponse(
            device_id=device_id,
            price_list_id=None,
            scope=None,
            price=None,
            currency=None,
        )

    return schemas.PriceEvaluationResponse(
        device_id=device_id,
        price_list_id=resolution.price_list_id,
        scope=resolution.scope,
        price=float(resolution.final_price),
        currency=resolution.currency,
    )


# Rutas legacy bajo `/price-lists` para compatibilidad retroactiva
router.add_api_route(
    "/price-lists",
    list_price_lists_endpoint,
    methods=["GET"],
    response_model=list[schemas.PriceListResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
router.add_api_route(
    "/price-lists",
    create_price_list_endpoint,
    methods=["POST"],
    response_model=schemas.PriceListResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
router.add_api_route(
    "/price-lists/{price_list_id}",
    get_price_list_endpoint,
    methods=["GET"],
    response_model=schemas.PriceListResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
router.add_api_route(
    "/price-lists/{price_list_id}",
    update_price_list_endpoint,
    methods=["PUT"],
    response_model=schemas.PriceListResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
router.add_api_route(
    "/price-lists/{price_list_id}",
    delete_price_list_endpoint,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
router.add_api_route(
    "/price-lists/{price_list_id}/items",
    create_price_list_item_endpoint,
    methods=["POST"],
    response_model=schemas.PriceListItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
router.add_api_route(
    "/price-lists/items/{item_id}",
    get_price_list_item_endpoint,
    methods=["GET"],
    response_model=schemas.PriceListItemResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
router.add_api_route(
    "/price-lists/items/{item_id}",
    update_price_list_item_endpoint,
    methods=["PUT"],
    response_model=schemas.PriceListItemResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
router.add_api_route(
    "/price-lists/items/{item_id}",
    delete_price_list_item_endpoint,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
router.add_api_route(
    "/price-lists/resolve",
    resolve_device_price_endpoint,
    methods=["GET"],
    response_model=schemas.PriceResolution,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
router.add_api_route(
    "/price-evaluation",
    evaluate_device_price_endpoint,
    methods=["GET"],
    response_model=schemas.PriceEvaluationResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)

__all__ = ["router"]
