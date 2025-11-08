"""Endpoints dedicados a exportaciones y etiquetas de inventario."""
from __future__ import annotations

from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, Path, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.roles import ADMIN
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import (
    inventory_catalog_export,
    inventory_import as inventory_import_service,
    inventory_labels,
)

router = APIRouter(prefix="/inventory", tags=["inventario"])


def _parse_commercial_state(value: str | None) -> models.CommercialState | None:
    """Intenta mapear la cadena recibida a un estado comercial válido."""

    if not value:
        return None

    normalized = value.strip()
    for candidate in (normalized, normalized.lower(), normalized.upper()):
        try:
            return models.CommercialState(candidate)
        except ValueError:
            continue
    return None


def _render_csv_response(
    *,
    db: Session,
    store_id: int,
    search: str | None,
    estado: str | None,
    categoria: str | None,
    condicion: str | None,
    estado_inventario: str | None,
    ubicacion: str | None,
    proveedor: str | None,
    fecha_ingreso_desde: date | None,
    fecha_ingreso_hasta: date | None,
) -> Response:
    estado_enum = _parse_commercial_state(estado)
    csv_data = inventory_import_service.export_devices_csv(
        db,
        store_id,
        search=search,
        estado=estado_enum,
        categoria=categoria,
        condicion=condicion,
        estado_inventario=estado_inventario,
        ubicacion=ubicacion,
        proveedor=proveedor,
        fecha_ingreso_desde=fecha_ingreso_desde,
        fecha_ingreso_hasta=fecha_ingreso_hasta,
    )
    metadata = schemas.BinaryFileResponse(
        filename=f"softmobile_catalogo_{store_id}.csv",
        media_type="text/csv",
    )
    return Response(
        content=csv_data,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/stores/{store_id}/devices/export",
    response_class=Response,
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
def export_devices_legacy(
    store_id: int = Path(..., ge=1),
    search: str | None = Query(default=None),
    estado: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    condicion: str | None = Query(default=None),
    estado_inventario: str | None = Query(default=None),
    ubicacion: str | None = Query(default=None),
    proveedor: str | None = Query(default=None),
    fecha_ingreso_desde: date | None = Query(default=None),
    fecha_ingreso_hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
) -> Response:
    """Mantiene la exportación CSV en la ruta histórica."""

    return _render_csv_response(
        db=db,
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
    )


@router.get(
    "/stores/{store_id}/devices/export/csv",
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
def export_devices_csv(
    store_id: int = Path(..., ge=1),
    search: str | None = Query(default=None),
    estado: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    condicion: str | None = Query(default=None),
    estado_inventario: str | None = Query(default=None),
    ubicacion: str | None = Query(default=None),
    proveedor: str | None = Query(default=None),
    fecha_ingreso_desde: date | None = Query(default=None),
    fecha_ingreso_hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
) -> Response:
    """Exporta el catálogo de dispositivos en formato CSV dedicado."""

    return _render_csv_response(
        db=db,
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
    )


@router.get(
    "/stores/{store_id}/devices/export/pdf",
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
def export_devices_pdf(
    store_id: int = Path(..., ge=1),
    search: str | None = Query(default=None),
    estado: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    condicion: str | None = Query(default=None),
    estado_inventario: str | None = Query(default=None),
    ubicacion: str | None = Query(default=None),
    proveedor: str | None = Query(default=None),
    fecha_ingreso_desde: date | None = Query(default=None),
    fecha_ingreso_hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
):
    """Genera un catálogo PDF en tema oscuro."""

    estado_enum = _parse_commercial_state(estado)
    pdf_bytes = inventory_catalog_export.render_devices_catalog_pdf(
        db,
        store_id,
        search=search,
        estado=estado_enum,
        categoria=categoria,
        condicion=condicion,
        estado_inventario=estado_inventario,
        ubicacion=ubicacion,
        proveedor=proveedor,
        fecha_ingreso_desde=fecha_ingreso_desde,
        fecha_ingreso_hasta=fecha_ingreso_hasta,
    )
    metadata = schemas.BinaryFileResponse(
        filename=f"softmobile_catalogo_{store_id}.pdf",
        media_type="application/pdf",
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/stores/{store_id}/devices/export/xlsx",
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
def export_devices_excel(
    store_id: int = Path(..., ge=1),
    search: str | None = Query(default=None),
    estado: str | None = Query(default=None),
    categoria: str | None = Query(default=None),
    condicion: str | None = Query(default=None),
    estado_inventario: str | None = Query(default=None),
    ubicacion: str | None = Query(default=None),
    proveedor: str | None = Query(default=None),
    fecha_ingreso_desde: date | None = Query(default=None),
    fecha_ingreso_hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
):
    """Genera un catálogo Excel con filtros aplicados."""

    estado_enum = _parse_commercial_state(estado)
    excel_bytes = inventory_catalog_export.render_devices_catalog_excel(
        db,
        store_id,
        search=search,
        estado=estado_enum,
        categoria=categoria,
        condicion=condicion,
        estado_inventario=estado_inventario,
        ubicacion=ubicacion,
        proveedor=proveedor,
        fecha_ingreso_desde=fecha_ingreso_desde,
        fecha_ingreso_hasta=fecha_ingreso_hasta,
    )
    metadata = schemas.BinaryFileResponse(
        filename=f"softmobile_catalogo_{store_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type=metadata.media_type,
        headers=metadata.content_disposition(),
        status_code=status.HTTP_200_OK,
    )


@router.get(
    "/stores/{store_id}/devices/{device_id}/label/pdf",
    response_class=Response,
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
def export_device_label_pdf(
    store_id: int = Path(..., ge=1),
    device_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
):
    """Genera una etiqueta PDF para el dispositivo indicado."""

    pdf_bytes, filename = inventory_labels.render_device_label_pdf(
        db, store_id, device_id
    )
    metadata = schemas.BinaryFileResponse(
        filename=filename,
        media_type="application/pdf",
    )
    return Response(
        content=pdf_bytes,
        media_type=metadata.media_type,
        headers=metadata.content_disposition(disposition="inline"),
        status_code=status.HTTP_200_OK,
    )
