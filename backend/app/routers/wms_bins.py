"""Rutas para ubicaciones WMS (bins) por sucursal.

Compatibles con v2.2.0 bajo bandera SOFTMOBILE_ENABLE_WMS_BINS sin romper
comportamientos existentes. Todas las operaciones sensibles exigen X-Reason.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import MOVEMENT_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles

router = APIRouter(prefix="/inventory", tags=["inventario", "wms"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_wms_bins:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funcionalidad no disponible",
        )


@router.get(
    "/stores/{store_id}/bins",
    response_model=list[schemas.WMSBinResponse],
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def list_bins(
    store_id: int = Path(..., ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    bins = crud.list_wms_bins(db, store_id, limit=limit, offset=offset)
    return [
        schemas.WMSBinResponse.model_validate(b, from_attributes=True)
        for b in bins
    ]


@router.post(
    "/stores/{store_id}/bins",
    response_model=schemas.WMSBinResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def create_bin(
    payload: schemas.WMSBinCreate,
    store_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    try:
        created = crud.create_wms_bin(
            db, store_id, payload, performed_by_id=getattr(
                current_user, "id", None)
        )
        return schemas.WMSBinResponse.model_validate(created, from_attributes=True)
    except ValueError as exc:
        message = str(exc)
        if message == "wms_bin_duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "wms_bin_duplicate",
                        "message": "El código de bin ya existe en la sucursal."},
            ) from exc
        if message == "wms_bin_code_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "wms_bin_code_required",
                        "message": "El código del bin es obligatorio."},
            ) from exc
        raise


@router.put(
    "/stores/{store_id}/bins/{bin_id}",
    response_model=schemas.WMSBinResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def update_bin(
    payload: schemas.WMSBinUpdate,
    store_id: int = Path(..., ge=1),
    bin_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    try:
        updated = crud.update_wms_bin(
            db, store_id, bin_id, payload, performed_by_id=getattr(
                current_user, "id", None)
        )
        return schemas.WMSBinResponse.model_validate(updated, from_attributes=True)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Recurso no encontrado") from exc
    except ValueError as exc:
        message = str(exc)
        if message == "wms_bin_duplicate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "wms_bin_duplicate",
                        "message": "El código de bin ya existe en la sucursal."},
            ) from exc
        if message == "wms_bin_code_required":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "wms_bin_code_required",
                        "message": "El código del bin es obligatorio."},
            ) from exc
        raise


@router.get(
    "/stores/{store_id}/devices/{device_id}/bin",
    response_model=schemas.WMSBinResponse | None,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def get_device_bin(
    store_id: int = Path(..., ge=1),
    device_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    try:
        result = crud.get_device_current_bin(db, store_id, device_id)
        if result is None:
            return None
        return schemas.WMSBinResponse.model_validate(result, from_attributes=True)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Dispositivo no encontrado") from exc


@router.post(
    "/stores/{store_id}/devices/{device_id}/bin",
    response_model=schemas.DeviceBinAssignmentResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def assign_device_bin(
    *,
    store_id: int = Path(..., ge=1),
    device_id: int = Path(..., ge=1),
    bin_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    try:
        assignment = crud.assign_device_to_bin(
            db,
            store_id,
            device_id=device_id,
            bin_id=bin_id,
            performed_by_id=getattr(current_user, "id", None),
            reason=reason,
        )
    except LookupError as exc:
        msg = str(exc)
        if msg == "wms_bin_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Bin no encontrado") from exc
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Dispositivo no encontrado") from exc
    # Construir respuesta envolviendo el bin
    current_bin = crud.get_device_current_bin(db, store_id, device_id)
    if current_bin is None:
        # Teóricamente no ocurre después de asignar
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Asignación no persistida")
    return schemas.DeviceBinAssignmentResponse(
        producto_id=device_id,
        bin=schemas.WMSBinResponse.model_validate(
            current_bin, from_attributes=True),
        asignado_en=assignment.assigned_at,
        desasignado_en=assignment.unassigned_at,
    )


@router.get(
    "/stores/{store_id}/bins/{bin_id}/devices",
    response_model=list[schemas.DeviceResponse],
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def list_devices_for_bin(
    store_id: int = Path(..., ge=1),
    bin_id: int = Path(..., ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    _ensure_feature_enabled()
    try:
        devices = crud.list_devices_in_bin(
            db, store_id, bin_id, limit=limit, offset=offset)
        return [schemas.DeviceResponse.model_validate(d, from_attributes=True) for d in devices]
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Bin no encontrado") from exc
