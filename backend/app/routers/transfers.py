"""Rutas para gestionar transferencias entre sucursales."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import GESTION_ROLES
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import transfer_reports

router = APIRouter(prefix="/transfers", tags=["transferencias"])


def _ensure_feature_enabled() -> None:
    if not settings.enable_transfers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")


def _prepare_transfer_report(
    db: Session,
    *,
    store_id: int | None,
    origin_store_id: int | None,
    destination_store_id: int | None,
    status: models.TransferStatus | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> schemas.TransferReport:
    transfers = crud.list_transfer_orders(
        db,
        store_id=store_id,
        origin_store_id=origin_store_id,
        destination_store_id=destination_store_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=500,
    )
    filters = schemas.TransferReportFilters(
        store_id=store_id,
        origin_store_id=origin_store_id,
        destination_store_id=destination_store_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return transfer_reports.build_transfer_report(transfers, filters)


@router.get("/", response_model=list[schemas.TransferOrderResponse])
def list_transfers(
    limit: int = Query(default=50, ge=1, le=200),
    store_id: int | None = Query(default=None, ge=1),
    origin_store_id: int | None = Query(default=None, ge=1),
    destination_store_id: int | None = Query(default=None, ge=1),
    status: models.TransferStatus | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    orders = crud.list_transfer_orders(
        db,
        store_id=store_id,
        origin_store_id=origin_store_id,
        destination_store_id=destination_store_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=min(limit, 200),
    )
    return orders


@router.get("/report", response_model=schemas.TransferReport)
def transfer_report(
    store_id: int | None = Query(default=None, ge=1),
    origin_store_id: int | None = Query(default=None, ge=1),
    destination_store_id: int | None = Query(default=None, ge=1),
    status: models.TransferStatus | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    return _prepare_transfer_report(
        db,
        store_id=store_id,
        origin_store_id=origin_store_id,
        destination_store_id=destination_store_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/export/pdf", response_model=schemas.BinaryFileResponse)
def export_transfer_report_pdf(
    store_id: int | None = Query(default=None, ge=1),
    origin_store_id: int | None = Query(default=None, ge=1),
    destination_store_id: int | None = Query(default=None, ge=1),
    status: models.TransferStatus | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    report = _prepare_transfer_report(
        db,
        store_id=store_id,
        origin_store_id=origin_store_id,
        destination_store_id=destination_store_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    pdf_bytes = transfer_reports.render_transfer_report_pdf(report)
    metadata = schemas.BinaryFileResponse(
        filename=f"transferencias_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


@router.get("/export/xlsx", response_model=schemas.BinaryFileResponse)
def export_transfer_report_excel(
    store_id: int | None = Query(default=None, ge=1),
    origin_store_id: int | None = Query(default=None, ge=1),
    destination_store_id: int | None = Query(default=None, ge=1),
    status: models.TransferStatus | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
):
    _ensure_feature_enabled()
    report = _prepare_transfer_report(
        db,
        store_id=store_id,
        origin_store_id=origin_store_id,
        destination_store_id=destination_store_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    excel_bytes = transfer_reports.render_transfer_report_excel(report)
    metadata = schemas.BinaryFileResponse(
        filename=f"transferencias_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
    )


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
