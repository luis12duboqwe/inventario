"""Operaciones CRUD para el módulo de Inventario (Devices)."""
from __future__ import annotations

from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..core.transactions import flush_session, transactional_session
from .common import log_audit_event as _log_action, to_decimal
from .stores import recalculate_store_inventory_value
from .warehouses import ensure_default_warehouse


def _recalculate_sale_price(device: models.Device) -> None:
    base_cost = to_decimal(device.costo_unitario)
    margin = to_decimal(device.margen_porcentaje)
    sale_factor = Decimal("1") + (margin / Decimal("100"))
    recalculated = (
        base_cost * sale_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    device.unit_price = recalculated
    device.precio_venta = recalculated


def _device_sync_payload(device: models.Device) -> dict[str, Any]:
    """Construye el payload serializado de un dispositivo para sincronización."""

    commercial_state = getattr(
        device.estado_comercial, "value", device.estado_comercial)
    updated_at = getattr(device, "updated_at", None)
    store_name = device.store.name if getattr(device, "store", None) else None
    return {
        "id": device.id,
        "store_id": device.store_id,
        "store_name": store_name,
        "warehouse_id": device.warehouse_id,
        "warehouse_name": getattr(device.warehouse, "name", None),
        "sku": device.sku,
        "name": device.name,
        "quantity": device.quantity,
        "unit_price": float(to_decimal(device.unit_price)),
        "costo_unitario": float(to_decimal(device.costo_unitario)),
        "margen_porcentaje": float(to_decimal(device.margen_porcentaje)),
        "estado": device.estado,
        "estado_comercial": commercial_state,
        "minimum_stock": int(getattr(device, "minimum_stock", 0) or 0),
        "reorder_point": int(getattr(device, "reorder_point", 0) or 0),
        "imei": device.imei,
        "serial": device.serial,
        "marca": device.marca,
        "modelo": device.modelo,
        "color": device.color,
        "capacidad_gb": device.capacidad_gb,
        "garantia_meses": device.garantia_meses,
        "proveedor": device.proveedor,
        "lote": device.lote,
        "fecha_compra": device.fecha_compra.isoformat() if device.fecha_compra else None,
        "fecha_ingreso": device.fecha_ingreso.isoformat() if device.fecha_ingreso else None,
        "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else None,
    }


def create_device(
    db: Session,
    store_id: int,
    payload: schemas.DeviceCreate,
    *,
    performed_by_id: int | None = None
) -> models.Device:
    with transactional_session(db):
        # 1. Validar almacén
        warehouse_id = payload.warehouse_id
        if not warehouse_id:
            default_wh = ensure_default_warehouse(db, store_id)
            warehouse_id = default_wh.id

        # 2. Crear instancia
        device = models.Device(
            store_id=store_id,
            warehouse_id=warehouse_id,
            sku=payload.sku.strip().upper(),
            name=payload.name.strip(),
            descripcion=payload.descripcion,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            costo_unitario=payload.costo_unitario,
            margen_porcentaje=payload.margen_porcentaje,
            minimum_stock=payload.minimum_stock,
            reorder_point=payload.reorder_point,
            categoria=payload.categoria,
            estado=payload.estado,
            estado_comercial=payload.estado_comercial,
            imei=payload.imei,
            serial=payload.serial,
            marca=payload.marca,
            modelo=payload.modelo,
            color=payload.color,
            capacidad_gb=payload.capacidad_gb,
            capacidad=payload.capacidad,
            condicion=payload.condicion,
            ubicacion=payload.ubicacion,
            garantia_meses=payload.garantia_meses,
            proveedor=payload.proveedor,
            lote=payload.lote,
            fecha_compra=payload.fecha_compra,
            fecha_ingreso=payload.fecha_ingreso or datetime.now(timezone.utc),
            imagen_url=str(payload.imagen_url) if payload.imagen_url else None,
        )

        # 3. Calcular precios
        _recalculate_sale_price(device)

        db.add(device)
        try:
            flush_session(db)
        except IntegrityError as exc:
            # Manejo de duplicados
            msg = str(exc).lower()
            if "devices.sku" in msg or "unique constraint failed: devices.sku" in msg:
                raise ValueError("device_already_exists") from exc
            if "devices.imei" in msg or "unique constraint failed: devices.imei" in msg:
                raise ValueError("device_identifier_conflict") from exc
            if "devices.serial" in msg or "unique constraint failed: devices.serial" in msg:
                raise ValueError("device_identifier_conflict") from exc

            # Fallback for other DBs or generic messages if needed, but be careful not to catch everything as SKU
            if "sku" in msg and "unique" in msg:
                raise ValueError("device_already_exists") from exc

            raise ValueError("device_creation_failed") from exc

        # 4. Auditoría y Sincronización
        _log_action(
            db,
            action="device_created",
            entity_type="device",
            entity_id=str(device.id),
            performed_by_id=performed_by_id,
            details=_device_sync_payload(device),
        )

        # 5. Actualizar valor inventario tienda
        recalculate_store_inventory_value(db, store_id)

        db.refresh(device)
        return device


def get_device(db: Session, store_id: int, device_id: int) -> models.Device:
    stmt = select(models.Device).where(
        models.Device.id == device_id,
        models.Device.store_id == store_id,
        models.Device.is_deleted.is_(False)
    ).options(
        selectinload(models.Device.store),
        selectinload(models.Device.warehouse)
    )
    try:
        return db.scalars(stmt).one()
    except NoResultFound as exc:
        raise LookupError("device_not_found") from exc


def update_device(
    db: Session,
    store_id: int,
    device_id: int,
    payload: schemas.DeviceUpdate,
    *,
    performed_by_id: int | None = None
) -> models.Device:
    device = get_device(db, store_id, device_id)

    with transactional_session(db):
        # Detectar cambios
        changes: list[str] = []
        payload_dict = payload.model_dump(exclude_unset=True)

        for field, value in payload_dict.items():
            if field == "imagen_url" and value is not None:
                value = str(value)

            # Mapeo de campos especiales
            model_field = field
            if field == "description":
                model_field = "descripcion"

            if not hasattr(device, model_field):
                continue

            current_val = getattr(device, model_field)
            if current_val != value:
                setattr(device, model_field, value)
                changes.append(f"{field}: {current_val} -> {value}")

        # Recalcular si cambiaron costos
        if "costo_unitario" in payload_dict or "margen_porcentaje" in payload_dict:
            _recalculate_sale_price(device)
            changes.append("price_recalculated")

        if not changes:
            return device

        device.updated_at = datetime.now(timezone.utc)
        db.add(device)
        flush_session(db)

        # Auditoría
        details: dict[str, Any] = {
            "changes": changes,
            "snapshot": _device_sync_payload(device)
        }
        _log_action(
            db,
            action="device_updated",
            entity_type="device",
            entity_id=str(device.id),
            performed_by_id=performed_by_id,
            details=details
        )

        # Actualizar valor tienda
        recalculate_store_inventory_value(db, device.store_id)

        db.refresh(device)
        return device


def delete_device(
    db: Session,
    store_id: int,
    device_id: int,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None
) -> models.Device:
    device = get_device(db, store_id, device_id)

    with transactional_session(db):
        device.is_deleted = True
        device.deleted_at = datetime.now(timezone.utc)
        db.add(device)

        details: dict[str, Any] = {
            "reason": reason,
            "snapshot": _device_sync_payload(device)
        }

        _log_action(
            db,
            action="device_deleted",
            entity_type="device",
            entity_id=str(device.id),
            performed_by_id=performed_by_id,
            details=details
        )

        recalculate_store_inventory_value(db, device.store_id)

    return device


def list_devices(
    db: Session,
    store_id: int,
    *,
    offset: int = 0,
    limit: int | None = 50,
    search: str | None = None,
    categoria: str | None = None,
    low_stock: bool = False,
    estado: models.CommercialState | None = None,
    condicion: str | None = None,
    estado_inventario: str | None = None,
    ubicacion: str | None = None,
    proveedor: str | None = None,
    warehouse_id: int | None = None,
    fecha_ingreso_desde: date | None = None,
    fecha_ingreso_hasta: date | None = None,
) -> list[models.Device]:
    stmt = select(models.Device).where(
        models.Device.store_id == store_id,
        models.Device.is_deleted.is_(False)
    )

    if warehouse_id is not None:
        stmt = stmt.where(models.Device.warehouse_id == warehouse_id)

    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(
            models.Device.name.ilike(term),
            models.Device.sku.ilike(term),
            models.Device.imei.ilike(term),
            models.Device.serial.ilike(term),
            models.Device.marca.ilike(term),
            models.Device.modelo.ilike(term)
        ))

    if categoria:
        stmt = stmt.where(models.Device.categoria == categoria)

    if low_stock:
        stmt = stmt.where(models.Device.quantity <=
                          models.Device.minimum_stock)

    if estado:
        stmt = stmt.where(models.Device.estado_comercial == estado)

    if condicion:
        stmt = stmt.where(models.Device.condicion == condicion)

    if estado_inventario:
        stmt = stmt.where(models.Device.estado == estado_inventario)

    if ubicacion:
        stmt = stmt.where(models.Device.ubicacion.ilike(f"%{ubicacion}%"))

    if proveedor:
        stmt = stmt.where(models.Device.proveedor.ilike(f"%{proveedor}%"))

    if fecha_ingreso_desde:
        stmt = stmt.where(models.Device.fecha_ingreso >= fecha_ingreso_desde)

    if fecha_ingreso_hasta:
        stmt = stmt.where(models.Device.fecha_ingreso <= fecha_ingreso_hasta)

    stmt = stmt.order_by(models.Device.name)

    if limit is not None:
        stmt = stmt.offset(offset).limit(limit)

    return list(db.scalars(stmt))

def _ensure_unique_identifiers(
    db: Session,
    *,
    imei: str | None,
    serial: str | None,
    exclude_device_id: int | None = None,
) -> None:
    if imei:
        statement = select(models.Device).where(models.Device.imei == imei)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
            raise ValueError("device_identifier_conflict")
        identifier_statement = select(models.DeviceIdentifier).where(
            or_(
                models.DeviceIdentifier.imei_1 == imei,
                models.DeviceIdentifier.imei_2 == imei,
            )
        )
        if exclude_device_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.producto_id != exclude_device_id
            )
        if db.scalars(identifier_statement).first() is not None:
            raise ValueError("device_identifier_conflict")
    if serial:
        statement = select(models.Device).where(models.Device.serial == serial)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
            raise ValueError("device_identifier_conflict")
        identifier_statement = select(models.DeviceIdentifier).where(
            models.DeviceIdentifier.numero_serie == serial
        )
        if exclude_device_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.producto_id != exclude_device_id
            )
        if db.scalars(identifier_statement).first() is not None:
            raise ValueError("device_identifier_conflict")


def _validate_device_numeric_fields(values: dict[str, Any]) -> None:
    quantity = values.get("quantity")
    if quantity is not None:
        try:
            parsed_quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("device_invalid_quantity")
        if parsed_quantity < 0:
            raise ValueError("device_invalid_quantity")

    raw_cost = values.get("costo_unitario")
    if raw_cost is not None:
        try:
            parsed_cost = to_decimal(raw_cost)
        except (ArithmeticError, TypeError, ValueError):
            raise ValueError("device_invalid_cost")
        if parsed_cost < 0:
            raise ValueError("device_invalid_cost")


def _ensure_unique_identifier_payload(
    db: Session,
    *,
    imei_1: str | None,
    imei_2: str | None,
    numero_serie: str | None,
    exclude_device_id: int | None = None,
    exclude_identifier_id: int | None = None,
) -> None:
    imei_values = {value for value in (imei_1, imei_2) if value}
    for imei in imei_values:
        statement = select(models.Device).where(models.Device.imei == imei)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
            raise ValueError("device_identifier_conflict")

        identifier_statement = select(models.DeviceIdentifier).where(
            or_(
                models.DeviceIdentifier.imei_1 == imei,
                models.DeviceIdentifier.imei_2 == imei,
            )
        )
        if exclude_device_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.producto_id != exclude_device_id
            )
        if exclude_identifier_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.id != exclude_identifier_id
            )
        if db.scalars(identifier_statement).first() is not None:
            raise ValueError("device_identifier_conflict")

    if numero_serie:
        statement = select(models.Device).where(
            models.Device.serial == numero_serie)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
            raise ValueError("device_identifier_conflict")

        identifier_statement = select(models.DeviceIdentifier).where(
            models.DeviceIdentifier.numero_serie == numero_serie
        )
        if exclude_device_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.producto_id != exclude_device_id
            )
        if exclude_identifier_id:
            identifier_statement = identifier_statement.where(
                models.DeviceIdentifier.id != exclude_identifier_id
            )
        if db.scalars(identifier_statement).first() is not None:
            raise ValueError("device_identifier_conflict")
