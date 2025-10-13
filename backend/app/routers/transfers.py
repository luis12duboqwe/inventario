"""Rutas para gestionar transferencias entre sucursales."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..security import require_roles

router = APIRouter(prefix="/transfers", tags=["transferencias"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_transfers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")


@router.get("/", response_model=list[schemas.TransferOrderResponse])
def list_transfers(
    limit: int = 50,
    store_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    orders = crud.list_transfer_orders(db, store_id=store_id, limit=min(limit, 100))
    return orders


@router.post("/", response_model=schemas.TransferOrderResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: schemas.TransferOrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.create_transfer_order(db, payload, requested_by_id=current_user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para transferir desde esta sucursal.") from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado") from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "transfer_same_store":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La sucursal de origen y destino deben ser distintas.") from exc
        if detail == "transfer_items_required":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Debes agregar al menos un dispositivo a la transferencia.") from exc
        if detail == "transfer_invalid_quantity":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La cantidad debe ser mayor a cero.") from exc
        raise


@router.post("/{transfer_id}/dispatch", response_model=schemas.TransferOrderResponse)
def dispatch_transfer(
    payload: schemas.TransferOrderTransition,
    transfer_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.dispatch_transfer_order(
            db,
            transfer_id,
            performed_by_id=current_user.id,
            reason=payload.reason,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para despachar esta transferencia.") from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transferencia no encontrada") from exc
    except ValueError as exc:
        if str(exc) == "transfer_invalid_transition":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No es posible despachar la transferencia en su estado actual.") from exc
        raise


@router.post("/{transfer_id}/receive", response_model=schemas.TransferOrderResponse)
def receive_transfer(
    payload: schemas.TransferOrderTransition,
    transfer_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.receive_transfer_order(
            db,
            transfer_id,
            performed_by_id=current_user.id,
            reason=payload.reason,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para recibir en esta sucursal.") from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transferencia no encontrada") from exc
    except ValueError as exc:
        detail = str(exc)
        if detail == "transfer_invalid_transition":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La transferencia no puede recibirse en su estado actual.") from exc
        if detail == "transfer_insufficient_stock":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La sucursal de origen no cuenta con stock suficiente.") from exc
        if detail == "transfer_requires_full_unit":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Los dispositivos con IMEI o serie deben transferirse completos.") from exc
        raise


@router.post("/{transfer_id}/cancel", response_model=schemas.TransferOrderResponse)
def cancel_transfer(
    payload: schemas.TransferOrderTransition,
    transfer_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    try:
        return crud.cancel_transfer_order(
            db,
            transfer_id,
            performed_by_id=current_user.id,
            reason=payload.reason,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para cancelar esta transferencia.") from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transferencia no encontrada") from exc
    except ValueError as exc:
        if str(exc) == "transfer_invalid_transition":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La transferencia ya fue cerrada.") from exc
        raise
