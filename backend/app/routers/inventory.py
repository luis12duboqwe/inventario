"""Operaciones sobre inventario, movimientos y reportes puntuales."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from .. import crud, schemas
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
    current_user=Depends(require_roles("admin", "manager")),
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
    current_user=Depends(require_roles("admin", "manager")),
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
    return device


@router.get("/summary", response_model=list[schemas.InventorySummary])
def inventory_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager", "auditor")),
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
