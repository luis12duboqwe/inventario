"""Endpoints for device management."""
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from .... import schemas
from ....core.roles import GESTION_ROLES, REPORTE_ROLES
from ....models.store import Store
from ....security import get_current_user, require_roles
from ....services.inventory import create_device, list_devices
from ...deps import get_db

router = APIRouter()


@router.get(
    "/",
    response_model=list[schemas.Device],
    summary="Listar dispositivos",
    dependencies=[Depends(get_current_user), Depends(require_roles(*REPORTE_ROLES))],
)
def get_devices(
    store_id: int = Path(..., description="Identificador de la sucursal"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*REPORTE_ROLES)),
) -> list[schemas.Device]:
    """Return every device belonging to the requested store."""

    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    return list_devices(db, store_id, limit=limit, offset=offset)


@router.post(
    "/",
    response_model=schemas.Device,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar dispositivo",
    dependencies=[Depends(get_current_user), Depends(require_roles(*GESTION_ROLES))],
)
def add_device(
    *,
    store_id: int = Path(..., description="Identificador de la sucursal"),
    device_in: schemas.DeviceCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles(*GESTION_ROLES)),
) -> schemas.Device:
    """Create a new device for the selected store."""

    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    try:
        return create_device(db, store_id=store_id, device_in=device_in)
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
