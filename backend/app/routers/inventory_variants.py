"""Endpoints para administrar variantes de productos y combos corporativos."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/inventory", tags=["inventario", "variantes"])


def _ensure_variants_enabled() -> None:
    if not settings.enable_variants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La funcionalidad de variantes no está disponible.",
        )


def _ensure_bundles_enabled() -> None:
    if not settings.enable_bundles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La funcionalidad de combos no está disponible.",
        )


def _raise_lookup_error(exc: LookupError) -> None:
    message = str(exc)
    detail = "Recurso no encontrado"
    if message == "product_variant_not_found":
        detail = "La variante solicitada no existe."
    elif message == "product_bundle_not_found":
        detail = "El combo solicitado no existe."
    elif message == "device_not_found":
        detail = "El dispositivo indicado no existe."
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc


def _raise_value_error(exc: ValueError) -> None:
    message = str(exc)
    if message == "product_variant_conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una variante con el mismo SKU para este dispositivo.",
        ) from exc
    if message == "product_bundle_conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un combo con el mismo SKU en la sucursal.",
        ) from exc
    if message == "bundle_items_required":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Un combo debe contener al menos un artículo.",
        ) from exc
    if message == "bundle_device_store_mismatch":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Todos los dispositivos del combo deben pertenecer a la misma sucursal.",
        ) from exc
    if message == "bundle_variant_device_mismatch":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La variante seleccionada no corresponde al dispositivo indicado.",
        ) from exc
    raise exc


@router.get(
    "/variants",
    response_model=list[schemas.ProductVariantResponse],
)
def list_product_variants_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    device_id: int | None = Query(default=None, ge=1),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.ProductVariantResponse]:
    _ensure_variants_enabled()
    variants = crud.list_product_variants(
        db,
        store_id=store_id,
        device_id=device_id,
        include_inactive=include_inactive,
    )
    return [
        schemas.ProductVariantResponse.model_validate(variant, from_attributes=True)
        for variant in variants
    ]


@router.post(
    "/devices/{device_id}/variants",
    response_model=schemas.ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_variant_endpoint(
    payload: schemas.ProductVariantCreate,
    device_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.ProductVariantResponse:
    _ensure_variants_enabled()
    try:
        variant = crud.create_product_variant(
            db,
            device_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup_error(exc)
    except ValueError as exc:  # pragma: no cover - rutas manejan detalle
        _raise_value_error(exc)
    return schemas.ProductVariantResponse.model_validate(variant, from_attributes=True)


@router.patch(
    "/variants/{variant_id}",
    response_model=schemas.ProductVariantResponse,
)
def update_product_variant_endpoint(
    payload: schemas.ProductVariantUpdate,
    variant_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.ProductVariantResponse:
    _ensure_variants_enabled()
    try:
        variant = crud.update_product_variant(
            db,
            variant_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup_error(exc)
    except ValueError as exc:
        _raise_value_error(exc)
    return schemas.ProductVariantResponse.model_validate(variant, from_attributes=True)


@router.delete(
    "/variants/{variant_id}",
    response_model=schemas.ProductVariantResponse,
)
def archive_product_variant_endpoint(
    variant_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.ProductVariantResponse:
    _ensure_variants_enabled()
    try:
        variant = crud.archive_product_variant(
            db,
            variant_id,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup_error(exc)
    return schemas.ProductVariantResponse.model_validate(variant, from_attributes=True)


@router.get(
    "/bundles",
    response_model=list[schemas.ProductBundleResponse],
)
def list_product_bundles_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> list[schemas.ProductBundleResponse]:
    _ensure_bundles_enabled()
    bundles = crud.list_product_bundles(
        db,
        store_id=store_id,
        include_inactive=include_inactive,
    )
    return [
        schemas.ProductBundleResponse.model_validate(bundle, from_attributes=True)
        for bundle in bundles
    ]


@router.post(
    "/bundles",
    response_model=schemas.ProductBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_bundle_endpoint(
    payload: schemas.ProductBundleCreate,
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.ProductBundleResponse:
    _ensure_bundles_enabled()
    try:
        bundle = crud.create_product_bundle(
            db,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup_error(exc)
    except ValueError as exc:
        _raise_value_error(exc)
    return schemas.ProductBundleResponse.model_validate(bundle, from_attributes=True)


@router.patch(
    "/bundles/{bundle_id}",
    response_model=schemas.ProductBundleResponse,
)
def update_product_bundle_endpoint(
    payload: schemas.ProductBundleUpdate,
    bundle_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.ProductBundleResponse:
    _ensure_bundles_enabled()
    try:
        bundle = crud.update_product_bundle(
            db,
            bundle_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup_error(exc)
    except ValueError as exc:
        _raise_value_error(exc)
    return schemas.ProductBundleResponse.model_validate(bundle, from_attributes=True)


@router.delete(
    "/bundles/{bundle_id}",
    response_model=schemas.ProductBundleResponse,
)
def archive_product_bundle_endpoint(
    bundle_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.ProductBundleResponse:
    _ensure_bundles_enabled()
    try:
        bundle = crud.archive_product_bundle(
            db,
            bundle_id,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        _raise_lookup_error(exc)
    return schemas.ProductBundleResponse.model_validate(bundle, from_attributes=True)
