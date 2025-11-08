"""Endpoints protegidos para la administración de listas de precios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import pricing

router = APIRouter(prefix="/pricing", tags=["precios", "inventario"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_price_lists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionalidad no disponible",
        )


@router.get(
    "/price-lists",
    response_model=list[schemas.PriceListResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def list_price_lists_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    include_inactive: bool = Query(default=False),
    include_global: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.PriceListResponse]:
    _ensure_feature_enabled()
    price_lists = crud.list_price_lists(
        db,
        store_id=store_id,
        customer_id=customer_id,
        include_inactive=include_inactive,
        include_global=include_global,
    )
    return [
        schemas.PriceListResponse.model_validate(price_list, from_attributes=True)
        for price_list in price_lists
    ]


@router.post(
    "/price-lists",
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
        price_list = crud.create_price_list(
            db,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except ValueError as exc:
        if str(exc) == "price_list_duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una lista con ese nombre en el mismo alcance.",
            ) from exc
        raise
    return schemas.PriceListResponse.model_validate(price_list, from_attributes=True)


@router.get(
    "/price-lists/{price_list_id}",
    response_model=schemas.PriceListResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def get_price_list_endpoint(
    price_list_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListResponse:
    _ensure_feature_enabled()
    try:
        price_list = crud.get_price_list(db, price_list_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada",
        ) from exc
    return schemas.PriceListResponse.model_validate(price_list, from_attributes=True)


@router.put(
    "/price-lists/{price_list_id}",
    response_model=schemas.PriceListResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def update_price_list_endpoint(
    payload: schemas.PriceListUpdate,
    price_list_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListResponse:
    _ensure_feature_enabled()
    try:
        price_list = crud.update_price_list(
            db,
            price_list_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada",
        ) from exc
    except ValueError as exc:
        if str(exc) == "price_list_duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una lista con ese nombre en el mismo alcance.",
            ) from exc
        raise
    return schemas.PriceListResponse.model_validate(price_list, from_attributes=True)


@router.delete(
    "/price-lists/{price_list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_price_list_endpoint(
    price_list_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> None:
    _ensure_feature_enabled()
    try:
        crud.delete_price_list(
            db,
            price_list_id,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista de precios no encontrada",
        ) from exc


@router.post(
    "/price-lists/{price_list_id}/items",
    response_model=schemas.PriceListItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def create_price_list_item_endpoint(
    payload: schemas.PriceListItemCreate,
    price_list_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListItemResponse:
    _ensure_feature_enabled()
    try:
        item = crud.create_price_list_item(
            db,
            price_list_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso no encontrado",
        ) from exc
    except ValueError as exc:
        message = str(exc)
        if message == "price_list_item_duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El dispositivo ya tiene precio asignado en esta lista.",
            ) from exc
        if message == "price_list_item_invalid_store":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El dispositivo pertenece a otra sucursal.",
            ) from exc
        raise
    return schemas.PriceListItemResponse.model_validate(item, from_attributes=True)


@router.put(
    "/price-lists/{price_list_id}/items/{item_id}",
    response_model=schemas.PriceListItemResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def update_price_list_item_endpoint(
    payload: schemas.PriceListItemUpdate,
    price_list_id: int = Path(..., ge=1),
    item_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceListItemResponse:
    _ensure_feature_enabled()
    try:
        item = crud.update_price_list_item(
            db,
            price_list_id,
            item_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Elemento no encontrado",
        ) from exc
    return schemas.PriceListItemResponse.model_validate(item, from_attributes=True)


@router.delete(
    "/price-lists/{price_list_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_price_list_item_endpoint(
    price_list_id: int = Path(..., ge=1),
    item_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> None:
    _ensure_feature_enabled()
    try:
        crud.delete_price_list_item(
            db,
            price_list_id,
            item_id,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Elemento no encontrado",
        ) from exc


@router.get(
    "/price-evaluation",
    response_model=schemas.PriceEvaluationResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def evaluate_price_endpoint(
    device_id: int = Query(..., ge=1),
    store_id: int | None = Query(default=None, ge=1),
    customer_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.PriceEvaluationResponse:
    _ensure_feature_enabled()
    payload = schemas.PriceEvaluationRequest(
        device_id=device_id, store_id=store_id, customer_id=customer_id
    )
    device = db.get(models.Device, payload.device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )
    resolved = pricing.resolve_price_for_device(
        db,
        device,
        store_id=payload.store_id,
        customer_id=payload.customer_id,
    )
    if resolved is None:
        return schemas.PriceEvaluationResponse(
            device_id=device.id,
        )
    price_list, item = resolved
    return schemas.PriceEvaluationResponse(
        device_id=device.id,
        price_list_id=price_list.id,
        scope=price_list.scope,
        price=float(item.price),
        currency=item.currency,
    )
