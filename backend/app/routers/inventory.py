"""Operaciones sobre inventario, movimientos y reportes puntuales."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES, REPORTE_ROLES
from ..database import get_db
from ..security import require_roles

router = APIRouter(prefix="/inventory", tags=["inventario"])


@router.post(
    "/stores/{store_id}/movements",
    response_model=schemas.MovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_movement(
    payload: schemas.MovementCreate,
    store_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        movement = crud.create_inventory_movement(
            db,
            store_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado") from exc
    except ValueError as exc:
        if str(exc) == "insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stock insuficiente para registrar la salida.",
            ) from exc
        raise
    return movement


@router.patch(
    "/stores/{store_id}/devices/{device_id}",
    response_model=schemas.DeviceResponse,
)
def update_device(
    payload: schemas.DeviceUpdate,
    store_id: int = Path(..., ge=1),
    device_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    try:
        device = crud.update_device(
            db,
            store_id,
            device_id,
            payload,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado") from exc
    except ValueError as exc:
        if str(exc) == "device_identifier_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "device_identifier_conflict",
                    "message": "El IMEI o número de serie ya está registrado en otra sucursal.",
                },
            ) from exc
        raise
    return device


@router.get("/devices/search", response_model=list[schemas.CatalogProDeviceResponse])
def advanced_device_search(
    imei: str | None = Query(default=None, min_length=10, max_length=18),
    serial: str | None = Query(default=None, min_length=4, max_length=120),
    capacidad_gb: int | None = Query(default=None, ge=0),
    color: str | None = Query(default=None, max_length=60),
    marca: str | None = Query(default=None, max_length=80),
    modelo: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    if not settings.enable_catalog_pro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")
    filters = schemas.DeviceSearchFilters(
        imei=imei,
        serial=serial,
        capacidad_gb=capacidad_gb,
        color=color,
        marca=marca,
        modelo=modelo,
    )
    if not any(
        [
            filters.imei,
            filters.serial,
            filters.color,
            filters.marca,
            filters.modelo,
            filters.capacidad_gb is not None,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "catalog_filters_required",
                "message": "Proporciona al menos un criterio para buscar en el catálogo.",
            },
        )
    devices = crud.search_devices(db, filters)
    results: list[schemas.CatalogProDeviceResponse] = []
    for device in devices:
        base = schemas.DeviceResponse.model_validate(device, from_attributes=True)
        results.append(
            schemas.CatalogProDeviceResponse(
                **base.model_dump(),
                store_name=device.store.name if device.store else "",
            )
        )
    return results


@router.get("/summary", response_model=list[schemas.InventorySummary])
def inventory_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*REPORTE_ROLES)),
):
    stores = crud.list_inventory_summary(db)
    summaries: list[schemas.InventorySummary] = []
    for store in stores:
        devices = [
            schemas.DeviceResponse.model_validate(device, from_attributes=True)
            for device in store.devices
        ]
        total_items = sum(device.quantity for device in store.devices)
        total_value = sum(
            Decimal(device.quantity) * (device.unit_price or Decimal("0"))
            for device in store.devices
        )
        summaries.append(
            schemas.InventorySummary(
                store_id=store.id,
                store_name=store.name,
                total_items=total_items,
                total_value=total_value,
                devices=devices,
            )
        )
    return summaries
