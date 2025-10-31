"""Operaciones sobre inventario, movimientos y reportes puntuales."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import ADMIN, MOVEMENT_ROLES
from ..core.transactions import transactional_session
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import inventory_import, inventory_smart_import
from backend.schemas.common import Page, PageParams

router = APIRouter(prefix="/inventory", tags=["inventario"])


@router.post(
    "/import/smart",
    response_model=schemas.InventorySmartImportResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
async def smart_import_inventory(
    file: UploadFile = File(...),
    commit: bool = Form(default=False),
    overrides: str | None = Form(default=None),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    try:
        parsed_overrides = json.loads(overrides) if overrides else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="overrides_invalid",
        ) from exc
    if not isinstance(parsed_overrides, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="overrides_invalid",
        )
    overrides_cast = {
        str(key): str(value) for key, value in parsed_overrides.items()
    }
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="archivo_vacio",
        )
    try:
        response = inventory_smart_import.process_smart_import(
            db,
            file_bytes=contents,
            filename=file.filename or "importacion.xlsx",
            commit=commit,
            overrides=overrides_cast,
            performed_by_id=current_user.id if current_user else None,
            username=getattr(current_user, "username", None),
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return response


@router.get(
    "/import/smart/history",
    response_model=Page[schemas.InventoryImportHistoryEntry],
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def list_import_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> Page[schemas.InventoryImportHistoryEntry]:
    page_offset = (
        pagination.offset if (pagination.page > 1 and offset == 0) else offset
    )
    page_size = min(pagination.size, limit)
    total = crud.count_inventory_import_history(db)
    records = crud.list_inventory_import_history(
        db, limit=page_size, offset=page_offset
    )
    items = [
        schemas.InventoryImportHistoryEntry.model_validate(record)
        for record in records
    ]
    return Page.from_items(items, page=pagination.page, size=page_size, total=total)


@router.get(
    "/devices/incomplete",
    response_model=Page[schemas.DeviceResponse],
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def list_incomplete_inventory_devices(
    store_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> Page[schemas.DeviceResponse]:
    page_offset = (
        pagination.offset if (pagination.page > 1 and offset == 0) else offset
    )
    page_size = min(pagination.size, limit)
    total = crud.count_incomplete_devices(db, store_id=store_id)
    devices = crud.list_incomplete_devices(
        db, store_id=store_id, limit=page_size, offset=page_offset
    )
    items = [schemas.DeviceResponse.model_validate(device) for device in devices]
    return Page.from_items(items, page=pagination.page, size=page_size, total=total)


@router.post(
    "/stores/{store_id}/movements",
    response_model=schemas.MovementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def register_movement(
    payload: schemas.MovementCreate,
    store_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    if payload.comentario != reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "reason_comment_mismatch",
                "message": "El comentario debe coincidir con el motivo corporativo enviado en la cabecera X-Reason.",
            },
        )
    try:
        with transactional_session(db):
            movement = crud.create_inventory_movement(
                db,
                store_id,
                payload,
                performed_by_id=current_user.id if current_user else None,
            )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado") from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo gerentes o administradores pueden registrar ajustes de inventario.",
        ) from exc
    except ValueError as exc:
        if str(exc) == "insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stock insuficiente para registrar la salida.",
            ) from exc
        if str(exc) == "invalid_destination_store":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "invalid_destination_store",
                    "message": "La sucursal destino del movimiento debe coincidir con la seleccionada.",
                },
            ) from exc
        raise
    return movement


@router.patch(
    "/stores/{store_id}/devices/{device_id}",
    response_model=schemas.DeviceResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def update_device(
    payload: schemas.DeviceUpdate,
    store_id: int = Path(..., ge=1),
    device_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    try:
        with transactional_session(db):
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


@router.get(
    "/stores/{store_id}/devices/{device_id}/identifier",
    response_model=schemas.DeviceIdentifierResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def retrieve_device_identifier(
    store_id: int = Path(..., ge=1),
    device_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    try:
        return crud.get_device_identifier(db, store_id, device_id)
    except LookupError as exc:
        message = str(exc)
        if message == "device_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "device_not_found", "message": "Dispositivo no encontrado"},
            ) from exc
        if message == "device_identifier_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "device_identifier_not_found",
                    "message": "El dispositivo no tiene identificadores registrados.",
                },
            ) from exc
        raise


@router.put(
    "/stores/{store_id}/devices/{device_id}/identifier",
    response_model=schemas.DeviceIdentifierResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def upsert_device_identifier(
    payload: schemas.DeviceIdentifierRequest,
    store_id: int = Path(..., ge=1),
    device_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    try:
        return crud.upsert_device_identifier(
            db,
            store_id,
            device_id,
            payload,
            reason=reason,
            performed_by_id=current_user.id if current_user else None,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        ) from exc
    except ValueError as exc:
        if str(exc) == "device_identifier_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "device_identifier_conflict",
                    "message": "El IMEI o número de serie ya fue registrado en otro producto.",
                },
            ) from exc
        raise


@router.get(
    "/devices/search",
    response_model=Page[schemas.CatalogProDeviceResponse],
    dependencies=[Depends(require_roles(ADMIN))],
)
def advanced_device_search(
    imei: str | None = Query(default=None, min_length=10, max_length=18),
    serial: str | None = Query(default=None, min_length=4, max_length=120),
    capacidad_gb: int | None = Query(default=None, ge=0),
    color: str | None = Query(default=None, max_length=60),
    marca: str | None = Query(default=None, max_length=80),
    modelo: str | None = Query(default=None, max_length=120),
    categoria: str | None = Query(default=None, max_length=80),
    condicion: str | None = Query(default=None, max_length=60),
    estado: str | None = Query(default=None, max_length=40),
    ubicacion: str | None = Query(default=None, max_length=120),
    proveedor: str | None = Query(default=None, max_length=120),
    fecha_ingreso_desde: date | None = Query(default=None),
    fecha_ingreso_hasta: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> Page[schemas.CatalogProDeviceResponse]:
    if not settings.enable_catalog_pro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionalidad no disponible")
    filters = schemas.DeviceSearchFilters(
        imei=imei,
        serial=serial,
        capacidad_gb=capacidad_gb,
        color=color,
        marca=marca,
        modelo=modelo,
        categoria=categoria,
        condicion=condicion,
        estado=estado,
        ubicacion=ubicacion,
        proveedor=proveedor,
        fecha_ingreso_desde=fecha_ingreso_desde,
        fecha_ingreso_hasta=fecha_ingreso_hasta,
    )
    if not any(
        [
            filters.imei,
            filters.serial,
            filters.color,
            filters.marca,
            filters.modelo,
            filters.categoria,
            filters.condicion,
            filters.estado,
            filters.ubicacion,
            filters.proveedor,
            filters.capacidad_gb is not None,
            filters.fecha_ingreso_desde is not None,
            filters.fecha_ingreso_hasta is not None,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "catalog_filters_required",
                "message": "Proporciona al menos un criterio para buscar en el catálogo.",
            },
        )
    page_offset = (
        pagination.offset if (pagination.page > 1 and offset == 0) else offset
    )
    page_size = min(pagination.size, limit)
    total = crud.count_devices_matching_filters(db, filters)
    devices = crud.search_devices(
        db, filters, limit=page_size, offset=page_offset
    )
    results: list[schemas.CatalogProDeviceResponse] = []
    for device in devices:
        base = schemas.DeviceResponse.model_validate(device, from_attributes=True)
        results.append(
            schemas.CatalogProDeviceResponse(
                **base.model_dump(),
                store_name=device.store.name if device.store else "",
            )
        )
    return Page.from_items(results, page=pagination.page, size=page_size, total=total)


@router.get("/summary", response_model=Page[schemas.InventorySummary], dependencies=[Depends(require_roles(ADMIN))])
def inventory_summary(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
) -> Page[schemas.InventorySummary]:
    page_offset = (
        pagination.offset if (pagination.page > 1 and offset == 0) else offset
    )
    page_size = min(pagination.size, limit)
    total = crud.count_stores(db)
    stores = crud.list_inventory_summary(db, limit=page_size, offset=page_offset)
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
    return Page.from_items(summaries, page=pagination.page, size=page_size, total=total)


@router.get(
    "/stores/{store_id}/devices/export",
    response_class=Response,
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
def export_devices(
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
    estado_enum: models.CommercialState | None = None
    if estado:
        normalized = estado.strip()
        try:
            estado_enum = models.CommercialState(normalized)
        except ValueError:
            try:
                estado_enum = models.CommercialState(normalized.lower())
            except ValueError:
                try:
                    estado_enum = models.CommercialState(normalized.upper())
                except ValueError:
                    estado_enum = None
    csv_data = inventory_import.export_devices_csv(
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
    )


@router.post(
    "/stores/{store_id}/devices/import",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.InventoryImportSummary,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
async def import_devices(
    store_id: int = Path(..., ge=1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
):
    if file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/octet-stream", None}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato no soportado. Carga un archivo CSV.",
        )
    content = await file.read()
    try:
        summary = inventory_import.import_devices_from_csv(
            db,
            store_id,
            content,
            performed_by_id=current_user.id if current_user else None,
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("csv_missing_columns"):
            missing = message.split(":", maxsplit=1)[1]
            detail = {
                "code": "csv_missing_columns",
                "message": f"El archivo debe incluir las columnas requeridas: {missing}",
            }
        elif message == "csv_missing_header":
            detail = {"code": "csv_missing_header", "message": "No se encontró encabezado en el archivo."}
        elif message == "csv_encoding_error":
            detail = {
                "code": "csv_encoding_error",
                "message": "No fue posible leer el archivo. Usa codificación UTF-8.",
            }
        else:
            detail = {
                "code": "csv_import_error",
                "message": "El archivo contiene datos inválidos.",
            }
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
    return schemas.InventoryImportSummary(**summary)
