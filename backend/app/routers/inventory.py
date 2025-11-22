"""Operaciones sobre inventario, movimientos y reportes puntuales."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.schemas.common import Page, PageParams

from .. import crud, models, schemas
from ..config import settings
from ..core.roles import ADMIN, MOVEMENT_ROLES
from ..core.transactions import transactional_session
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import require_roles
from ..services import (
    inventory_availability,
    inventory_catalog_export,
    inventory_import,
    inventory_labels,
    inventory_search,
    inventory_smart_import,
)
from backend.schemas.common import Page, PageParams

router = APIRouter(prefix="/inventory", tags=["inventario"])


@router.get(
    "/stores/{store_id}/warehouses",
    response_model=list[schemas.WarehouseResponse],
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def list_store_warehouses(
    store_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> list[schemas.WarehouseResponse]:
    try:
        warehouses = crud.list_warehouses(db, store_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La sucursal solicitada no existe.",
        ) from exc
    return [
        schemas.WarehouseResponse.model_validate(warehouse, from_attributes=True)
        for warehouse in warehouses
    ]


@router.post(
    "/stores/{store_id}/warehouses",
    response_model=schemas.WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def create_store_warehouse(
    payload: schemas.WarehouseCreate,
    store_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.WarehouseResponse:
    try:
        warehouse = crud.create_warehouse(
            db,
            store_id,
            payload,
            performed_by_id=getattr(current_user, "id", None),
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La sucursal solicitada no existe.",
        ) from exc
    except ValueError as exc:
        message = str(exc)
        if message in {"warehouse_code_duplicate", "warehouse_name_duplicate"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc
        if message in {"warehouse_name_required", "warehouse_code_required"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=message,
            ) from exc
        raise
    return schemas.WarehouseResponse.model_validate(warehouse, from_attributes=True)


@router.post(
    "/warehouses/transfers",
    response_model=schemas.WarehouseTransferResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def transfer_between_warehouses_endpoint(
    payload: schemas.WarehouseTransferCreate,
    db: Session = Depends(get_db),
    _reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.WarehouseTransferResponse:
    try:
        movement_out, movement_in = crud.transfer_between_warehouses(
            db, payload, performed_by_id=getattr(current_user, "id", None)
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén no encontrado",
        ) from exc
    except ValueError as exc:
        message = str(exc)
        if message in {
            "warehouse_transfer_same_destination",
            "warehouse_transfer_invalid_quantity",
            "warehouse_transfer_full_quantity_required",
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=message,
            ) from exc
        if message in {"insufficient_stock", "warehouse_transfer_mismatch"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc
        raise
    return schemas.WarehouseTransferResponse(
        movement_out=schemas.MovementResponse.model_validate(
            movement_out, from_attributes=True
        ),
        movement_in=schemas.MovementResponse.model_validate(
            movement_in, from_attributes=True
        ),
    )


@router.get(
    "/availability",
    response_model=schemas.InventoryAvailabilityResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def get_inventory_availability(
    db: Session = Depends(get_db),
    query: str | None = Query(default=None, min_length=2, max_length=120),
    limit: int = Query(default=50, ge=1, le=250),
    sku: list[str] = Query(default_factory=list),
    device_id: list[int] = Query(default_factory=list),
) -> schemas.InventoryAvailabilityResponse:
    normalized_query = query.strip() if query else None
    normalized_skus = [value.strip() for value in sku if value and value.strip()]
    normalized_ids = sorted({int(value) for value in device_id if value > 0})
    payload = inventory_availability.get_inventory_availability(
        db,
        skus=normalized_skus or None,
        device_ids=normalized_ids or None,
        search=normalized_query,
        limit=limit,
    )
    return schemas.InventoryAvailabilityResponse.model_validate(payload)


@router.get(
    "/reservations",
    response_model=Page[schemas.InventoryReservationResponse],
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def list_inventory_reservations_endpoint(
    store_id: int | None = Query(default=None, ge=1),
    device_id: int | None = Query(default=None, ge=1),
    status_filter: models.InventoryState | None = Query(default=None),
    include_expired: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pagination: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> Page[schemas.InventoryReservationResponse]:
    crud.expire_reservations(
        db,
        store_id=store_id,
        device_ids=[device_id] if device_id is not None else None,
    )
    reservations = crud.list_inventory_reservations(
        db,
        store_id=store_id,
        device_id=device_id,
        status=status_filter,
        include_expired=include_expired,
    )
    page_offset = (
        pagination.offset if (pagination.page > 1 and offset == 0) else offset
    )
    page_size = min(pagination.size, limit)
    sliced = reservations[page_offset : page_offset + page_size]
    items = [
        schemas.InventoryReservationResponse.model_validate(record)
        for record in sliced
    ]
    return Page.from_items(
        items,
        page=pagination.page,
        size=page_size,
        total=len(reservations),
    )


@router.post(
    "/reservations",
    response_model=schemas.InventoryReservationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def create_inventory_reservation_endpoint(
    payload: schemas.InventoryReservationCreate,
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.InventoryReservationResponse:
    try:
        reservation = crud.create_reservation(
            db,
            store_id=payload.store_id,
            device_id=payload.device_id,
            quantity=payload.quantity,
            expires_at=payload.expires_at,
            reserved_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado"
        ) from exc
    except ValueError as exc:
        message = str(exc)
        if message in {"reservation_invalid_quantity", "reservation_invalid_expiration", "reservation_reason_required", "reservation_requires_single_unit"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=message,
            ) from exc
        if message in {"reservation_insufficient_stock", "reservation_device_unavailable"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc
        raise
    return schemas.InventoryReservationResponse.model_validate(reservation)


@router.put(
    "/reservations/{reservation_id}/renew",
    response_model=schemas.InventoryReservationResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def renew_inventory_reservation_endpoint(
    payload: schemas.InventoryReservationRenew,
    reservation_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.InventoryReservationResponse:
    try:
        reservation = crud.renew_reservation(
            db,
            reservation_id,
            expires_at=payload.expires_at,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada"
        ) from exc
    except ValueError as exc:
        message = str(exc)
        if message in {"reservation_not_active", "reservation_invalid_expiration", "reservation_reason_required"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT
                if message == "reservation_not_active"
                else status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=message,
            ) from exc
        raise
    return schemas.InventoryReservationResponse.model_validate(reservation)


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=schemas.InventoryReservationResponse,
    dependencies=[Depends(require_roles(*MOVEMENT_ROLES))],
)
def cancel_inventory_reservation_endpoint(
    reservation_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*MOVEMENT_ROLES)),
) -> schemas.InventoryReservationResponse:
    try:
        reservation = crud.release_reservation(
            db,
            reservation_id,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
            target_state=models.InventoryState.CANCELADO,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada"
        ) from exc
    except ValueError as exc:
        message = str(exc)
        if message in {"reservation_not_active", "reservation_invalid_transition"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc
        raise
    return schemas.InventoryReservationResponse.model_validate(reservation)


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
    items = [schemas.DeviceResponse.model_validate(
        device) for device in devices]
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Recurso no encontrado") from exc
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
        if str(exc) == "adjustment_insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stock insuficiente para registrar el ajuste solicitado.",
            ) from exc
        if str(exc) == "adjustment_device_already_sold":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El dispositivo ya fue vendido y no admite ajustes negativos.",
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Dispositivo no encontrado") from exc
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
                detail={"code": "device_not_found",
                        "message": "Dispositivo no encontrado"},
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
    estado_comercial: str | None = Query(default=None, max_length=10),
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Funcionalidad no disponible")
    try:
        filters = schemas.DeviceSearchFilters(
            imei=imei,
            serial=serial,
            capacidad_gb=capacidad_gb,
            color=color,
            marca=marca,
            modelo=modelo,
            categoria=categoria,
            condicion=condicion,
            estado_comercial=estado_comercial,
            estado=estado,
            ubicacion=ubicacion,
            proveedor=proveedor,
            fecha_ingreso_desde=fecha_ingreso_desde,
            fecha_ingreso_hasta=fecha_ingreso_hasta,
        )
    except ValidationError as exc:
        serialized_errors: list[dict[str, object]] = []
        for error in exc.errors():
            context = error.get("ctx")
            if isinstance(context, dict) and "error" in context:
                serialized_context = dict(context)
                if isinstance(serialized_context["error"], ValueError):
                    serialized_context["error"] = str(serialized_context["error"])
                serialized_errors.append({**error, "ctx": serialized_context})
            else:
                serialized_errors.append(error)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=serialized_errors) from exc
    if not any(
        [
            filters.imei,
            filters.serial,
            filters.color,
            filters.marca,
            filters.modelo,
            filters.categoria,
            filters.condicion,
            filters.estado_comercial is not None,
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
    results, total = inventory_search.advanced_catalog_search(
        db,
        filters=filters,
        limit=page_size,
        offset=page_offset,
        requested_by=current_user,
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
    stores = crud.list_inventory_summary(
        db, limit=page_size, offset=page_offset)
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


