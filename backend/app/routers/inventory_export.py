"""Endpoints dedicados a exportaciones y etiquetas de inventario."""
from __future__ import annotations

from datetime import date
from io import BytesIO

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
    Response,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..core.roles import ADMIN
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import (
    inventory_catalog_export,
    inventory_import as inventory_import_service,
    inventory_labels,
    hardware,
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


def _resolve_label_connector(
    db: Session, store_id: int, printer_name: str | None
) -> schemas.POSConnectorSettings | None:
    try:
        config = crud.get_pos_config(db, store_id)
    except LookupError:
        return None
    hardware_settings = schemas.POSHardwareSettings.model_validate(
        config.hardware_settings
    )
    if not hardware_settings.printers:
        return None
    printer = None
    if printer_name:
        printer = next(
            (
                item
                for item in hardware_settings.printers
                if item.name.lower() == printer_name.lower()
            ),
            None,
        )
    if printer is None:
        printer = next((item for item in hardware_settings.printers if item.is_default), None)
    if printer is None:
        printer = hardware_settings.printers[0]
    return printer.connector


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
    "/stores/{store_id}/devices/{device_id}/label/{format}",
    response_class=Response,
    dependencies=[Depends(require_roles(ADMIN))],
)
def export_device_label(
    store_id: int = Path(..., ge=1),
    device_id: int = Path(..., ge=1),
    format: schemas.LabelFormat = Path(...),
    template: schemas.LabelTemplateKey = Query(
        default=schemas.LabelTemplateKey.SIZE_38X25
    ),
    printer_name: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
):
    """Genera etiquetas en PDF o comandos directos (ZPL/ESC/POS)."""

    connector = _resolve_label_connector(db, store_id, printer_name)
    if format is schemas.LabelFormat.PDF:
        pdf_bytes, filename = inventory_labels.render_device_label_pdf(
            db, store_id, device_id, template_key=template
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

    commands, filename = inventory_labels.render_device_label_commands(
        db,
        store_id,
        device_id,
        format=format,
        template_key=template,
    )
    content_type = "text/zpl" if format is schemas.LabelFormat.ZPL else "text/escpos"
    payload = schemas.LabelCommandsResponse(
        format=format,
        template=template,
        commands=commands,
        filename=filename,
        content_type=content_type,
        connector=connector,
    )
    return JSONResponse(content=payload.model_dump(), status_code=status.HTTP_200_OK)


@router.post(
    "/stores/{store_id}/devices/{device_id}/label/print",
    response_model=schemas.POSHardwareActionResponse,
)
async def enqueue_device_label_print(
    background_tasks: BackgroundTasks,
    payload: schemas.InventoryLabelPrintRequest,
    store_id: int = Path(..., ge=1),
    device_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(ADMIN)),
):
    """Encola una impresión directa de etiqueta vía canal de hardware."""

    commands, filename = inventory_labels.render_device_label_commands(
        db,
        store_id,
        device_id,
        format=payload.format,
        template_key=payload.template,
    )
    connector = payload.connector or _resolve_label_connector(db, store_id, None)
    if payload.format is schemas.LabelFormat.ZPL:
        job = hardware.build_zebra_job(
            template=payload.template.value,
            commands=commands,
            connector=connector,
        )
    elif payload.format is schemas.LabelFormat.ESCPOS:
        job = hardware.build_epson_job(
            template=payload.template.value,
            commands=commands,
            connector=connector,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de etiqueta no soportado para impresión directa.",
        )
    event = job.as_event(store_id=store_id)
    hardware.hardware_channels.schedule_broadcast(background_tasks, store_id, event)
    crud.log_audit_event(
        db,
        action="inventory_label_direct_print",
        entity_type="inventory_label",
        entity_id=f"{store_id}:{device_id}",
        performed_by_id=current_user.id if current_user else None,
        details={
            "formato": payload.format.value,
            "plantilla": payload.template.value,
            "archivo": filename,
            "reason": reason,
            "connector": connector.model_dump() if connector else None,
        },
    )
    return schemas.POSHardwareActionResponse(
        status="queued",
        message="Etiqueta encolada para impresión local.",
        details=event,
    )
