"""Endpoints simplificados de sucursales con conversión al núcleo."""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from backend.app.core.roles import GESTION_ROLES, REPORTE_ROLES
from backend.app.routers import stores as core_stores
from backend.app.security import get_current_user, require_roles
from backend.db import get_db
from backend.schemas import store as schemas
from backend.schemas.common import Page, PageParams

from ._core_bridge import mount_core_router

router = APIRouter(tags=["stores"], dependencies=[Depends(get_current_user)])


@router.get(
    "/stores",
    response_model=Page[schemas.StoreRead],
    dependencies=[Depends(get_current_user)],
)
def list_stores(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_roles(*GESTION_ROLES)),
) -> Page[schemas.StoreRead]:
    """Devuelve las sucursales del núcleo en un formato paginado."""

    core_page = core_stores.list_stores(
        pagination=pagination,
        limit=limit,
        offset=offset,
        db=db,
        current_user=current_user,
    )
    items = [schemas.StoreRead.from_core(item) for item in core_page.items]
    return Page.from_items(items, page=core_page.page, size=core_page.size, total=core_page.total)


@router.post(
    "/stores",
    response_model=schemas.StoreRead,
    dependencies=[Depends(get_current_user)],
    status_code=status.HTTP_201_CREATED,
)
def create_store(
    payload: schemas.StoreCreate,
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_roles(*GESTION_ROLES)),
) -> schemas.StoreRead:
    """Crea una sucursal reutilizando la lógica del núcleo."""

    core_payload = payload.to_core()
    result = core_stores.create_store(core_payload, db, current_user)
    return schemas.StoreRead.from_core(result)


@router.get(
    "/stores/{store_id}",
    response_model=schemas.StoreRead,
    dependencies=[Depends(get_current_user)],
)
def retrieve_store(
    store_id: int = Path(..., ge=1, description="Identificador de la sucursal"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_roles(*GESTION_ROLES)),
) -> schemas.StoreRead:
    """Obtiene la información de una sucursal concreta."""

    try:
        result = core_stores.retrieve_store(store_id, db, current_user)
    except HTTPException:
        raise
    return schemas.StoreRead.from_core(result)


@router.put(
    "/stores/{store_id}",
    response_model=schemas.StoreRead,
    dependencies=[Depends(get_current_user)],
)
def update_store(
    payload: schemas.StoreUpdate,
    store_id: int = Path(..., ge=1, description="Identificador de la sucursal"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_roles(*GESTION_ROLES)),
) -> schemas.StoreRead:
    """Actualiza una sucursal existente aprovechando el núcleo corporativo."""

    core_payload = payload.to_core()
    try:
        result = core_stores.update_store(
            payload=core_payload, store_id=store_id, db=db, current_user=current_user
        )
    except HTTPException:
        raise
    return schemas.StoreRead.from_core(result)


@router.get(
    "/stores/{store_id}/memberships",
    response_model=Page[schemas.StoreMembershipRead],
    dependencies=[Depends(get_current_user)],
)
def list_memberships(
    store_id: int = Path(..., ge=1, description="Identificador de la sucursal"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_roles(*GESTION_ROLES)),
) -> Page[schemas.StoreMembershipRead]:
    """Lista las membresías activas de la sucursal en formato paginado."""

    core_page = core_stores.list_store_memberships(
        store_id=store_id,
        limit=limit,
        offset=offset,
        pagination=pagination,
        db=db,
        current_user=current_user,
    )
    items = [schemas.StoreMembershipRead.from_core(item) for item in core_page.items]
    return Page.from_items(items, page=core_page.page, size=core_page.size, total=core_page.total)


@router.put(
    "/stores/{store_id}/memberships/{user_id}",
    response_model=schemas.StoreMembershipRead,
    dependencies=[Depends(get_current_user)],
)
def upsert_membership(
    payload: schemas.StoreMembershipUpdate,
    store_id: int = Path(..., ge=1),
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_roles(*GESTION_ROLES)),
) -> schemas.StoreMembershipRead:
    """Crea o actualiza una membresía apoyándose en la lógica del núcleo."""

    if payload.store_id != store_id or payload.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los identificadores del cuerpo deben coincidir con la ruta.",
        )
    core_payload = payload.to_core()
    result = core_stores.upsert_membership(
        payload=core_payload,
        store_id=store_id,
        user_id=user_id,
        db=db,
        current_user=current_user,
    )
    return schemas.StoreMembershipRead.from_core(result)


@router.get(
    "/stores/{store_id}/devices",
    response_model=Page[schemas.StoreDeviceRead],
    dependencies=[Depends(get_current_user)],
    include_in_schema=False,
)
def proxy_list_devices(
    store_id: int,
    search: str | None = None,
    estado: str | None = None,
    categoria: str | None = None,
    condicion: str | None = None,
    estado_inventario: str | None = None,
    ubicacion: str | None = None,
    proveedor: str | None = None,
    fecha_ingreso_desde: date | None = None,
    fecha_ingreso_hasta: date | None = None,
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_roles(*REPORTE_ROLES)),
):
    """Delegado para no romper compatibilidad al incluir el router del núcleo."""

    core_page = core_stores.list_devices(
        store_id=store_id,
        search=search,
        estado=estado,
        categoria=categoria,
        condicion=condicion,
        estado_inventario=estado_inventario,
        ubicacion=ubicacion,
        proveedor=proveedor,
        fecha_ingreso_desde=fecha_ingreso_desde,
        fecha_ingreso_hasta=fecha_ingreso_hasta,
        db=db,
        current_user=current_user,
    )
    items = [schemas.StoreDeviceRead.from_core(item) for item in core_page.items]
    return Page.from_items(
        items,
        page=core_page.page,
        size=core_page.size,
        total=core_page.total,
    )


# Incluimos el router original para exponer el resto de operaciones avanzadas.
router.include_router(mount_core_router(core_stores.router))

__all__ = ["router"]
