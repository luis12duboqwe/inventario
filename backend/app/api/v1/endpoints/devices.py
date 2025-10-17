"""Endpoints for device management."""
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from .... import schemas
from ....models import Store
from ....services.inventory import create_device, list_devices
from ...deps import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.DeviceResponse], summary="Listar dispositivos")
def get_devices(
    store_id: int = Path(..., description="Identificador de la sucursal"),
    db: Session = Depends(get_db),
) -> list[schemas.DeviceResponse]:
    """Return every device belonging to the requested store."""

    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    return list_devices(db, store_id)


@router.post(
    "/",
    response_model=schemas.DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar dispositivo",
)
def add_device(
    *,
    store_id: int = Path(..., description="Identificador de la sucursal"),
    device_in: schemas.DeviceCreate,
    db: Session = Depends(get_db),
) -> schemas.DeviceResponse:
    """Create a new device for the selected store."""

    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sucursal no encontrada")
    return create_device(db, store_id=store_id, device_in=device_in)
