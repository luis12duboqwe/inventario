
"""Endpoints protegidos para la administración de listas de precios."""
"""Endpoints para la administración de listas de precios corporativas."""

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
pricing_router = APIRouter(prefix="/pricing", tags=["precios", "inventario"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_price_lists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionalidad no disponible",
        )


def _raise_lookup(exc: LookupError) -> NoReturn:
    detail_map = {
        "price_list_not_found": "La lista de precios solicitada no existe.",
        "price_list_item_not_found": "El elemento de la lista de precios no existe.",
        "store_not_found": "La sucursal indicada no existe.",
        "customer_not_found": "El cliente indicado no existe.",
        "device_not_found": "El dispositivo indicado no existe.",
    }
    detail = detail_map.get(str(exc), "Recurso no encontrado")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc


def _raise_value_error(exc: ValueError) -> NoReturn:
    detail_map = {
        "price_list_conflict": "Ya existe una lista con los mismos criterios.",
        "price_list_item_conflict": "Ya existe un elemento con el mismo dispositivo.",
    }
    numeric_errors = {
        "price_list_item_price_invalid",
        "price_list_item_discount_invalid",
    }
    message = str(exc)
    if message in detail_map:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail_map[message]) from exc
    if message in numeric_errors:
    if message in {"price_list_conflict", "price_list_duplicate"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una lista de precios con los mismos criterios.",
        ) from exc
    if message in {"price_list_item_conflict", "price_list_item_duplicate"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un elemento con los mismos criterios.",
        ) from exc
    if message == "price_list_item_invalid_store":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El dispositivo no pertenece a la sucursal configurada.",
        ) from exc
    if message in {"price_list_item_price_invalid", "price_list_item_discount_invalid"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los valores numéricos proporcionados no son válidos.",
        ) from exc
    raise exc


def _performed_by_id(user) -> int | None:
    return getattr(user, "id", None)


@router.get("", response_model=list[schemas.PriceListResponse])
def list_price_lists_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    is_active: bool | None = Query(default=None),
    include_items: bool = Query(default=False),
    include_inactive: bool = Query(default=False),
    include_global: bool = Query(default=True),
    include_inactive: bool = Query(default=True),
    include_global: bool = Query(default=True),
    include_items: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.PriceListResponse]:
    _ensure_feature_enabled()
    _ = current_user
    return pricing.list_price_lists(
    return pricing.list_price_lists(
    active_filter = is_active
    if active_filter is None and not include_inactive:
        active_filter = True
    price_lists = pricing.list_price_lists(
        db,
        store_id=store_id,
        customer_id=customer_id,
        is_active=active_filter,
        include_items=include_items,
    )


    if not include_global:
        price_lists = [
            price_list
            for price_list in price_lists
            if price_list.store_id is not None or price_list.customer_id is not None
        ]
    return price_lists
    return pricing.list_price_lists(
        db,
        store_id=store_id,
        customer_id=customer_id,
        include_inactive=include_inactive,
        include_global=include_global,
        include_items=include_items,
    )


@router.get(
    "/resolve",
    response_model=schemas.PriceResolution | None,
)
@router.get("/resolve", response_model=schemas.PriceResolution | None)
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
    _ = current_user
    try:
        return pricing.resolve_device_price(
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


@router.get(
    "/{price_list_id}",
    response_model=schemas.PriceListResponse,
)
@router.get("/{price_list_id}", response_model=schemas.PriceListResponse)
def get_price_list_endpoint(
    price_list_id: int = Path(ge=1),
    include_items: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListResponse:
    _ensure_feature_enabled()
    _ = current_user
    try:
        return pricing.get_price_list(db, price_list_id, include_items=include_items)
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
    _: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListResponse:
    _ensure_feature_enabled()
    _ = reason
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
    "/{price_list_id}",
    response_model=schemas.PriceListResponse,
)
@router.put("/{price_list_id}", response_model=schemas.PriceListResponse)
def update_price_list_endpoint(
    payload: schemas.PriceListUpdate,
    price_list_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    _: str = Depends(require_reason),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    _: str = Depends(require_reason),
) -> schemas.PriceListResponse:
    _ensure_feature_enabled()
    _ = reason
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
    "/{price_list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_price_list_endpoint(
    price_list_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    _: str = Depends(require_reason),
@router.delete("/{price_list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price_list_endpoint(
    price_list_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    _: str = Depends(require_reason),
) -> Response:
    _ensure_feature_enabled()
    _ = reason
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
    "/items/{item_id}",
    response_model=schemas.PriceListItemResponse,
)
@router.get("/items/{item_id}", response_model=schemas.PriceListItemResponse)
def get_price_list_item_endpoint(
    item_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListItemResponse:
    _ensure_feature_enabled()
    _ = current_user
    try:
        return pricing.get_price_list_item(db, item_id)
    except LookupError as exc:
        _raise_lookup(exc)


@router.post(
    "/{price_list_id}/items",
    response_model=schemas.PriceListItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_price_list_item_endpoint(
    payload: schemas.PriceListItemCreate,
    price_list_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    _: str = Depends(require_reason),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    _: str = Depends(require_reason),
) -> schemas.PriceListItemResponse:
    _ensure_feature_enabled()
    _ = reason
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
    "/items/{item_id}",
    response_model=schemas.PriceListItemResponse,
)
@router.put("/items/{item_id}", response_model=schemas.PriceListItemResponse)
def update_price_list_item_endpoint(
    payload: schemas.PriceListItemUpdate,
    item_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    _: str = Depends(require_reason),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    _: str = Depends(require_reason),
) -> schemas.PriceListItemResponse:
    _ensure_feature_enabled()
    _ = reason
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
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_price_list_item_endpoint(
    item_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    _: str = Depends(require_reason),
@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_price_list_item_endpoint(
    item_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    _: str = Depends(require_reason),
) -> Response:
    _ensure_feature_enabled()
    _ = reason
    try:
        pricing.delete_price_list_item(
            db,
            item_id,
            performed_by_id=_performed_by_id(current_user),
        )
    except LookupError as exc:
        _raise_lookup(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    "/evaluation",
    response_model=schemas.PriceEvaluationResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
@pricing_router.get(
    "/price-evaluation",
    response_model=schemas.PriceEvaluationResponse,
)
def evaluate_device_price_endpoint(
    device_id: int = Query(ge=1),
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceEvaluationResponse:
    _ensure_feature_enabled()
    _ = current_user
    try:
        resolution = pricing.resolve_device_price(
            db,
            device_id=device_id,
            store_id=store_id,
            customer_id=customer_id,
            reference_date=None,
            default_price=None,
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
        device_id=resolution.device_id,
        price_list_id=resolution.price_list_id,
        scope=resolution.scope,
        price=resolution.price,
        currency=resolution.currency,
    )


# Registro de rutas equivalentes bajo `/pricing`
# Legacy `/price-lists` routes
router.add_api_route(
    "",
    list_price_lists_endpoint,
    methods=["GET"],
    response_model=list[schemas.PriceListResponse],
)
router.add_api_route(
    "",
    create_price_list_endpoint,
    methods=["POST"],
    response_model=schemas.PriceListResponse,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/{price_list_id}",
    get_price_list_endpoint,
    methods=["GET"],
    response_model=schemas.PriceListResponse,
)
router.add_api_route(
    "/{price_list_id}",
    update_price_list_endpoint,
    methods=["PUT"],
    response_model=schemas.PriceListResponse,
)
router.add_api_route(
    "/{price_list_id}",
    delete_price_list_endpoint,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)
router.add_api_route(
    "/{price_list_id}/items",
    create_price_list_item_endpoint,
    methods=["POST"],
    response_model=schemas.PriceListItemResponse,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/items/{item_id}",
    get_price_list_item_endpoint,
    methods=["GET"],
    response_model=schemas.PriceListItemResponse,
)
router.add_api_route(
    "/items/{item_id}",
    update_price_list_item_endpoint,
    methods=["PUT"],
    response_model=schemas.PriceListItemResponse,
)
router.add_api_route(
    "/items/{item_id}",
    delete_price_list_item_endpoint,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)
router.add_api_route(
    "/resolve",
    resolve_device_price_endpoint,
    methods=["GET"],
    response_model=schemas.PriceResolution,
)
router.add_api_route(
    "/evaluate",
    evaluate_device_price_endpoint,
    methods=["GET"],
    response_model=schemas.PriceEvaluationResponse,
)

# Modern `/pricing/*` registration for compatibility
# Rutas espejo bajo `/pricing`
pricing_router.add_api_route(
    "/price-lists",
    list_price_lists_endpoint,
    methods=["GET"],
    response_model=list[schemas.PriceListResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
pricing_router.add_api_route(
    "/price-lists",
    create_price_list_endpoint,
    methods=["POST"],
    response_model=schemas.PriceListResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
pricing_router.add_api_route(
    "/price-lists/{price_list_id}",
    get_price_list_endpoint,
    methods=["GET"],
    response_model=schemas.PriceListResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
pricing_router.add_api_route(
    "/price-lists/{price_list_id}",
    update_price_list_endpoint,
    methods=["PUT"],
    response_model=schemas.PriceListResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
pricing_router.add_api_route(
    "/price-lists/{price_list_id}",
    delete_price_list_endpoint,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
pricing_router.add_api_route(
    "/price-lists/items/{item_id}",
    get_price_list_item_endpoint,
    methods=["GET"],
    response_model=schemas.PriceListItemResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
pricing_router.add_api_route(
    "/price-lists/{price_list_id}/items",
    create_price_list_item_endpoint,
    methods=["POST"],
    response_model=schemas.PriceListItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
pricing_router.add_api_route(
    "/price-lists/items/{item_id}",
    get_price_list_item_endpoint,
    methods=["GET"],
    response_model=schemas.PriceListItemResponse,
)
pricing_router.add_api_route(
    "/price-lists/items/{item_id}",
    get_price_list_item_endpoint,
    methods=["GET"],
    response_model=schemas.PriceListItemResponse,
)
pricing_router.add_api_route(
    "/price-lists/items/{item_id}",
    update_price_list_item_endpoint,
    methods=["PUT"],
    response_model=schemas.PriceListItemResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
pricing_router.add_api_route(
    "/price-lists/items/{item_id}",
    delete_price_list_item_endpoint,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
pricing_router.add_api_route(
    "/price-resolution",
    resolve_device_price_endpoint,
    methods=["GET"],
    response_model=schemas.PriceResolution,
)
pricing_router.add_api_route(
    "/price-evaluation",
    evaluate_device_price_endpoint,
    "/price-lists/resolve",
    resolve_device_price_endpoint,
    methods=["GET"],
    response_model=schemas.PriceResolution | None,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
pricing_router.add_api_route(
    "/price-lists/resolve",
    resolve_device_price_endpoint,
    methods=["GET"],
    response_model=schemas.PriceEvaluationResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
    response_model=schemas.PriceResolution | None,
)

__all__ = ["router", "pricing_router"]
