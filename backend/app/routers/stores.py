"""Rutas relacionadas con sucursales y dispositivos."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from datetime import date

from backend.schemas.common import Page, PageParams

from .. import crud, schemas
from ..config import settings
from ..core.roles import ADMIN, GESTION_ROLES
from ..database import get_db
from ..models import CommercialState
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/stores", tags=["stores"])


@router.post(
    "",
    response_model=schemas.StoreResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def create_store(
    payload: schemas.StoreCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        store = crud.create_store(
            db, payload, performed_by_id=current_user.id if current_user else None)
    except ValueError as exc:
        if str(exc) == "store_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "store_already_exists",
                    "message": "Ya existe una sucursal con ese nombre.",
                },
            ) from exc
        if str(exc) == "store_code_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "store_code_already_exists",
                    "message": "Ya existe una sucursal con ese código.",
                },
            ) from exc
        raise
    return store


@router.get("", response_model=Page[schemas.StoreResponse], dependencies=[Depends(require_roles(*GESTION_ROLES))])
def list_stores(
    pagination: PageParams = Depends(),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> Page[schemas.StoreResponse]:
    page_offset = pagination.offset if (
        pagination.page > 1 and offset == 0) else offset
    page_size = min(pagination.size, limit)
    total = crud.count_stores(db)
    stores = crud.list_stores(db, limit=page_size, offset=page_offset)
    return Page.from_items(stores, page=pagination.page, size=page_size, total=total)


@router.get("/{store_id}", response_model=schemas.StoreResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def retrieve_store(
    store_id: int = Path(..., ge=1,
                         description="Identificador de la sucursal"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.get_store(db, store_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "store_not_found",
                    "message": "La sucursal solicitada no existe."},
        ) from exc


@router.get(
    "/{store_id}/devices/{device_id}",
    response_model=schemas.DeviceResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
def retrieve_device(
    store_id: int = Path(..., ge=1, description="Identificador de la sucursal"),
    device_id: int = Path(..., ge=1, description="Identificador del dispositivo"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    if not settings.enable_catalog_pro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ruta no disponible"
        )

    try:
        device = crud.get_device(db, store_id, device_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "device_not_found", "message": "Dispositivo no encontrado."},
        ) from exc

    return schemas.DeviceResponse.model_validate(device, from_attributes=True)


@router.put("/{store_id}", response_model=schemas.StoreResponse, dependencies=[Depends(require_roles(*GESTION_ROLES))])
def update_store(
    payload: schemas.StoreUpdate,
    store_id: int = Path(..., ge=1,
                         description="Identificador de la sucursal"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        return crud.update_store(
            db,
            store_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "store_not_found",
                    "message": "La sucursal solicitada no existe."},
        ) from exc
    except ValueError as exc:
        if str(exc) == "store_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "store_already_exists",
                    "message": "Ya existe una sucursal con ese nombre.",
                },
            ) from exc
        if str(exc) == "store_code_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "store_code_already_exists",
                    "message": "Ya existe una sucursal con ese código.",
                },
            ) from exc
        raise


@router.delete(
    "/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def delete_store(
    store_id: int = Path(..., ge=1, description="Identificador de la sucursal"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
    reason: str = Depends(require_reason),
) -> Response:
    try:
        crud.soft_delete_store(
            db,
            store_id,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "store_not_found", "message": "La sucursal solicitada no existe."},
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{store_id}/devices",
    response_model=schemas.DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def create_device(
    payload: schemas.DeviceCreate,
    store_id: int = Path(..., ge=1,
                         description="Identificador de la sucursal"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        device = crud.create_device(
            db,
            store_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "store_not_found",
                    "message": "La sucursal solicitada no existe."},
        ) from exc
    except ValueError as exc:
        if str(exc) == "device_invalid_quantity":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "device_invalid_quantity",
                    "message": "La cantidad debe ser mayor que cero.",
                },
            ) from exc
        if str(exc) == "device_invalid_cost":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "device_invalid_cost",
                    "message": "El costo_unitario debe ser mayor que cero.",
                },
            ) from exc
        if str(exc) == "device_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "device_already_exists",
                    "message": "Ya existe un dispositivo con ese SKU en la sucursal.",
                },
            ) from exc
        if str(exc) == "device_identifier_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "device_identifier_conflict",
                    "message": "El IMEI o número de serie ya fue registrado por otra sucursal.",
                },
            ) from exc
        raise
    return device


@router.get("/{store_id}/devices", response_model=Page[schemas.DeviceResponse], dependencies=[Depends(require_roles(ADMIN))])
def list_devices(
    store_id: int = Path(..., ge=1,
                         description="Identificador de la sucursal"),
    search: str | None = Query(default=None, min_length=1, max_length=120),
    estado: str | None = Query(
        default=None, description="Filtra por estado comercial"),
    categoria: str | None = Query(default=None, max_length=80),
    condicion: str | None = Query(default=None, max_length=60),
    estado_inventario: str | None = Query(default=None, max_length=40),
    ubicacion: str | None = Query(default=None, max_length=120),
    proveedor: str | None = Query(default=None, max_length=120),
    warehouse_id: int | None = Query(default=None, ge=1),
    fecha_ingreso_desde: date | None = Query(default=None),
    fecha_ingreso_hasta: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> Page[schemas.DeviceResponse]:
    if not settings.enable_catalog_pro:
        # Compatibilidad retroactiva: cuando el catálogo pro está desactivado, ocultar la lista detallada
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ruta no disponible")

    estado_enum: CommercialState | None = None
    if estado:
        normalized = estado.strip()
        try:
            estado_enum = CommercialState(normalized)
        except ValueError:
            try:
                estado_enum = CommercialState(normalized.lower())
            except ValueError:
                try:
                    estado_enum = CommercialState(normalized.upper())
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "code": "invalid_estado_comercial",
                            "message": "Estado comercial inválido. Usa nuevo, A, B o C.",
                        },
                    ) from exc
    try:
        page_offset = pagination.offset if (
            pagination.page > 1 and offset == 0) else offset
        page_size = min(pagination.size, limit)
        total = crud.count_store_devices(
            db,
            store_id,
            search=search,
            estado=estado_enum,
            categoria=categoria,
            condicion=condicion,
            estado_inventario=estado_inventario,
            ubicacion=ubicacion,
            proveedor=proveedor,
            warehouse_id=warehouse_id,
            fecha_ingreso_desde=fecha_ingreso_desde,
            fecha_ingreso_hasta=fecha_ingreso_hasta,
        )
        devices = crud.list_devices(
            db,
            store_id,
            search=search,
            estado=estado_enum,
            categoria=categoria,
            condicion=condicion,
            estado_inventario=estado_inventario,
            ubicacion=ubicacion,
            proveedor=proveedor,
            warehouse_id=warehouse_id,
            fecha_ingreso_desde=fecha_ingreso_desde,
            fecha_ingreso_hasta=fecha_ingreso_hasta,
            limit=page_size,
            offset=page_offset,
        )
        return Page.from_items(devices, page=pagination.page, size=page_size, total=total)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "store_not_found",
                    "message": "La sucursal solicitada no existe."},
        ) from exc


@router.get(
    "/{store_id}/memberships",
    response_model=Page[schemas.StoreMembershipResponse],
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def list_store_memberships(
    store_id: int = Path(..., ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> Page[schemas.StoreMembershipResponse]:
    try:
        crud.get_store(db, store_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="La sucursal solicitada no existe.") from exc
    page_offset = pagination.offset if (
        pagination.page > 1 and offset == 0) else offset
    page_size = min(pagination.size, limit)
    total = crud.count_store_memberships(db, store_id)
    memberships = crud.list_store_memberships(
        db,
        store_id,
        limit=page_size,
        offset=page_offset,
    )
    return Page.from_items(memberships, page=pagination.page, size=page_size, total=total)


@router.put(
    "/{store_id}/memberships/{user_id}",
    response_model=schemas.StoreMembershipResponse,
    dependencies=[Depends(require_roles(*GESTION_ROLES))],
)
def upsert_membership(
    payload: schemas.StoreMembershipUpdate,
    store_id: int = Path(..., ge=1),
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    if payload.store_id != store_id or payload.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los identificadores del cuerpo deben coincidir con la ruta.",
        )
    try:
        crud.get_store(db, store_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="La sucursal solicitada no existe.") from exc
    membership = crud.upsert_store_membership(
        db,
        user_id=user_id,
        store_id=store_id,
        can_create_transfer=payload.can_create_transfer,
        can_receive_transfer=payload.can_receive_transfer,
    )
    return membership
