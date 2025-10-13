"""Rutas relacionadas con sucursales y dispositivos."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..security import require_roles

router = APIRouter(prefix="/stores", tags=["stores"])


@router.post(
    "",
    response_model=schemas.StoreResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_store(
    payload: schemas.StoreCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
):
    try:
        store = crud.create_store(db, payload, performed_by_id=current_user.id if current_user else None)
    except ValueError as exc:
        if str(exc) == "store_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "store_already_exists",
                    "message": "Ya existe una sucursal con ese nombre.",
                },
            ) from exc
        raise
    return store


@router.get("", response_model=list[schemas.StoreResponse])
def list_stores(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
):
    return crud.list_stores(db)


@router.get("/{store_id}", response_model=schemas.StoreResponse)
def retrieve_store(
    store_id: int = Path(..., ge=1, description="Identificador de la sucursal"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
):
    try:
        return crud.get_store(db, store_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "store_not_found", "message": "La sucursal solicitada no existe."},
        ) from exc


@router.post(
    "/{store_id}/devices",
    response_model=schemas.DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_device(
    payload: schemas.DeviceCreate,
    store_id: int = Path(..., ge=1, description="Identificador de la sucursal"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
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
            detail={"code": "store_not_found", "message": "La sucursal solicitada no existe."},
        ) from exc
    except ValueError as exc:
        if str(exc) == "device_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "device_already_exists",
                    "message": "Ya existe un dispositivo con ese SKU en la sucursal.",
                },
            ) from exc
        raise
    return device


@router.get("/{store_id}/devices", response_model=list[schemas.DeviceResponse])
def list_devices(
    store_id: int = Path(..., ge=1, description="Identificador de la sucursal"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager", "auditor")),
):
    try:
        return crud.list_devices(db, store_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "store_not_found", "message": "La sucursal solicitada no existe."},
        ) from exc
