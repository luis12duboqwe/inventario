"""Operaciones de base de datos para las entidades principales."""
from __future__ import annotations

import copy
import csv
import json
import math
import secrets
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from io import StringIO
from typing import Literal

from sqlalchemy import case, desc, func, or_, select, tuple_
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import ColumnElement

from . import models, schemas, telemetry
from .core.roles import ADMIN, GERENTE, INVITADO, OPERADOR
from .services.inventory import calculate_inventory_valuation
from .config import settings
from .utils import audit as audit_utils
from .utils.cache import TTLCache

DEFAULT_SECURITY_MODULES: list[str] = [
    "usuarios",
    "seguridad",
    "inventario",
    "ventas",
    "compras",
    "pos",
    "clientes",
    "proveedores",
    "reparaciones",
    "transferencias",
    "operaciones",
    "reportes",
    "auditoria",
    "sincronizacion",
    "respaldos",
    "tiendas",
    "actualizaciones",
]

_RESTRICTED_DELETE_FOR_MANAGER = {"seguridad", "respaldos", "usuarios", "actualizaciones"}
_RESTRICTED_EDIT_FOR_OPERATOR = {"seguridad", "respaldos", "usuarios", "actualizaciones", "auditoria"}
_RESTRICTED_DELETE_FOR_OPERATOR = _RESTRICTED_EDIT_FOR_OPERATOR | {"reportes", "sincronizacion"}

ROLE_MODULE_PERMISSION_MATRIX: dict[str, dict[str, dict[str, bool]]] = {
    ADMIN: {
        module: {"can_view": True, "can_edit": True, "can_delete": True}
        for module in DEFAULT_SECURITY_MODULES
    },
    GERENTE: {
        module: {
            "can_view": True,
            "can_edit": True,
            "can_delete": module not in _RESTRICTED_DELETE_FOR_MANAGER,
        }
        for module in DEFAULT_SECURITY_MODULES
    },
    OPERADOR: {
        module: {
            "can_view": True,
            "can_edit": module not in _RESTRICTED_EDIT_FOR_OPERATOR,
            "can_delete": module not in _RESTRICTED_DELETE_FOR_OPERATOR,
        }
        for module in DEFAULT_SECURITY_MODULES
    },
    INVITADO: {
        module: {
            "can_view": module
            in {"inventario", "reportes", "clientes", "proveedores", "ventas"},
            "can_edit": False,
            "can_delete": False,
        }
        for module in DEFAULT_SECURITY_MODULES
    },
}


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
        statement = select(models.Device).where(models.Device.serial == numero_serie)
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


def _to_decimal(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _normalize_date_range(
    date_from: date | datetime | None, date_to: date | datetime | None
) -> tuple[datetime, datetime]:
    now = datetime.utcnow()

    if isinstance(date_from, datetime):
        start_dt = date_from
        if start_dt.time() == datetime.min.time():
            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif isinstance(date_from, date):
        start_dt = datetime.combine(date_from, datetime.min.time())
    else:
        start_dt = now - timedelta(days=30)

    if isinstance(date_to, datetime):
        end_dt = date_to
        if end_dt.time() == datetime.min.time():
            end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif isinstance(date_to, date):
        end_dt = datetime.combine(date_to, datetime.max.time())
    else:
        end_dt = now

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    return start_dt, end_dt


_PERSISTENT_ALERTS_CACHE: TTLCache[list[dict[str, object]]] = TTLCache(ttl_seconds=60.0)


def _persistent_alerts_cache_key(
    *,
    threshold_minutes: int,
    min_occurrences: int,
    lookback_hours: int,
    limit: int,
) -> tuple[int, int, int, int]:
    return (threshold_minutes, min_occurrences, lookback_hours, limit)


def invalidate_persistent_audit_alerts_cache() -> None:
    """Limpia la cache en memoria de recordatorios críticos."""

    _PERSISTENT_ALERTS_CACHE.clear()


def _user_display_name(user: models.User | None) -> str | None:
    if user is None:
        return None
    if user.full_name and user.full_name.strip():
        return user.full_name.strip()
    if user.username and user.username.strip():
        return user.username.strip()
    return None


def _linear_regression(
    points: Sequence[tuple[float, float]]
) -> tuple[float, float, float]:
    if not points:
        return 0.0, 0.0, 0.0
    if len(points) == 1:
        return 0.0, points[0][1], 0.0

    n = float(len(points))
    sum_x = sum(point[0] for point in points)
    sum_y = sum(point[1] for point in points)
    sum_xy = sum(point[0] * point[1] for point in points)
    sum_xx = sum(point[0] ** 2 for point in points)
    sum_yy = sum(point[1] ** 2 for point in points)

    denominator = (n * sum_xx) - (sum_x**2)
    if math.isclose(denominator, 0.0):
        slope = 0.0
    else:
        slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator

    intercept = (sum_y - (slope * sum_x)) / n

    denominator_r = (n * sum_yy) - (sum_y**2)
    if denominator <= 0 or denominator_r <= 0:
        r_squared = 0.0
    else:
        r_squared = ((n * sum_xy) - (sum_x * sum_y)) ** 2 / (denominator * denominator_r)

    return slope, intercept, r_squared


def _project_linear_sum(
    slope: float, intercept: float, start_index: int, horizon: int
) -> float:
    total = 0.0
    for offset in range(horizon):
        x_value = float(start_index + offset)
        estimate = slope * x_value + intercept
        total += max(0.0, estimate)
    return total


_OUTBOX_PRIORITY_MAP: dict[str, models.SyncOutboxPriority] = {
    "sale": models.SyncOutboxPriority.HIGH,
    "transfer_order": models.SyncOutboxPriority.HIGH,
    "purchase_order": models.SyncOutboxPriority.NORMAL,
    "repair_order": models.SyncOutboxPriority.NORMAL,
    "customer": models.SyncOutboxPriority.NORMAL,
    "customer_ledger_entry": models.SyncOutboxPriority.NORMAL,
    "pos_config": models.SyncOutboxPriority.NORMAL,
    "supplier": models.SyncOutboxPriority.NORMAL,
    "cash_session": models.SyncOutboxPriority.NORMAL,
    "device": models.SyncOutboxPriority.NORMAL,
    "inventory": models.SyncOutboxPriority.NORMAL,
    "store": models.SyncOutboxPriority.LOW,
    "global": models.SyncOutboxPriority.LOW,
    "backup": models.SyncOutboxPriority.LOW,
    "pos_draft": models.SyncOutboxPriority.LOW,
}

_OUTBOX_PRIORITY_ORDER: dict[models.SyncOutboxPriority, int] = {
    models.SyncOutboxPriority.HIGH: 0,
    models.SyncOutboxPriority.NORMAL: 1,
    models.SyncOutboxPriority.LOW: 2,
}

_SYSTEM_MODULE_MAP: dict[str, str] = {
    "sale": "ventas",
    "pos": "ventas",
    "purchase": "compras",
    "inventory": "inventario",
    "device": "inventario",
    "supplier_batch": "inventario",
    "inventory_adjustment": "ajustes",
    "adjustment": "ajustes",
    "backup": "respaldos",
    "user": "usuarios",
    "role": "usuarios",
    "auth": "usuarios",
    "store": "inventario",
    "customer": "clientes",
    "supplier": "proveedores",
    "transfer_order": "inventario",
    "purchase_order": "compras",
    "purchase_vendor": "compras",
    "cash_session": "ventas",
}


def _resolve_outbox_priority(entity_type: str, priority: models.SyncOutboxPriority | None) -> models.SyncOutboxPriority:
    if priority is not None:
        return priority
    return _OUTBOX_PRIORITY_MAP.get(entity_type, models.SyncOutboxPriority.NORMAL)


def _priority_weight(priority: models.SyncOutboxPriority | None) -> int:
    if priority is None:
        return _OUTBOX_PRIORITY_ORDER[models.SyncOutboxPriority.NORMAL]
    return _OUTBOX_PRIORITY_ORDER.get(priority, 1)


def _resolve_system_module(entity_type: str) -> str:
    normalized = (entity_type or "").lower()
    for prefix, module in sorted(
        _SYSTEM_MODULE_MAP.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if normalized.startswith(prefix):
            return module
    return "general"


def _map_system_level(action: str, details: str | None) -> models.SystemLogLevel:
    severity = audit_utils.classify_severity(action or "", details)
    if severity == "critical":
        return models.SystemLogLevel.CRITICAL
    if severity == "warning":
        return models.SystemLogLevel.WARNING
    return models.SystemLogLevel.INFO


def _create_system_log(
    db: Session,
    *,
    audit_log: models.AuditLog | None,
    usuario: str | None,
    module: str,
    action: str,
    description: str,
    level: models.SystemLogLevel,
    ip_address: str | None = None,
) -> models.SystemLog:
    normalized_module = (module or "general").lower()
    entry = models.SystemLog(
        usuario=usuario,
        modulo=normalized_module,
        accion=action,
        descripcion=description,
        fecha=datetime.utcnow(),
        nivel=level,
        ip_origen=ip_address,
        audit_log=audit_log,
    )
    db.add(entry)
    db.flush()
    return entry


def _recalculate_sale_price(device: models.Device) -> None:
    base_cost = _to_decimal(device.costo_unitario)
    margin = _to_decimal(device.margen_porcentaje)
    sale_factor = Decimal("1") + (margin / Decimal("100"))
    recalculated = (base_cost * sale_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    device.unit_price = recalculated
    device.precio_venta = recalculated


def _normalize_store_ids(store_ids: Iterable[int] | None) -> set[int] | None:
    if not store_ids:
        return None
    normalized = {int(store_id) for store_id in store_ids if int(store_id) > 0}
    return normalized or None


def _log_action(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    performed_by_id: int | None,
    details: str | None = None,
) -> models.AuditLog:
    log = models.AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by_id=performed_by_id,
        details=details,
    )
    db.add(log)
    db.flush()
    usuario = None
    if performed_by_id is not None:
        user = db.get(models.User, performed_by_id)
        if user is not None:
            usuario = user.username
    module = _resolve_system_module(entity_type)
    description = details or f"{action} sobre {entity_type} {entity_id}"
    level = _map_system_level(action, details)
    _create_system_log(
        db,
        audit_log=log,
        usuario=usuario,
        module=module,
        action=action,
        description=description,
        level=level,
    )
    invalidate_persistent_audit_alerts_cache()
    return log


def register_system_error(
    db: Session,
    *,
    mensaje: str,
    stack_trace: str | None,
    modulo: str,
    usuario: str | None,
    ip_origen: str | None = None,
) -> models.SystemError:
    normalized_module = (modulo or "general").lower()
    error = models.SystemError(
        mensaje=mensaje,
        stack_trace=stack_trace,
        modulo=normalized_module,
        fecha=datetime.utcnow(),
        usuario=usuario,
    )
    db.add(error)
    db.flush()
    _create_system_log(
        db,
        audit_log=None,
        usuario=usuario,
        module=normalized_module,
        action="system_error",
        description=mensaje,
        level=models.SystemLogLevel.ERROR,
        ip_address=ip_origen,
    )
    return error


def list_system_logs(
    db: Session,
    *,
    usuario: str | None = None,
    modulo: str | None = None,
    nivel: models.SystemLogLevel | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[models.SystemLog]:
    statement = select(models.SystemLog).order_by(models.SystemLog.fecha.desc())
    if usuario:
        statement = statement.where(models.SystemLog.usuario == usuario)
    if modulo:
        statement = statement.where(models.SystemLog.modulo == modulo.lower())
    if nivel:
        statement = statement.where(models.SystemLog.nivel == nivel)
    if date_from:
        statement = statement.where(models.SystemLog.fecha >= date_from)
    if date_to:
        statement = statement.where(models.SystemLog.fecha <= date_to)
    return list(db.scalars(statement).all())


def list_system_errors(
    db: Session,
    *,
    usuario: str | None = None,
    modulo: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[models.SystemError]:
    statement = select(models.SystemError).order_by(models.SystemError.fecha.desc())
    if usuario:
        statement = statement.where(models.SystemError.usuario == usuario)
    if modulo:
        statement = statement.where(models.SystemError.modulo == modulo.lower())
    if date_from:
        statement = statement.where(models.SystemError.fecha >= date_from)
    if date_to:
        statement = statement.where(models.SystemError.fecha <= date_to)
    return list(db.scalars(statement).all())


def _device_value(device: models.Device) -> Decimal:
    return Decimal(device.quantity) * (device.unit_price or Decimal("0"))


def _movement_value(movement: models.InventoryMovement) -> Decimal:
    """Calcula el valor monetario estimado de un movimiento."""

    unit_cost: Decimal | None = movement.unit_cost
    if unit_cost is None and movement.device is not None:
        if getattr(movement.device, "costo_unitario", None):
            unit_cost = movement.device.costo_unitario
        elif movement.device.unit_price is not None:
            unit_cost = movement.device.unit_price
    base_cost = _to_decimal(unit_cost)
    return (Decimal(movement.quantity) * base_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _recalculate_store_inventory_value(
    db: Session, store: models.Store | int
) -> Decimal:
    if isinstance(store, models.Store):
        store_obj = store
    else:
        store_obj = get_store(db, int(store))
    db.flush()
    total_value = db.scalar(
        select(func.coalesce(func.sum(models.Device.quantity * models.Device.unit_price), 0))
        .where(models.Device.store_id == store_obj.id)
    )
    normalized_total = _to_decimal(total_value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    store_obj.inventory_value = normalized_total
    db.add(store_obj)
    db.flush()
    return normalized_total


def _device_category_expr() -> ColumnElement[str]:
    return func.coalesce(
        func.nullif(models.Device.modelo, ""),
        func.nullif(models.Device.sku, ""),
        func.nullif(models.Device.name, ""),
    )


def _customer_payload(customer: models.Customer) -> dict[str, object]:
    return {
        "id": customer.id,
        "name": customer.name,
        "contact_name": customer.contact_name,
        "email": customer.email,
        "phone": customer.phone,
        "customer_type": customer.customer_type,
        "status": customer.status,
        "credit_limit": float(customer.credit_limit or Decimal("0")),
        "outstanding_debt": float(customer.outstanding_debt or Decimal("0")),
        "last_interaction_at": customer.last_interaction_at.isoformat() if customer.last_interaction_at else None,
        "updated_at": customer.updated_at.isoformat(),
    }


def _device_sync_payload(device: models.Device) -> dict[str, object]:
    """Construye el payload serializado de un dispositivo para sincronización."""

    commercial_state = getattr(device.estado_comercial, "value", device.estado_comercial)
    updated_at = getattr(device, "updated_at", None)
    store_name = device.store.name if getattr(device, "store", None) else None
    return {
        "id": device.id,
        "store_id": device.store_id,
        "store_name": store_name,
        "sku": device.sku,
        "name": device.name,
        "quantity": device.quantity,
        "unit_price": float(_to_decimal(device.unit_price)),
        "costo_unitario": float(_to_decimal(device.costo_unitario)),
        "margen_porcentaje": float(_to_decimal(device.margen_porcentaje)),
        "estado": device.estado,
        "estado_comercial": commercial_state,
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


def _inventory_movement_payload(movement: models.InventoryMovement) -> dict[str, object]:
    """Genera el payload de sincronización para un movimiento de inventario."""

    store_name = movement.store.name if movement.store else None
    source_name = movement.source_store.name if movement.source_store else None
    device = movement.device
    performed_by = _user_display_name(movement.performed_by)
    created_at = movement.created_at.isoformat() if movement.created_at else None
    return {
        "id": movement.id,
        "store_id": movement.store_id,
        "store_name": store_name,
        "source_store_id": movement.source_store_id,
        "source_store_name": source_name,
        "device_id": movement.device_id,
        "device_sku": device.sku if device else None,
        "movement_type": movement.movement_type.value,
        "quantity": movement.quantity,
        "comment": movement.comment,
        "unit_cost": float(_to_decimal(movement.unit_cost)) if movement.unit_cost is not None else None,
        "performed_by_id": movement.performed_by_id,
        "performed_by_name": performed_by,
        "created_at": created_at,
    }


def _purchase_order_payload(order: models.PurchaseOrder) -> dict[str, object]:
    """Serializa una orden de compra para la cola de sincronización."""

    store_name = order.store.name if getattr(order, "store", None) else None
    status_value = getattr(order.status, "value", order.status)
    items_payload = [
        {
            "device_id": item.device_id,
            "quantity_ordered": item.quantity_ordered,
            "quantity_received": item.quantity_received,
            "unit_cost": float(_to_decimal(item.unit_cost)),
        }
        for item in order.items
    ]
    return {
        "id": order.id,
        "store_id": order.store_id,
        "store_name": store_name,
        "supplier": order.supplier,
        "status": status_value,
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "closed_at": order.closed_at.isoformat() if order.closed_at else None,
        "items": items_payload,
    }


def _repair_payload(order: models.RepairOrder) -> dict[str, object]:
    return {
        "id": order.id,
        "store_id": order.store_id,
        "status": order.status.value,
        "technician_name": order.technician_name,
        "customer_id": order.customer_id,
        "customer_name": order.customer_name,
        "labor_cost": float(order.labor_cost),
        "parts_cost": float(order.parts_cost),
        "total_cost": float(order.total_cost),
        "updated_at": order.updated_at.isoformat(),
    }


def _pos_config_payload(config: models.POSConfig) -> dict[str, object]:
    return {
        "store_id": config.store_id,
        "tax_rate": float(config.tax_rate),
        "invoice_prefix": config.invoice_prefix,
        "printer_name": config.printer_name,
        "printer_profile": config.printer_profile,
        "quick_product_ids": config.quick_product_ids,
        "updated_at": config.updated_at.isoformat(),
    }


def _pos_draft_payload(draft: models.POSDraftSale) -> dict[str, object]:
    return {
        "id": draft.id,
        "store_id": draft.store_id,
        "payload": draft.payload,
        "updated_at": draft.updated_at.isoformat(),
    }


def _history_to_json(
    entries: list[schemas.ContactHistoryEntry] | list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    if not entries:
        return normalized
    for entry in entries:
        if isinstance(entry, schemas.ContactHistoryEntry):
            timestamp = entry.timestamp
            note = entry.note
        else:
            timestamp = entry.get("timestamp")  # type: ignore[assignment]
            note = entry.get("note") if isinstance(entry, dict) else None
        if isinstance(timestamp, str):
            parsed_timestamp = timestamp
        elif isinstance(timestamp, datetime):
            parsed_timestamp = timestamp.isoformat()
        else:
            parsed_timestamp = datetime.utcnow().isoformat()
        normalized.append({"timestamp": parsed_timestamp, "note": (note or "").strip()})
    return normalized


def _last_history_timestamp(history: list[dict[str, object]]) -> datetime | None:
    timestamps = []
    for entry in history:
        raw_timestamp = entry.get("timestamp")
        if isinstance(raw_timestamp, datetime):
            timestamps.append(raw_timestamp)
        elif isinstance(raw_timestamp, str):
            try:
                timestamps.append(datetime.fromisoformat(raw_timestamp))
            except ValueError:
                continue
    if not timestamps:
        return None
    return max(timestamps)


def _append_customer_history(customer: models.Customer, note: str) -> None:
    history = list(customer.history or [])
    history.append({"timestamp": datetime.utcnow().isoformat(), "note": note})
    customer.history = history
    customer.last_interaction_at = datetime.utcnow()


_ALLOWED_CUSTOMER_STATUSES = {"activo", "inactivo", "moroso", "vip", "bloqueado"}
_ALLOWED_CUSTOMER_TYPES = {"minorista", "mayorista", "corporativo"}


def _normalize_customer_status(value: str | None) -> str:
    normalized = (value or "activo").strip().lower()
    if normalized not in _ALLOWED_CUSTOMER_STATUSES:
        raise ValueError("invalid_customer_status")
    return normalized


def _normalize_customer_type(value: str | None) -> str:
    normalized = (value or "minorista").strip().lower()
    if normalized not in _ALLOWED_CUSTOMER_TYPES:
        raise ValueError("invalid_customer_type")
    return normalized


def _ensure_non_negative_decimal(value: Decimal, error_code: str) -> Decimal:
    normalized = _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if normalized < Decimal("0"):
        raise ValueError(error_code)
    return normalized


def _ensure_debt_respects_limit(credit_limit: Decimal, outstanding: Decimal) -> None:
    """Valida que el saldo pendiente no supere el límite de crédito configurado."""

    normalized_limit = _to_decimal(credit_limit).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    normalized_outstanding = _to_decimal(outstanding).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if normalized_outstanding <= Decimal("0"):
        return
    if normalized_limit <= Decimal("0"):
        raise ValueError("customer_outstanding_exceeds_limit")
    if normalized_outstanding > normalized_limit:
        raise ValueError("customer_outstanding_exceeds_limit")


def _validate_customer_credit(customer: models.Customer, pending_charge: Decimal) -> None:
    amount = _to_decimal(pending_charge)
    if amount <= Decimal("0"):
        return
    limit = _to_decimal(customer.credit_limit)
    if limit <= Decimal("0"):
        raise ValueError("customer_credit_limit_exceeded")
    projected = (_to_decimal(customer.outstanding_debt) + amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if projected > limit:
        raise ValueError("customer_credit_limit_exceeded")


def _customer_ledger_payload(entry: models.CustomerLedgerEntry) -> dict[str, object]:
    return {
        "id": entry.id,
        "customer_id": entry.customer_id,
        "entry_type": entry.entry_type.value,
        "reference_type": entry.reference_type,
        "reference_id": entry.reference_id,
        "amount": float(entry.amount),
        "balance_after": float(entry.balance_after),
        "note": entry.note,
        "details": entry.details,
        "created_at": entry.created_at.isoformat(),
        "created_by_id": entry.created_by_id,
    }


def _create_customer_ledger_entry(
    db: Session,
    *,
    customer: models.Customer,
    entry_type: models.CustomerLedgerEntryType,
    amount: Decimal,
    note: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    details: dict[str, object] | None = None,
    created_by_id: int | None = None,
) -> models.CustomerLedgerEntry:
    entry = models.CustomerLedgerEntry(
        customer_id=customer.id,
        entry_type=entry_type,
        reference_type=reference_type,
        reference_id=reference_id,
        amount=_to_decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        balance_after=_to_decimal(customer.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        note=note,
        details=details or {},
        created_by_id=created_by_id,
    )
    db.add(entry)
    db.flush()
    return entry


def _sync_customer_ledger_entry(db: Session, entry: models.CustomerLedgerEntry) -> None:
    db.refresh(entry)
    db.refresh(entry, attribute_names=["created_by"])
    enqueue_sync_outbox(
        db,
        entity_type="customer_ledger_entry",
        entity_id=str(entry.id),
        operation="UPSERT",
        payload=_customer_ledger_payload(entry),
    )


def _resolve_part_unit_cost(device: models.Device, provided: Decimal | float | int | None) -> Decimal:
    candidate = _to_decimal(provided)
    if candidate <= Decimal("0"):
        if device.costo_unitario and device.costo_unitario > 0:
            candidate = _to_decimal(device.costo_unitario)
        else:
            candidate = _to_decimal(device.unit_price)
    return candidate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def list_audit_logs(
    db: Session,
    *,
    limit: int = 100,
    action: str | None = None,
    entity_type: str | None = None,
    performed_by_id: int | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
) -> list[models.AuditLog]:
    statement = (
        select(models.AuditLog)
        .order_by(models.AuditLog.created_at.desc())
        .limit(limit)
    )
    if action:
        statement = statement.where(models.AuditLog.action == action)
    if entity_type:
        statement = statement.where(models.AuditLog.entity_type == entity_type)
    if performed_by_id is not None:
        statement = statement.where(models.AuditLog.performed_by_id == performed_by_id)
    if date_from is not None or date_to is not None:
        start_dt, end_dt = _normalize_date_range(date_from, date_to)
        statement = statement.where(
            models.AuditLog.created_at >= start_dt, models.AuditLog.created_at <= end_dt
        )
    return list(db.scalars(statement).unique())


class AuditAcknowledgementError(Exception):
    """Errores relacionados con el registro de acuses manuales."""


class AuditAcknowledgementConflict(AuditAcknowledgementError):
    """Se intenta registrar un acuse cuando ya existe uno vigente."""


class AuditAcknowledgementNotFound(AuditAcknowledgementError):
    """No existen alertas críticas asociadas a la entidad solicitada."""


def get_audit_acknowledgements_map(
    db: Session,
    *,
    entities: Iterable[tuple[str, str]],
) -> dict[tuple[str, str], models.AuditAlertAcknowledgement]:
    """Obtiene los acuses existentes para las entidades provistas."""

    normalized: set[tuple[str, str]] = set()
    for entity_type, entity_id in entities:
        normalized_type = (entity_type or "").strip()
        normalized_id = (entity_id or "").strip()
        if not normalized_type or not normalized_id:
            continue
        normalized.add((normalized_type, normalized_id))

    if not normalized:
        return {}

    statement = (
        select(models.AuditAlertAcknowledgement)
        .options(joinedload(models.AuditAlertAcknowledgement.acknowledged_by))
        .where(
            tuple_(
                models.AuditAlertAcknowledgement.entity_type,
                models.AuditAlertAcknowledgement.entity_id,
            ).in_(normalized)
        )
    )
    return {
        (ack.entity_type, ack.entity_id): ack
        for ack in db.scalars(statement)
    }


def export_audit_logs_csv(
    db: Session,
    *,
    limit: int = 1000,
    action: str | None = None,
    entity_type: str | None = None,
    performed_by_id: int | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
) -> str:
    logs = list_audit_logs(
        db,
        limit=limit,
        action=action,
        entity_type=entity_type,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
    )
    buffer = StringIO()
    acknowledgements = get_audit_acknowledgements_map(
        db,
        entities={(log.entity_type, log.entity_id) for log in logs},
    )
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ID",
            "Acción",
            "Tipo de entidad",
            "ID de entidad",
            "Detalle",
            "Usuario responsable",
            "Fecha de creación",
            "Estado alerta",
            "Acuse registrado",
            "Nota de acuse",
        ]
    )
    for log in logs:
        key = (log.entity_type, log.entity_id)
        acknowledgement = acknowledgements.get(key)
        status = "Pendiente"
        acknowledgement_text = ""
        acknowledgement_note = ""
        if acknowledgement and acknowledgement.acknowledged_at >= log.created_at:
            display_name = _user_display_name(acknowledgement.acknowledged_by)
            status = "Atendida"
            acknowledgement_text = acknowledgement.acknowledged_at.strftime("%Y-%m-%dT%H:%M:%S")
            if display_name:
                acknowledgement_text += f" · {display_name}"
            acknowledgement_note = acknowledgement.note or ""
        writer.writerow(
            [
                log.id,
                log.action,
                log.entity_type,
                log.entity_id,
                log.details or "",
                log.performed_by_id or "",
                log.created_at.isoformat(),
                status,
                acknowledgement_text,
                acknowledgement_note,
            ]
        )
    return buffer.getvalue()


def acknowledge_audit_alert(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    acknowledged_by_id: int | None,
    note: str | None = None,
) -> models.AuditAlertAcknowledgement:
    """Registra o actualiza el acuse manual de una alerta crítica."""

    normalized_type = entity_type.strip()
    normalized_id = entity_id.strip()
    if not normalized_type or not normalized_id:
        raise ValueError("entity identifiers must be provided")

    recent_logs_stmt = (
        select(models.AuditLog)
        .where(models.AuditLog.entity_type == normalized_type)
        .where(models.AuditLog.entity_id == normalized_id)
        .order_by(models.AuditLog.created_at.desc())
        .limit(200)
    )
    recent_logs = list(db.scalars(recent_logs_stmt))
    last_critical: models.AuditLog | None = None
    for item in recent_logs:
        severity = audit_utils.classify_severity(item.action or "", item.details)
        if severity == "critical":
            last_critical = item
            break

    if last_critical is None:
        telemetry.record_audit_acknowledgement_failure(
            normalized_type, "not_found"
        )
        raise AuditAcknowledgementNotFound(
            "No existen alertas críticas registradas para la entidad indicada."
        )

    statement = (
        select(models.AuditAlertAcknowledgement)
        .where(models.AuditAlertAcknowledgement.entity_type == normalized_type)
        .where(models.AuditAlertAcknowledgement.entity_id == normalized_id)
    )
    acknowledgement = db.scalars(statement).first()
    now = datetime.utcnow()

    if (
        acknowledgement is not None
        and acknowledgement.acknowledged_at >= last_critical.created_at
    ):
        telemetry.record_audit_acknowledgement_failure(
            normalized_type, "already_acknowledged"
        )
        raise AuditAcknowledgementConflict(
            "La alerta ya fue atendida después del último evento crítico registrado."
        )

    event = "created"
    if acknowledgement is None:
        acknowledgement = models.AuditAlertAcknowledgement(
            entity_type=normalized_type,
            entity_id=normalized_id,
            acknowledged_by_id=acknowledged_by_id,
            acknowledged_at=now,
            note=note,
        )
        db.add(acknowledgement)
    else:
        event = "updated"
        acknowledgement.acknowledged_at = now
        acknowledgement.acknowledged_by_id = acknowledged_by_id
        acknowledgement.note = note

    db.add(
        models.AuditLog(
            action="audit_alert_acknowledged",
            entity_type=normalized_type,
            entity_id=normalized_id,
            details=(
                f"Resolución manual registrada: {note}" if note else "Resolución manual registrada"
            ),
            performed_by_id=acknowledged_by_id,
        )
    )

    db.commit()
    invalidate_persistent_audit_alerts_cache()
    db.refresh(acknowledgement)
    telemetry.record_audit_acknowledgement(normalized_type, event)
    return acknowledgement


def get_persistent_audit_alerts(
    db: Session,
    *,
    threshold_minutes: int = 15,
    min_occurrences: int = 1,
    lookback_hours: int = 48,
    limit: int = 10,
) -> list[dict[str, object]]:
    """Obtiene alertas críticas persistentes para recordatorios automáticos."""

    if threshold_minutes < 0:
        raise ValueError("threshold_minutes must be non-negative")
    if min_occurrences < 1:
        raise ValueError("min_occurrences must be >= 1")
    if lookback_hours < 1:
        raise ValueError("lookback_hours must be >= 1")
    if limit < 1:
        raise ValueError("limit must be >= 1")

    cache_key = _persistent_alerts_cache_key(
        threshold_minutes=threshold_minutes,
        min_occurrences=min_occurrences,
        lookback_hours=lookback_hours,
        limit=limit,
    )
    cached = _PERSISTENT_ALERTS_CACHE.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)

    now = datetime.utcnow()
    lookback_start = now - timedelta(hours=lookback_hours)

    statement = (
        select(models.AuditLog)
        .where(models.AuditLog.created_at >= lookback_start)
        .order_by(models.AuditLog.created_at.asc())
    )
    logs = list(db.scalars(statement))

    persistent_alerts = audit_utils.identify_persistent_critical_alerts(
        logs,
        threshold_minutes=threshold_minutes,
        min_occurrences=min_occurrences,
        limit=limit,
        reference_time=now,
    )

    keys = {(alert["entity_type"], alert["entity_id"]) for alert in persistent_alerts}
    acknowledgements: dict[tuple[str, str], models.AuditAlertAcknowledgement] = {}
    if keys:
        ack_stmt = (
            select(models.AuditAlertAcknowledgement)
            .options(joinedload(models.AuditAlertAcknowledgement.acknowledged_by))
            .where(
                tuple_(
                    models.AuditAlertAcknowledgement.entity_type,
                    models.AuditAlertAcknowledgement.entity_id,
                ).in_(keys)
            )
        )
        acknowledgements = {
            (ack.entity_type, ack.entity_id): ack for ack in db.scalars(ack_stmt)
        }

    enriched: list[dict[str, object]] = []
    for alert in persistent_alerts:
        key = (alert["entity_type"], alert["entity_id"])
        acknowledgement = acknowledgements.get(key)
        status = "pending"
        acknowledged_at = None
        acknowledged_by_id = None
        acknowledged_by_name = None
        acknowledged_note = None
        if acknowledgement and acknowledgement.acknowledged_at >= alert["last_seen"]:
            status = "acknowledged"
            acknowledged_at = acknowledgement.acknowledged_at
            acknowledged_by_id = acknowledgement.acknowledged_by_id
            if acknowledgement.acknowledged_by is not None:
                acknowledged_by_name = (
                    acknowledgement.acknowledged_by.full_name
                    or acknowledgement.acknowledged_by.username
                )
            acknowledged_note = acknowledgement.note

        enriched.append(
            {
                "entity_type": alert["entity_type"],
                "entity_id": alert["entity_id"],
                "first_seen": alert["first_seen"],
                "last_seen": alert["last_seen"],
                "occurrences": alert["occurrences"],
                "latest_action": alert["latest_action"],
                "latest_details": alert["latest_details"],
                "status": status,
                "acknowledged_at": acknowledged_at,
                "acknowledged_by_id": acknowledged_by_id,
                "acknowledged_by_name": acknowledged_by_name,
                "acknowledged_note": acknowledged_note,
            }
        )

    _PERSISTENT_ALERTS_CACHE.set(cache_key, copy.deepcopy(enriched))
    return enriched


def ensure_role_permissions(db: Session, role_name: str) -> None:
    defaults = ROLE_MODULE_PERMISSION_MATRIX.get(role_name)
    if not defaults:
        return
    for module, flags in defaults.items():
        statement = (
            select(models.Permission)
            .where(models.Permission.role_name == role_name)
            .where(models.Permission.module == module)
        )
        permission = db.scalars(statement).first()
        if permission is None:
            permission = models.Permission(role_name=role_name, module=module)
            permission.can_view = bool(flags.get("can_view", False))
            permission.can_edit = bool(flags.get("can_edit", False))
            permission.can_delete = bool(flags.get("can_delete", False))
            db.add(permission)
        else:
            if permission.can_view is None:
                permission.can_view = bool(flags.get("can_view", False))
            if permission.can_edit is None:
                permission.can_edit = bool(flags.get("can_edit", False))
            if permission.can_delete is None:
                permission.can_delete = bool(flags.get("can_delete", False))
    db.flush()


def ensure_role(db: Session, name: str) -> models.Role:
    statement = select(models.Role).where(models.Role.name == name)
    role = db.scalars(statement).first()
    if role is None:
        role = models.Role(name=name)
        db.add(role)
        db.flush()
    ensure_role_permissions(db, name)
    return role


def list_roles(db: Session) -> list[models.Role]:
    statement = select(models.Role).order_by(models.Role.name.asc())
    return list(db.scalars(statement).unique())


def user_has_module_permission(
    db: Session, user: models.User, module: str, action: Literal["view", "edit", "delete"]
) -> bool:
    normalized_module = module.strip().lower()
    if not normalized_module:
        return False
    roles = {assignment.role.name for assignment in user.roles}
    roles.add(user.rol)
    if ADMIN in roles:
        return True
    field_name = {
        "view": "can_view",
        "edit": "can_edit",
        "delete": "can_delete",
    }[action]
    statement = (
        select(models.Permission)
        .where(models.Permission.role_name.in_(roles))
        .where(models.Permission.module == normalized_module)
    )
    for permission in db.scalars(statement):
        if bool(getattr(permission, field_name)):
            return True
    return False


def get_user_by_username(db: Session, username: str) -> models.User | None:
    statement = (
        select(models.User)
        .options(
            joinedload(models.User.roles).joinedload(models.UserRole.role),
            joinedload(models.User.store),
        )
        .where(models.User.username == username)
    )
    return db.scalars(statement).first()


def get_user(db: Session, user_id: int) -> models.User:
    statement = (
        select(models.User)
        .options(
            joinedload(models.User.roles).joinedload(models.UserRole.role),
            joinedload(models.User.store),
        )
        .where(models.User.id == user_id)
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("user_not_found") from exc


ROLE_PRIORITY: dict[str, int] = {
    ADMIN: 0,
    GERENTE: 1,
    OPERADOR: 2,
    INVITADO: 3,
}


def _select_primary_role(role_names: Iterable[str]) -> str:
    """Determina el rol primario a persistir en la tabla de usuarios."""

    ordered_roles = [role for role in role_names if role in ROLE_PRIORITY]
    if not ordered_roles:
        return OPERADOR
    return min(ordered_roles, key=ROLE_PRIORITY.__getitem__)


def create_user(
    db: Session,
    payload: schemas.UserCreate,
    *,
    password_hash: str,
    role_names: Iterable[str],
) -> models.User:
    role_names = list(role_names)
    store_id: int | None = None
    if payload.store_id is not None:
        try:
            store = get_store(db, payload.store_id)
        except LookupError as exc:
            raise ValueError("store_not_found") from exc
        store_id = store.id
    primary_role = _select_primary_role(role_names)
    user = models.User(
        username=payload.username,
        full_name=payload.full_name,
        telefono=payload.telefono,
        rol=primary_role,
        estado="ACTIVO",
        password_hash=password_hash,
        store_id=store_id,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("user_already_exists") from exc

    assigned_roles: list[models.UserRole] = []
    for role_name in role_names:
        role = ensure_role(db, role_name)
        assigned_roles.append(models.UserRole(user=user, role=role))
    if assigned_roles:
        db.add_all(assigned_roles)

    _log_action(
        db,
        action="user_created",
        entity_type="user",
        entity_id=str(user.id),
        performed_by_id=None,
    )

    db.commit()
    db.refresh(user)
    return user


def list_users(
    db: Session,
    *,
    search: str | None = None,
    role: str | None = None,
    status: Literal["all", "active", "inactive", "locked"] = "all",
    store_id: int | None = None,
) -> list[models.User]:
    statement = (
        select(models.User)
        .options(
            joinedload(models.User.roles).joinedload(models.UserRole.role),
            joinedload(models.User.store),
        )
        .order_by(models.User.username.asc())
    )

    if search:
        normalized = f"%{search.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.User.username).like(normalized),
                func.lower(models.User.full_name).like(normalized),
            )
        )

    if role:
        normalized_role = role.strip().upper()
        statement = statement.where(
            or_(
                func.upper(models.User.rol) == normalized_role,
                models.User.roles.any(
                    models.UserRole.role.has(
                        func.upper(models.Role.name) == normalized_role
                    )
                ),
            )
        )

    status_normalized = (status or "all").lower()
    if status_normalized == "active":
        statement = statement.where(models.User.is_active.is_(True))
    elif status_normalized == "inactive":
        statement = statement.where(models.User.is_active.is_(False))

    if store_id is not None:
        statement = statement.where(models.User.store_id == store_id)

    users = list(db.scalars(statement).unique())
    if status_normalized == "locked":
        return [user for user in users if _user_is_locked(user)]
    return users


def set_user_roles(
    db: Session,
    user: models.User,
    role_names: Iterable[str],
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.User:
    role_names = list(role_names)
    user.roles.clear()
    db.flush()
    for role_name in role_names:
        role = ensure_role(db, role_name)
        db.add(models.UserRole(user=user, role=role))

    user.rol = _select_primary_role(role_names)
    db.commit()
    db.refresh(user)

    log_payload: dict[str, object] = {"roles": sorted(role_names)}
    if reason:
        log_payload["reason"] = reason
    _log_action(
        db,
        action="user_roles_updated",
        entity_type="user",
        entity_id=str(user.id),
        performed_by_id=performed_by_id,
        details=json.dumps(log_payload, ensure_ascii=False),
    )
    db.commit()
    db.refresh(user)
    return user


def set_user_status(
    db: Session,
    user: models.User,
    *,
    is_active: bool,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.User:
    user.is_active = is_active
    user.estado = "ACTIVO" if is_active else "INACTIVO"
    db.commit()
    db.refresh(user)
    log_payload: dict[str, object] = {
        "is_active": is_active,
        "estado": user.estado,
    }
    if reason:
        log_payload["reason"] = reason
    _log_action(
        db,
        action="user_status_changed",
        entity_type="user",
        entity_id=str(user.id),
        performed_by_id=performed_by_id,
        details=json.dumps(log_payload, ensure_ascii=False),
    )
    db.commit()
    db.refresh(user)
    return user


def get_role(db: Session, name: str) -> models.Role:
    statement = select(models.Role).where(func.upper(models.Role.name) == name.strip().upper())
    role = db.scalars(statement).first()
    if role is None:
        raise LookupError("role_not_found")
    return role


def update_user(
    db: Session,
    user: models.User,
    updates: dict[str, object],
    *,
    password_hash: str | None = None,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.User:
    was_inactive = not user.is_active
    changes: dict[str, object] = {}

    if "full_name" in updates:
        raw_name = updates.get("full_name")
        normalized_name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else None
        if user.full_name != normalized_name:
            user.full_name = normalized_name
            changes["full_name"] = normalized_name

    if "telefono" in updates:
        raw_phone = updates.get("telefono")
        normalized_phone = raw_phone.strip() if isinstance(raw_phone, str) and raw_phone.strip() else None
        if user.telefono != normalized_phone:
            user.telefono = normalized_phone
            changes["telefono"] = normalized_phone

    if "store_id" in updates:
        store_value = updates.get("store_id")
        if store_value is None:
            if user.store_id is not None:
                user.store_id = None
                changes["store_id"] = None
        else:
            try:
                store_id = int(store_value)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid_store_id") from exc
            try:
                store = get_store(db, store_id)
            except LookupError as exc:
                raise ValueError("store_not_found") from exc
            if user.store_id != store.id:
                user.store_id = store.id
                changes["store_id"] = store.id

    if password_hash:
        user.password_hash = password_hash
        user.failed_login_attempts = 0
        user.locked_until = None
        changes["password_changed"] = True
        if was_inactive:
            user.is_active = True
            user.estado = "ACTIVO"
            changes["is_active"] = True
            changes["estado"] = "ACTIVO"

    if not changes:
        return user

    db.commit()
    db.refresh(user)

    log_payload: dict[str, object] = {"changes": changes}
    if reason:
        log_payload["reason"] = reason
    _log_action(
        db,
        action="user_updated",
        entity_type="user",
        entity_id=str(user.id),
        performed_by_id=performed_by_id,
        details=json.dumps(log_payload, ensure_ascii=False),
    )
    db.commit()
    db.refresh(user)
    return user


def list_role_permissions(
    db: Session,
    *,
    role_name: str | None = None,
) -> list[schemas.RolePermissionMatrix]:
    role_names: list[str]
    if role_name:
        role = get_role(db, role_name)
        role_names = [role.name]
    else:
        role_names = [role.name for role in list_roles(db)]

    if not role_names:
        return []

    for name in role_names:
        ensure_role_permissions(db, name)
    db.commit()

    statement = (
        select(models.Permission)
        .where(models.Permission.role_name.in_(role_names))
        .order_by(models.Permission.role_name.asc(), models.Permission.module.asc())
    )
    records = list(db.scalars(statement))

    grouped: dict[str, list[schemas.RoleModulePermission]] = {name: [] for name in role_names}
    for permission in records:
        grouped.setdefault(permission.role_name, []).append(
            schemas.RoleModulePermission(
                module=permission.module,
                can_view=permission.can_view,
                can_edit=permission.can_edit,
                can_delete=permission.can_delete,
            )
        )

    matrices: list[schemas.RolePermissionMatrix] = []
    for name in role_names:
        permissions = sorted(grouped.get(name, []), key=lambda item: item.module)
        matrices.append(schemas.RolePermissionMatrix(role=name, permissions=permissions))
    return matrices


def update_role_permissions(
    db: Session,
    role_name: str,
    permissions: Sequence[schemas.RoleModulePermission],
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> schemas.RolePermissionMatrix:
    role = get_role(db, role_name)
    ensure_role_permissions(db, role.name)
    db.flush()

    updated_modules: list[dict[str, object]] = []
    for entry in permissions:
        module_key = entry.module.strip().lower()
        statement = (
            select(models.Permission)
            .where(models.Permission.role_name == role.name)
            .where(models.Permission.module == module_key)
        )
        permission = db.scalars(statement).first()
        if permission is None:
            permission = models.Permission(role_name=role.name, module=module_key)
            db.add(permission)
        permission.can_view = bool(entry.can_view)
        permission.can_edit = bool(entry.can_edit)
        permission.can_delete = bool(entry.can_delete)
        updated_modules.append(
            {
                "module": module_key,
                "can_view": permission.can_view,
                "can_edit": permission.can_edit,
                "can_delete": permission.can_delete,
            }
        )

    db.commit()

    log_payload: dict[str, object] = {"permissions": updated_modules}
    if reason:
        log_payload["reason"] = reason
    _log_action(
        db,
        action="role_permissions_updated",
        entity_type="role",
        entity_id=role.name,
        performed_by_id=performed_by_id,
        details=json.dumps(log_payload, ensure_ascii=False),
    )
    db.commit()

    return list_role_permissions(db, role_name=role.name)[0]


def _user_is_locked(user: models.User) -> bool:
    locked_until = user.locked_until
    if locked_until is None:
        return False
    if locked_until.tzinfo is None:
        return locked_until > datetime.utcnow()
    return locked_until > datetime.now(timezone.utc)


def build_user_directory(
    db: Session,
    *,
    search: str | None = None,
    role: str | None = None,
    status: Literal["all", "active", "inactive", "locked"] = "all",
    store_id: int | None = None,
) -> schemas.UserDirectoryReport:
    users = list_users(
        db,
        search=search,
        role=role,
        status=status,
        store_id=store_id,
    )

    active_count = sum(1 for user in users if user.is_active)
    inactive_count = sum(1 for user in users if not user.is_active)
    locked_count = sum(1 for user in users if _user_is_locked(user))

    items = [
        schemas.UserDirectoryEntry(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            telefono=user.telefono,
            rol=user.rol,
            estado=user.estado,
            is_active=user.is_active,
            roles=sorted({assignment.role.name for assignment in user.roles}),
            store_id=user.store_id,
            store_name=user.store.name if user.store else None,
            last_login_at=user.last_login_attempt_at,
        )
        for user in users
    ]

    report = schemas.UserDirectoryReport(
        generated_at=datetime.utcnow(),
        filters=schemas.UserDirectoryFilters(
            search=search,
            role=role,
            status=status,
            store_id=store_id,
        ),
        totals=schemas.UserDirectoryTotals(
            total=len(users),
            active=active_count,
            inactive=inactive_count,
            locked=locked_count,
        ),
        items=items,
    )
    return report


def get_user_dashboard_metrics(
    db: Session,
    *,
    activity_limit: int = 12,
    session_limit: int = 8,
    lookback_hours: int = 48,
) -> schemas.UserDashboardMetrics:
    activity_limit = max(1, min(activity_limit, 50))
    session_limit = max(1, min(session_limit, 25))

    directory = build_user_directory(db)

    activity_statement = (
        select(models.AuditLog)
        .options(joinedload(models.AuditLog.performed_by))
        .where(
            or_(
                models.AuditLog.entity_type.in_(["user", "usuarios", "security"]),
                models.AuditLog.action.ilike("auth_%"),
                models.AuditLog.action.ilike("user_%"),
            )
        )
        .order_by(models.AuditLog.created_at.desc())
        .limit(activity_limit)
    )
    logs = list(db.scalars(activity_statement))

    target_ids = {
        int(log.entity_id)
        for log in logs
        if log.entity_type in {"user", "usuarios"} and str(log.entity_id).isdigit()
    }
    user_lookup: dict[int, models.User] = {}
    if target_ids:
        lookup_statement = (
            select(models.User)
            .options(joinedload(models.User.store))
            .where(models.User.id.in_(target_ids))
        )
        user_lookup = {user.id: user for user in db.scalars(lookup_statement)}

    recent_activity: list[schemas.UserDashboardActivity] = []
    for log in logs:
        details: dict[str, object] | None = None
        if log.details:
            try:
                parsed = json.loads(log.details)
                if isinstance(parsed, dict):
                    details = parsed
                else:
                    details = {"raw": log.details}
            except json.JSONDecodeError:
                details = {"raw": log.details}

        target_user_id: int | None = None
        target_username: str | None = None
        if log.entity_type in {"user", "usuarios"} and str(log.entity_id).isdigit():
            target_user_id = int(log.entity_id)
            target = user_lookup.get(target_user_id)
            if target is not None:
                target_username = _user_display_name(target)

        recent_activity.append(
            schemas.UserDashboardActivity(
                id=log.id,
                action=log.action,
                created_at=log.created_at,
                severity=audit_utils.classify_severity(log.action or "", log.details),
                performed_by_id=log.performed_by_id,
                performed_by_name=_user_display_name(log.performed_by),
                target_user_id=target_user_id,
                target_username=target_username,
                details=details,
            )
        )

    sessions = list_active_sessions(db)[:session_limit]
    session_entries: list[schemas.UserSessionSummary] = []
    for session in sessions:
        status = "activa"
        if session.revoked_at is not None:
            status = "revocada"
        elif is_session_expired(session.expires_at):
            status = "expirada"
        session_entries.append(
            schemas.UserSessionSummary(
                session_id=session.id,
                user_id=session.user_id,
                username=_user_display_name(session.user) or f"Usuario {session.user_id}",
                created_at=session.created_at,
                last_used_at=session.last_used_at,
                expires_at=session.expires_at,
                status=status,
                revoke_reason=session.revoke_reason,
            )
        )

    persistent_alerts = [
        alert
        for alert in get_persistent_audit_alerts(
            db,
            threshold_minutes=60,
            min_occurrences=1,
            lookback_hours=lookback_hours,
            limit=10,
        )
        if str(alert.get("entity_type", "")).lower()
        in {"user", "usuarios", "security"}
    ]
    persistent_map = {
        (str(alert["entity_type"]), str(alert["entity_id"])): alert
        for alert in persistent_alerts
    }

    alert_logs_statement = (
        select(models.AuditLog)
        .where(models.AuditLog.entity_type.in_(["user", "usuarios", "security"]))
        .order_by(models.AuditLog.created_at.desc())
        .limit(100)
    )
    alert_logs = list(db.scalars(alert_logs_statement))
    summary = audit_utils.summarize_alerts(alert_logs, max_highlights=5)

    highlights: list[schemas.AuditHighlight] = []
    acknowledged_entities: dict[tuple[str, str], schemas.AuditAcknowledgedEntity] = {}
    for highlight in summary.highlights:
        key = (highlight["entity_type"], highlight["entity_id"])
        alert_data = persistent_map.get(key)
        status = str(alert_data.get("status", "pending")) if alert_data else "pending"
        acknowledged_at = alert_data.get("acknowledged_at") if alert_data else None
        acknowledged_by_id = alert_data.get("acknowledged_by_id") if alert_data else None
        acknowledged_by_name = alert_data.get("acknowledged_by_name") if alert_data else None
        acknowledged_note = alert_data.get("acknowledged_note") if alert_data else None

        if status == "acknowledged" and acknowledged_at is not None:
            acknowledged_entities[key] = schemas.AuditAcknowledgedEntity(
                entity_type=highlight["entity_type"],
                entity_id=highlight["entity_id"],
                acknowledged_at=acknowledged_at,
                acknowledged_by_id=acknowledged_by_id,
                acknowledged_by_name=acknowledged_by_name,
                note=acknowledged_note,
            )

        highlights.append(
            schemas.AuditHighlight(
                id=highlight["id"],
                action=highlight["action"],
                created_at=highlight["created_at"],
                severity=highlight["severity"],
                entity_type=highlight["entity_type"],
                entity_id=highlight["entity_id"],
                status="acknowledged" if status == "acknowledged" else "pending",
                acknowledged_at=acknowledged_at,
                acknowledged_by_id=acknowledged_by_id,
                acknowledged_by_name=acknowledged_by_name,
                acknowledged_note=acknowledged_note,
            )
        )

    pending_count = len([item for item in highlights if item.status != "acknowledged"])
    acknowledged_list = list(acknowledged_entities.values())

    audit_alerts = schemas.DashboardAuditAlerts(
        total=summary.total,
        critical=summary.critical,
        warning=summary.warning,
        info=summary.info,
        pending_count=pending_count,
        acknowledged_count=len(acknowledged_list),
        highlights=highlights,
        acknowledged_entities=acknowledged_list,
    )

    return schemas.UserDashboardMetrics(
        generated_at=datetime.utcnow(),
        totals=directory.totals,
        recent_activity=recent_activity,
        active_sessions=session_entries,
        audit_alerts=audit_alerts,
    )

def get_totp_secret(db: Session, user_id: int) -> models.UserTOTPSecret | None:
    statement = select(models.UserTOTPSecret).where(models.UserTOTPSecret.user_id == user_id)
    return db.scalars(statement).first()


def provision_totp_secret(
    db: Session,
    user_id: int,
    secret: str,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.UserTOTPSecret:
    record = get_totp_secret(db, user_id)
    if record is None:
        record = models.UserTOTPSecret(user_id=user_id, secret=secret, is_active=False)
        db.add(record)
    else:
        record.secret = secret
        record.is_active = False
        record.activated_at = None
        record.last_verified_at = None
    db.commit()
    db.refresh(record)

    details = json.dumps({"reason": reason}, ensure_ascii=False) if reason else None
    _log_action(
        db,
        action="totp_provisioned",
        entity_type="user",
        entity_id=str(user_id),
        performed_by_id=performed_by_id,
        details=details,
    )
    db.commit()
    db.refresh(record)
    return record


def activate_totp_secret(
    db: Session,
    user_id: int,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.UserTOTPSecret:
    record = get_totp_secret(db, user_id)
    if record is None:
        raise LookupError("totp_not_provisioned")
    record.is_active = True
    now = datetime.utcnow()
    record.activated_at = now
    record.last_verified_at = now
    db.commit()
    db.refresh(record)

    details = json.dumps({"reason": reason}, ensure_ascii=False) if reason else None
    _log_action(
        db,
        action="totp_activated",
        entity_type="user",
        entity_id=str(user_id),
        performed_by_id=performed_by_id,
        details=details,
    )
    db.commit()
    db.refresh(record)
    return record


def deactivate_totp_secret(
    db: Session,
    user_id: int,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> None:
    record = get_totp_secret(db, user_id)
    if record is None:
        return
    record.is_active = False
    db.commit()

    details = json.dumps({"reason": reason}, ensure_ascii=False) if reason else None
    _log_action(
        db,
        action="totp_deactivated",
        entity_type="user",
        entity_id=str(user_id),
        performed_by_id=performed_by_id,
        details=details,
    )
    db.commit()


def update_totp_last_verified(db: Session, user_id: int) -> None:
    record = get_totp_secret(db, user_id)
    if record is None:
        return
    record.last_verified_at = datetime.utcnow()
    db.commit()


def clear_login_lock(db: Session, user: models.User) -> models.User:
    if user.locked_until and user.locked_until <= datetime.utcnow():
        user.locked_until = None
        user.failed_login_attempts = 0
        db.commit()
        db.refresh(user)
    return user


def register_failed_login(
    db: Session, user: models.User, *, reason: str | None = None
) -> models.User:
    now = datetime.utcnow()
    user.failed_login_attempts += 1
    user.last_login_attempt_at = now
    locked_until: datetime | None = None
    if user.failed_login_attempts >= settings.max_failed_login_attempts:
        locked_until = now + timedelta(minutes=settings.account_lock_minutes)
        user.locked_until = locked_until
    db.commit()
    db.refresh(user)

    details_payload: dict[str, object] = {
        "attempts": user.failed_login_attempts,
        "locked_until": locked_until.isoformat() if locked_until else None,
    }
    if reason:
        details_payload["reason"] = reason
    details = json.dumps(details_payload, ensure_ascii=False)
    _log_action(
        db,
        action="auth_login_failed",
        entity_type="user",
        entity_id=str(user.id),
        performed_by_id=user.id,
        details=details,
    )
    db.commit()
    db.refresh(user)
    return user


def register_successful_login(
    db: Session, user: models.User, *, session_token: str | None = None
) -> models.User:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_attempt_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    details_payload = (
        {"session_hint": session_token[-6:]} if session_token else None
    )
    details = (
        json.dumps(details_payload, ensure_ascii=False)
        if details_payload is not None
        else None
    )
    _log_action(
        db,
        action="auth_login_success",
        entity_type="user",
        entity_id=str(user.id),
        performed_by_id=user.id,
        details=details,
    )
    db.commit()
    db.refresh(user)
    return user


def log_unknown_login_attempt(db: Session, username: str) -> None:
    _log_action(
        db,
        action="auth_login_failed",
        entity_type="auth",
        entity_id=username,
        performed_by_id=None,
    )
    db.commit()


def create_password_reset_token(
    db: Session, user_id: int, *, expires_minutes: int
) -> models.PasswordResetToken:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
    record = models.PasswordResetToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    details = json.dumps(
        {"expires_at": record.expires_at.isoformat()}, ensure_ascii=False
    )
    _log_action(
        db,
        action="password_reset_requested",
        entity_type="user",
        entity_id=str(user_id),
        performed_by_id=None,
        details=details,
    )
    db.commit()
    db.refresh(record)
    return record


def get_password_reset_token(
    db: Session, token: str
) -> models.PasswordResetToken | None:
    statement = select(models.PasswordResetToken).where(
        models.PasswordResetToken.token == token
    )
    return db.scalars(statement).first()


def mark_password_reset_token_used(
    db: Session, token_record: models.PasswordResetToken
) -> models.PasswordResetToken:
    token_record.used_at = datetime.utcnow()
    db.commit()
    db.refresh(token_record)
    return token_record


def reset_user_password(
    db: Session,
    user: models.User,
    *,
    password_hash: str,
    performed_by_id: int | None = None,
) -> models.User:
    user.password_hash = password_hash
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_attempt_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    _log_action(
        db,
        action="password_reset_completed",
        entity_type="user",
        entity_id=str(user.id),
        performed_by_id=performed_by_id,
    )
    db.commit()
    db.refresh(user)
    return user


def is_session_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        return expires_at <= datetime.utcnow()
    return expires_at <= datetime.now(timezone.utc)


def create_active_session(
    db: Session,
    user_id: int,
    *,
    session_token: str,
    expires_at: datetime | None = None,
) -> models.ActiveSession:
    session = models.ActiveSession(
        user_id=user_id, session_token=session_token, expires_at=expires_at
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_active_session_by_token(db: Session, session_token: str) -> models.ActiveSession | None:
    statement = (
        select(models.ActiveSession)
        .options(
            joinedload(models.ActiveSession.user)
            .joinedload(models.User.roles)
            .joinedload(models.UserRole.role)
        )
        .where(models.ActiveSession.session_token == session_token)
    )
    return db.scalars(statement).first()


def mark_session_used(db: Session, session_token: str) -> models.ActiveSession | None:
    session = get_active_session_by_token(db, session_token)
    if session is None or session.revoked_at is not None:
        return None
    if is_session_expired(session.expires_at):
        if session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            session.revoke_reason = session.revoke_reason or "expired"
            db.commit()
            db.refresh(session)
        return None
    session.last_used_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


def list_active_sessions(db: Session, *, user_id: int | None = None) -> list[models.ActiveSession]:
    statement = select(models.ActiveSession).order_by(models.ActiveSession.created_at.desc())
    if user_id is not None:
        statement = statement.where(models.ActiveSession.user_id == user_id)
    return list(db.scalars(statement))


def revoke_session(
    db: Session,
    session_id: int,
    *,
    revoked_by_id: int | None,
    reason: str,
) -> models.ActiveSession:
    statement = select(models.ActiveSession).where(models.ActiveSession.id == session_id)
    session = db.scalars(statement).first()
    if session is None:
        raise LookupError("session_not_found")
    if session.revoked_at is not None:
        return session
    session.revoked_at = datetime.utcnow()
    session.revoked_by_id = revoked_by_id
    session.revoke_reason = reason
    db.commit()
    db.refresh(session)
    return session


def _normalize_store_status(value: str | None) -> str:
    if value is None:
        return "activa"
    normalized = value.strip().lower()
    return normalized or "activa"


def _normalize_store_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def _generate_store_code(db: Session) -> str:
    statement = select(models.Store.code)
    highest_sequence = 0
    for existing_code in db.scalars(statement):
        if not existing_code:
            continue
        prefix, separator, suffix = existing_code.partition("-")
        if prefix != "SUC" or separator != "-" or not suffix.isdigit():
            continue
        highest_sequence = max(highest_sequence, int(suffix))
    return f"SUC-{highest_sequence + 1:03d}"


def create_store(db: Session, payload: schemas.StoreCreate, *, performed_by_id: int | None = None) -> models.Store:
    status = _normalize_store_status(payload.status)
    code = _normalize_store_code(payload.code)
    timezone = (payload.timezone or "UTC").strip()
    store = models.Store(
        name=payload.name.strip(),
        location=payload.location.strip() if payload.location else None,
        phone=payload.phone.strip() if payload.phone else None,
        manager=payload.manager.strip() if payload.manager else None,
        status=status,
        code=code or _generate_store_code(db),
        timezone=timezone or "UTC",
    )
    db.add(store)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        message = str(getattr(exc, "orig", exc)).lower()
        if "codigo" in message or "uq_sucursales_codigo" in message:
            raise ValueError("store_code_already_exists") from exc
        raise ValueError("store_already_exists") from exc
    db.refresh(store)

    _log_action(
        db,
        action="store_created",
        entity_type="store",
        entity_id=str(store.id),
        performed_by_id=performed_by_id,
    )
    db.commit()
    db.refresh(store)
    return store


def list_stores(db: Session) -> list[models.Store]:
    statement = select(models.Store).order_by(models.Store.name.asc())
    return list(db.scalars(statement))


def list_customers(
    db: Session,
    *,
    query: str | None = None,
    limit: int = 100,
    status: str | None = None,
    customer_type: str | None = None,
    has_debt: bool | None = None,
) -> list[models.Customer]:
    statement = select(models.Customer).order_by(models.Customer.name.asc()).limit(limit)
    if status:
        normalized_status = _normalize_customer_status(status)
        statement = statement.where(models.Customer.status == normalized_status)
    if customer_type:
        normalized_type = _normalize_customer_type(customer_type)
        statement = statement.where(models.Customer.customer_type == normalized_type)
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.Customer.name).like(normalized),
                func.lower(models.Customer.contact_name).like(normalized),
                func.lower(models.Customer.email).like(normalized),
                func.lower(models.Customer.phone).like(normalized),
                func.lower(models.Customer.customer_type).like(normalized),
                func.lower(models.Customer.status).like(normalized),
                func.lower(func.coalesce(models.Customer.notes, "")).like(normalized),
            )
        )
    if status:
        statement = statement.where(func.lower(models.Customer.status) == status.lower())
    if customer_type:
        statement = statement.where(
            func.lower(models.Customer.customer_type) == customer_type.lower()
        )
    if has_debt is True:
        statement = statement.where(models.Customer.outstanding_debt > 0)
    elif has_debt is False:
        statement = statement.where(models.Customer.outstanding_debt <= 0)
    return list(db.scalars(statement))


def get_customer(db: Session, customer_id: int) -> models.Customer:
    statement = select(models.Customer).where(models.Customer.id == customer_id)
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("customer_not_found") from exc


def create_customer(
    db: Session,
    payload: schemas.CustomerCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Customer:
    history = _history_to_json(payload.history)
    customer_type = _normalize_customer_type(payload.customer_type)
    status = _normalize_customer_status(payload.status)
    credit_limit = _ensure_non_negative_decimal(
        payload.credit_limit, "customer_credit_limit_negative"
    )
    outstanding_debt = _ensure_non_negative_decimal(
        payload.outstanding_debt, "customer_outstanding_debt_negative"
    )
    _ensure_debt_respects_limit(credit_limit, outstanding_debt)
    customer = models.Customer(
        name=payload.name,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        customer_type=customer_type,
        status=status,
        credit_limit=credit_limit,
        notes=payload.notes,
        history=history,
        outstanding_debt=outstanding_debt,
        last_interaction_at=_last_history_timestamp(history),
    )
    db.add(customer)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("customer_already_exists") from exc
    db.refresh(customer)

    _log_action(
        db,
        action="customer_created",
        entity_type="customer",
        entity_id=str(customer.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"name": customer.name}),
    )
    db.commit()
    db.refresh(customer)
    enqueue_sync_outbox(
        db,
        entity_type="customer",
        entity_id=str(customer.id),
        operation="UPSERT",
        payload=_customer_payload(customer),
    )
    return customer


def update_customer(
    db: Session,
    customer_id: int,
    payload: schemas.CustomerUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.Customer:
    customer = get_customer(db, customer_id)
    previous_outstanding = _to_decimal(customer.outstanding_debt).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    updated_fields: dict[str, object] = {}
    outstanding_delta: Decimal | None = None
    ledger_entry: models.CustomerLedgerEntry | None = None
    ledger_details: dict[str, object] | None = None
    pending_history_note: str | None = None
    pending_ledger_entry_kwargs: dict[str, object] | None = None
    if payload.name is not None:
        customer.name = payload.name
        updated_fields["name"] = payload.name
    if payload.contact_name is not None:
        customer.contact_name = payload.contact_name
        updated_fields["contact_name"] = payload.contact_name
    if payload.email is not None:
        customer.email = payload.email
        updated_fields["email"] = payload.email
    if payload.phone is not None:
        customer.phone = payload.phone
        updated_fields["phone"] = payload.phone
    if payload.address is not None:
        customer.address = payload.address
        updated_fields["address"] = payload.address
    if payload.customer_type is not None:
        normalized_type = _normalize_customer_type(payload.customer_type)
        customer.customer_type = normalized_type
        updated_fields["customer_type"] = normalized_type
    if payload.status is not None:
        normalized_status = _normalize_customer_status(payload.status)
        customer.status = normalized_status
        updated_fields["status"] = normalized_status
    if payload.credit_limit is not None:
        customer.credit_limit = _ensure_non_negative_decimal(
            payload.credit_limit, "customer_credit_limit_negative"
        )
        updated_fields["credit_limit"] = float(customer.credit_limit)
    if payload.notes is not None:
        customer.notes = payload.notes
        updated_fields["notes"] = payload.notes
    if payload.outstanding_debt is not None:
        new_outstanding = _ensure_non_negative_decimal(
            payload.outstanding_debt, "customer_outstanding_debt_negative"
        )
        difference = (new_outstanding - previous_outstanding).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        customer.outstanding_debt = new_outstanding
        updated_fields["outstanding_debt"] = float(new_outstanding)
        if difference != Decimal("0"):
            outstanding_delta = difference
            pending_history_note = (
                "Ajuste manual de saldo: antes $"
                f"{float(previous_outstanding):.2f}, ahora ${float(new_outstanding):.2f}"
            )
            ledger_details = {
                "previous_balance": float(previous_outstanding),
                "new_balance": float(new_outstanding),
                "difference": float(difference),
            }
            updated_fields["outstanding_debt_delta"] = float(difference)
            pending_ledger_entry_kwargs = {
                "entry_type": models.CustomerLedgerEntryType.ADJUSTMENT,
                "amount": outstanding_delta,
                "note": pending_history_note,
                "reference_type": "adjustment",
                "reference_id": None,
                "details": ledger_details,
                "created_by_id": performed_by_id,
            }
        previous_outstanding = new_outstanding
    if payload.history is not None:
        history = _history_to_json(payload.history)
        customer.history = history
        customer.last_interaction_at = _last_history_timestamp(history)
        updated_fields["history"] = history
    _ensure_debt_respects_limit(customer.credit_limit, customer.outstanding_debt)
    if pending_history_note:
        _append_customer_history(customer, pending_history_note)
        updated_fields.setdefault("history_note", pending_history_note)
    if pending_ledger_entry_kwargs is not None:
        ledger_entry = _create_customer_ledger_entry(
            db,
            customer=customer,
            **pending_ledger_entry_kwargs,
        )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    if ledger_entry is not None:
        _sync_customer_ledger_entry(db, ledger_entry)

    if updated_fields:
        _log_action(
            db,
            action="customer_updated",
            entity_type="customer",
            entity_id=str(customer.id),
            performed_by_id=performed_by_id,
            details=json.dumps(updated_fields),
        )
        db.commit()
        db.refresh(customer)
    enqueue_sync_outbox(
        db,
        entity_type="customer",
        entity_id=str(customer.id),
        operation="UPSERT",
        payload=_customer_payload(customer),
    )
    return customer


def delete_customer(
    db: Session,
    customer_id: int,
    *,
    performed_by_id: int | None = None,
) -> None:
    customer = get_customer(db, customer_id)
    db.delete(customer)
    db.commit()
    _log_action(
        db,
        action="customer_deleted",
        entity_type="customer",
        entity_id=str(customer_id),
        performed_by_id=performed_by_id,
    )
    db.commit()
    enqueue_sync_outbox(
        db,
        entity_type="customer",
        entity_id=str(customer_id),
        operation="DELETE",
        payload={"id": customer_id},
    )


def export_customers_csv(
    db: Session,
    *,
    query: str | None = None,
    status: str | None = None,
    customer_type: str | None = None,
) -> str:
    customers = list_customers(
        db,
        query=query,
        limit=5000,
        status=status,
        customer_type=customer_type,
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ID",
            "Nombre",
            "Tipo",
            "Estado",
            "Contacto",
            "Correo",
            "Teléfono",
            "Dirección",
            "Límite de crédito",
            "Saldo",
            "Última interacción",
        ]
    )
    for customer in customers:
        writer.writerow(
            [
                customer.id,
                customer.name,
                customer.customer_type,
                customer.status,
                customer.contact_name or "",
                customer.email or "",
                customer.phone or "",
                customer.address or "",
                float(customer.credit_limit),
                float(customer.outstanding_debt),
                customer.last_interaction_at.isoformat()
                if customer.last_interaction_at
                else "",
            ]
        )
    return buffer.getvalue()


def append_customer_note(
    db: Session,
    customer_id: int,
    payload: schemas.CustomerNoteCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Customer:
    customer = get_customer(db, customer_id)
    _append_customer_history(customer, payload.note)
    db.add(customer)

    ledger_entry = _create_customer_ledger_entry(
        db,
        customer=customer,
        entry_type=models.CustomerLedgerEntryType.NOTE,
        amount=Decimal("0"),
        note=payload.note,
        reference_type="note",
        reference_id=None,
        details={"event": "note_added", "note": payload.note},
        created_by_id=performed_by_id,
    )

    _log_action(
        db,
        action="customer_note_added",
        entity_type="customer",
        entity_id=str(customer.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"note": payload.note}),
    )

    db.commit()
    db.refresh(customer)
    db.refresh(ledger_entry)

    enqueue_sync_outbox(
        db,
        entity_type="customer",
        entity_id=str(customer.id),
        operation="UPSERT",
        payload=_customer_payload(customer),
    )
    _sync_customer_ledger_entry(db, ledger_entry)
    return customer


def register_customer_payment(
    db: Session,
    customer_id: int,
    payload: schemas.CustomerPaymentCreate,
    *,
    performed_by_id: int | None = None,
) -> models.CustomerLedgerEntry:
    customer = get_customer(db, customer_id)
    current_debt = _to_decimal(customer.outstanding_debt).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if current_debt <= Decimal("0"):
        raise ValueError("customer_payment_no_debt")

    amount = _to_decimal(payload.amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if amount <= Decimal("0"):
        raise ValueError("customer_payment_invalid_amount")

    applied_amount = min(current_debt, amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    sale = None
    if payload.sale_id is not None:
        sale = get_sale(db, payload.sale_id)
        if sale.customer_id != customer.id:
            raise ValueError("customer_payment_sale_mismatch")

    customer.outstanding_debt = (current_debt - applied_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    _append_customer_history(
        customer,
        f"Pago registrado por ${float(applied_amount):.2f}",
    )
    db.add(customer)

    payment_details: dict[str, object] = {
        "method": payload.method,
        "requested_amount": float(amount),
        "applied_amount": float(applied_amount),
    }
    if payload.reference:
        payment_details["reference"] = payload.reference
    if sale is not None:
        payment_details["sale_id"] = sale.id
        payment_details["store_id"] = sale.store_id
    if payload.note:
        payment_details["note"] = payload.note

    ledger_entry = _create_customer_ledger_entry(
        db,
        customer=customer,
        entry_type=models.CustomerLedgerEntryType.PAYMENT,
        amount=-applied_amount,
        note=payload.note,
        reference_type="sale" if sale is not None else "payment",
        reference_id=str(sale.id) if sale is not None else None,
        details=payment_details,
        created_by_id=performed_by_id,
    )

    _log_action(
        db,
        action="customer_payment_registered",
        entity_type="customer",
        entity_id=str(customer.id),
        performed_by_id=performed_by_id,
        details=json.dumps(
            {
                "applied_amount": float(applied_amount),
                "method": payload.method,
                "reference": payload.reference,
                "sale_id": sale.id if sale is not None else None,
            }
        ),
    )

    db.commit()
    db.refresh(customer)
    db.refresh(ledger_entry)

    enqueue_sync_outbox(
        db,
        entity_type="customer",
        entity_id=str(customer.id),
        operation="UPSERT",
        payload=_customer_payload(customer),
    )
    _sync_customer_ledger_entry(db, ledger_entry)
    return ledger_entry


def get_customer_summary(
    db: Session, customer_id: int
) -> schemas.CustomerSummaryResponse:
    customer = get_customer(db, customer_id)

    ledger_entries = list(
        db.scalars(
            select(models.CustomerLedgerEntry)
            .where(models.CustomerLedgerEntry.customer_id == customer.id)
            .order_by(models.CustomerLedgerEntry.created_at.desc())
            .limit(100)
        )
    )
    payments = [
        entry
        for entry in ledger_entries
        if entry.entry_type == models.CustomerLedgerEntryType.PAYMENT
    ]

    sales = list(
        db.scalars(
            select(models.Sale)
            .options(joinedload(models.Sale.store))
            .where(models.Sale.customer_id == customer.id)
            .order_by(models.Sale.created_at.desc())
            .limit(50)
        )
    )
    store_ids = {sale.store_id for sale in sales}
    configs: dict[int, models.POSConfig] = {}
    if store_ids:
        config_stmt = select(models.POSConfig).where(models.POSConfig.store_id.in_(store_ids))
        configs = {config.store_id: config for config in db.scalars(config_stmt)}

    sales_summary = [
        schemas.CustomerSaleSummary(
            sale_id=sale.id,
            store_id=sale.store_id,
            store_name=sale.store.name if sale.store else None,
            payment_method=sale.payment_method,
            status=sale.status,
            subtotal_amount=float(sale.subtotal_amount or Decimal("0")),
            tax_amount=float(sale.tax_amount or Decimal("0")),
            total_amount=float(sale.total_amount or Decimal("0")),
            created_at=sale.created_at,
        )
        for sale in sales
    ]

    invoices = [
        schemas.CustomerInvoiceSummary(
            sale_id=sale.id,
            invoice_number=(
                f"{configs[sale.store_id].invoice_prefix}-{sale.id:06d}"
                if sale.store_id in configs
                else f"VENTA-{sale.id:06d}"
            ),
            total_amount=float(sale.total_amount or Decimal("0")),
            status=sale.status,
            created_at=sale.created_at,
            store_id=sale.store_id,
        )
        for sale in sales
    ]

    credit_limit = _to_decimal(customer.credit_limit).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    outstanding = _to_decimal(customer.outstanding_debt).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    available_credit = (credit_limit - outstanding).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total_sales_credit = sum(
        float(_to_decimal(sale.total_amount))
        for sale in sales
        if sale.payment_method == models.PaymentMethod.CREDITO
        and (sale.status or "").upper() != "CANCELADA"
    )
    total_payments = sum(float(abs(entry.amount)) for entry in payments)

    snapshot = schemas.CustomerFinancialSnapshot(
        credit_limit=float(credit_limit),
        outstanding_debt=float(outstanding),
        available_credit=float(available_credit),
        total_sales_credit=total_sales_credit,
        total_payments=total_payments,
    )

    customer_schema = schemas.CustomerResponse.model_validate(customer)
    return schemas.CustomerSummaryResponse(
        customer=customer_schema,
        totals=snapshot,
        sales=sales_summary,
        invoices=invoices,
        payments=payments[:20],
        ledger=ledger_entries[:50],
    )


def _customer_sales_stats_subquery(
    *, date_from: date | None = None, date_to: date | None = None
):
    statement = (
        select(
            models.Sale.customer_id.label("customer_id"),
            func.count(models.Sale.id).label("sales_count"),
            func.coalesce(func.sum(models.Sale.total_amount), Decimal("0")).label(
                "sales_total"
            ),
            func.max(models.Sale.created_at).label("last_sale_at"),
        )
        .where(
            models.Sale.customer_id.is_not(None),
            models.Sale.status != "CANCELADA",
        )
    )
    if date_from is not None:
        statement = statement.where(func.date(models.Sale.created_at) >= date_from)
    if date_to is not None:
        statement = statement.where(func.date(models.Sale.created_at) <= date_to)
    return statement.group_by(models.Sale.customer_id).subquery()


def build_customer_portfolio(
    db: Session,
    *,
    category: Literal["delinquent", "frequent"],
    limit: int = 50,
    date_from: date | None = None,
    date_to: date | None = None,
) -> schemas.CustomerPortfolioReport:
    sales_stats = _customer_sales_stats_subquery(date_from=date_from, date_to=date_to)
    base_statement = select(
        models.Customer,
        sales_stats.c.sales_count,
        sales_stats.c.sales_total,
        sales_stats.c.last_sale_at,
    )

    if category == "frequent":
        statement = (
            base_statement.join(sales_stats, sales_stats.c.customer_id == models.Customer.id)
            .order_by(desc(sales_stats.c.sales_total), models.Customer.name.asc())
            .limit(limit)
        )
    else:
        statement = (
            base_statement.outerjoin(
                sales_stats, sales_stats.c.customer_id == models.Customer.id
            )
            .where(
                or_(
                    models.Customer.status == "moroso",
                    models.Customer.outstanding_debt > 0,
                )
            )
            .order_by(models.Customer.outstanding_debt.desc(), models.Customer.name.asc())
            .limit(limit)
        )

    rows = db.execute(statement).all()
    items: list[schemas.CustomerPortfolioItem] = []
    total_debt = Decimal("0")
    total_sales = Decimal("0")

    for row in rows:
        customer: models.Customer = row[0]
        sales_count = int(row[1] or 0)
        sales_total = Decimal(row[2] or 0)
        last_sale_at = row[3]
        outstanding = Decimal(customer.outstanding_debt or 0).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        credit_limit = Decimal(customer.credit_limit or 0).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        available_credit = max(Decimal("0"), credit_limit - outstanding)

        total_debt += outstanding
        total_sales += sales_total

        items.append(
            schemas.CustomerPortfolioItem(
                customer_id=customer.id,
                name=customer.name,
                status=customer.status,
                customer_type=customer.customer_type,
                credit_limit=float(credit_limit),
                outstanding_debt=float(outstanding),
                available_credit=float(available_credit),
                sales_total=float(sales_total),
                sales_count=sales_count,
                last_sale_at=last_sale_at,
                last_interaction_at=customer.last_interaction_at,
            )
        )

    filters = schemas.CustomerPortfolioFilters(
        category=category,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    totals = schemas.CustomerPortfolioTotals(
        customers=len(items),
        moroso_flagged=sum(1 for item in items if item.status == "moroso"),
        outstanding_debt=float(total_debt),
        sales_total=float(total_sales),
    )

    return schemas.CustomerPortfolioReport(
        generated_at=datetime.utcnow(),
        category=category,
        filters=filters,
        items=items,
        totals=totals,
    )


def get_customer_dashboard_metrics(
    db: Session,
    *,
    months: int = 6,
    top_limit: int = 5,
) -> schemas.CustomerDashboardMetrics:
    months = max(1, min(months, 24))
    today = datetime.utcnow().date()
    current_month = date(today.year, today.month, 1)
    months_sequence: list[date] = []
    for _ in range(months):
        months_sequence.append(current_month)
        if current_month.month == 1:
            current_month = date(current_month.year - 1, 12, 1)
        else:
            current_month = date(current_month.year, current_month.month - 1, 1)
    months_sequence.reverse()
    cutoff_month = months_sequence[0]
    cutoff_datetime = datetime.combine(cutoff_month, datetime.min.time())

    creation_rows = db.execute(
        select(models.Customer.created_at).where(
            models.Customer.created_at >= cutoff_datetime
        )
    ).all()
    month_totals: dict[date, int] = {month: 0 for month in months_sequence}
    for (created_at,) in creation_rows:
        if created_at is None:
            continue
        created_month = date(created_at.year, created_at.month, 1)
        if created_month in month_totals:
            month_totals[created_month] += 1

    new_customers_chart = [
        schemas.DashboardChartPoint(
            label=month.strftime("%b %Y"),
            value=float(month_totals.get(month, 0)),
        )
        for month in months_sequence
    ]

    portfolio = build_customer_portfolio(
        db,
        category="frequent",
        limit=top_limit,
    )
    top_customers = [
        schemas.CustomerLeaderboardEntry(
            customer_id=item.customer_id,
            name=item.name,
            status=item.status,
            customer_type=item.customer_type,
            sales_total=item.sales_total,
            sales_count=item.sales_count,
            last_sale_at=item.last_sale_at,
            outstanding_debt=item.outstanding_debt,
        )
        for item in portfolio.items
    ]

    delinquent_row = db.execute(
        select(
            func.count(models.Customer.id).label("customers_with_debt"),
            func.coalesce(
                func.sum(models.Customer.outstanding_debt), Decimal("0")
            ).label("total_outstanding_debt"),
            func.coalesce(
                func.sum(
                    case(
                        (models.Customer.status == "moroso", 1),
                        else_=0,
                    )
                ),
                0,
            ).label("moroso_flagged"),
        ).where(models.Customer.outstanding_debt > 0)
    ).one()

    delinquent_summary = schemas.CustomerDelinquentSummary(
        customers_with_debt=int(delinquent_row.customers_with_debt or 0),
        moroso_flagged=int(delinquent_row.moroso_flagged or 0),
        total_outstanding_debt=float(delinquent_row.total_outstanding_debt or 0),
    )

    return schemas.CustomerDashboardMetrics(
        generated_at=datetime.utcnow(),
        months=months,
        new_customers_per_month=new_customers_chart,
        top_customers=top_customers,
        delinquent_summary=delinquent_summary,
    )


def list_suppliers(
    db: Session,
    *,
    query: str | None = None,
    limit: int = 100,
) -> list[models.Supplier]:
    statement = select(models.Supplier).order_by(models.Supplier.name.asc()).limit(limit)
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.Supplier.name).like(normalized),
                func.lower(models.Supplier.contact_name).like(normalized),
                func.lower(models.Supplier.email).like(normalized),
            )
        )
    return list(db.scalars(statement))


def get_supplier(db: Session, supplier_id: int) -> models.Supplier:
    statement = select(models.Supplier).where(models.Supplier.id == supplier_id)
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("supplier_not_found") from exc


def create_supplier(
    db: Session,
    payload: schemas.SupplierCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Supplier:
    history = _history_to_json(payload.history)
    supplier = models.Supplier(
        name=payload.name,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        notes=payload.notes,
        history=history,
        outstanding_debt=_to_decimal(payload.outstanding_debt),
    )
    db.add(supplier)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("supplier_already_exists") from exc
    db.refresh(supplier)

    _log_action(
        db,
        action="supplier_created",
        entity_type="supplier",
        entity_id=str(supplier.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"name": supplier.name}),
    )
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(
    db: Session,
    supplier_id: int,
    payload: schemas.SupplierUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.Supplier:
    supplier = get_supplier(db, supplier_id)
    updated_fields: dict[str, object] = {}
    if payload.name is not None:
        supplier.name = payload.name
        updated_fields["name"] = payload.name
    if payload.contact_name is not None:
        supplier.contact_name = payload.contact_name
        updated_fields["contact_name"] = payload.contact_name
    if payload.email is not None:
        supplier.email = payload.email
        updated_fields["email"] = payload.email
    if payload.phone is not None:
        supplier.phone = payload.phone
        updated_fields["phone"] = payload.phone
    if payload.address is not None:
        supplier.address = payload.address
        updated_fields["address"] = payload.address
    if payload.notes is not None:
        supplier.notes = payload.notes
        updated_fields["notes"] = payload.notes
    if payload.outstanding_debt is not None:
        supplier.outstanding_debt = _to_decimal(payload.outstanding_debt)
        updated_fields["outstanding_debt"] = float(supplier.outstanding_debt)
    if payload.history is not None:
        history = _history_to_json(payload.history)
        supplier.history = history
        updated_fields["history"] = history
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    if updated_fields:
        _log_action(
            db,
            action="supplier_updated",
            entity_type="supplier",
            entity_id=str(supplier.id),
            performed_by_id=performed_by_id,
            details=json.dumps(updated_fields),
        )
        db.commit()
        db.refresh(supplier)
    return supplier


def delete_supplier(
    db: Session,
    supplier_id: int,
    *,
    performed_by_id: int | None = None,
) -> None:
    supplier = get_supplier(db, supplier_id)
    db.delete(supplier)
    db.commit()
    _log_action(
        db,
        action="supplier_deleted",
        entity_type="supplier",
        entity_id=str(supplier_id),
        performed_by_id=performed_by_id,
    )
    db.commit()


def get_purchase_vendor(db: Session, vendor_id: int) -> models.Proveedor:
    vendor = db.get(models.Proveedor, vendor_id)
    if vendor is None:
        raise LookupError("purchase_vendor_not_found")
    return vendor


def list_purchase_vendors(
    db: Session,
    *,
    vendor_id: int | None = None,
    query: str | None = None,
    estado: str | None = None,
    limit: int = 100,
) -> list[schemas.PurchaseVendorResponse]:
    statement = (
        select(
            models.Proveedor,
            func.coalesce(func.sum(models.Compra.total), 0).label("total_compras"),
            func.coalesce(func.sum(models.Compra.impuesto), 0).label("total_impuesto"),
            func.count(models.Compra.id_compra).label("compras_registradas"),
            func.max(models.Compra.fecha).label("ultima_compra"),
        )
        .outerjoin(models.Compra, models.Compra.proveedor_id == models.Proveedor.id_proveedor)
        .group_by(models.Proveedor.id_proveedor)
        .order_by(models.Proveedor.nombre.asc())
        .limit(limit)
    )
    if vendor_id is not None:
        statement = statement.where(models.Proveedor.id_proveedor == vendor_id)
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(func.lower(models.Proveedor.nombre).like(normalized))
    if estado:
        statement = statement.where(func.lower(models.Proveedor.estado) == estado.lower())

    rows = db.execute(statement).all()
    vendors: list[schemas.PurchaseVendorResponse] = []
    for vendor, total, tax, count, last_date in rows:
        vendors.append(
            schemas.PurchaseVendorResponse(
                id_proveedor=vendor.id_proveedor,
                nombre=vendor.nombre,
                telefono=vendor.telefono,
                correo=vendor.correo,
                direccion=vendor.direccion,
                tipo=vendor.tipo,
                notas=vendor.notas,
                estado=vendor.estado,
                total_compras=_to_decimal(total or 0),
                total_impuesto=_to_decimal(tax or 0),
                compras_registradas=int(count or 0),
                ultima_compra=last_date,
            )
        )
    return vendors


def create_purchase_vendor(
    db: Session,
    payload: schemas.PurchaseVendorCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Proveedor:
    vendor = models.Proveedor(
        nombre=payload.nombre,
        telefono=payload.telefono,
        correo=payload.correo,
        direccion=payload.direccion,
        tipo=payload.tipo,
        estado=payload.estado or "activo",
        notas=payload.notas,
    )
    db.add(vendor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("purchase_vendor_duplicate") from exc
    db.refresh(vendor)

    _log_action(
        db,
        action="purchase_vendor_created",
        entity_type="purchase_vendor",
        entity_id=str(vendor.id_proveedor),
        performed_by_id=performed_by_id,
        details=json.dumps({"nombre": vendor.nombre, "estado": vendor.estado}),
    )
    db.commit()
    db.refresh(vendor)
    return vendor


def update_purchase_vendor(
    db: Session,
    vendor_id: int,
    payload: schemas.PurchaseVendorUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.Proveedor:
    vendor = get_purchase_vendor(db, vendor_id)
    updated_fields: dict[str, object] = {}
    if payload.nombre is not None:
        vendor.nombre = payload.nombre
        updated_fields["nombre"] = payload.nombre
    if payload.telefono is not None:
        vendor.telefono = payload.telefono
        updated_fields["telefono"] = payload.telefono
    if payload.correo is not None:
        vendor.correo = payload.correo
        updated_fields["correo"] = payload.correo
    if payload.direccion is not None:
        vendor.direccion = payload.direccion
        updated_fields["direccion"] = payload.direccion
    if payload.tipo is not None:
        vendor.tipo = payload.tipo
        updated_fields["tipo"] = payload.tipo
    if payload.notas is not None:
        vendor.notas = payload.notas
        updated_fields["notas"] = payload.notas
    if payload.estado is not None:
        vendor.estado = payload.estado
        updated_fields["estado"] = payload.estado

    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    if updated_fields:
        _log_action(
            db,
            action="purchase_vendor_updated",
            entity_type="purchase_vendor",
            entity_id=str(vendor.id_proveedor),
            performed_by_id=performed_by_id,
            details=json.dumps(updated_fields),
        )
        db.commit()
        db.refresh(vendor)
    return vendor


def set_purchase_vendor_status(
    db: Session,
    vendor_id: int,
    estado: str,
    *,
    performed_by_id: int | None = None,
) -> models.Proveedor:
    vendor = get_purchase_vendor(db, vendor_id)
    vendor.estado = estado
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    _log_action(
        db,
        action="purchase_vendor_status_updated",
        entity_type="purchase_vendor",
        entity_id=str(vendor.id_proveedor),
        performed_by_id=performed_by_id,
        details=json.dumps({"estado": estado}),
    )
    db.commit()
    db.refresh(vendor)
    return vendor


def export_purchase_vendors_csv(
    db: Session,
    *,
    query: str | None = None,
    estado: str | None = None,
) -> str:
    vendors = list_purchase_vendors(db, query=query, estado=estado, limit=500)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ID",
            "Nombre",
            "Estado",
            "Teléfono",
            "Correo",
            "Tipo",
            "Total compras",
            "Impuestos",
            "Órdenes registradas",
            "Última compra",
        ]
    )
    for vendor in vendors:
        writer.writerow(
            [
                vendor.id,
                vendor.nombre,
                vendor.estado,
                vendor.telefono or "",
                vendor.correo or "",
                vendor.tipo or "",
                float(vendor.total_compras),
                float(vendor.total_impuesto),
                vendor.compras_registradas,
                vendor.ultima_compra.isoformat() if vendor.ultima_compra else "",
            ]
        )
    return buffer.getvalue()


def list_supplier_batches(
    db: Session, supplier_id: int, *, limit: int = 50
) -> list[models.SupplierBatch]:
    supplier = get_supplier(db, supplier_id)
    statement = (
        select(models.SupplierBatch)
        .where(models.SupplierBatch.supplier_id == supplier.id)
        .order_by(models.SupplierBatch.purchase_date.desc(), models.SupplierBatch.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).unique())


def get_supplier_batch_overview(
    db: Session,
    *,
    store_id: int,
    limit: int = 5,
) -> list[dict[str, object]]:
    statement = (
        select(models.SupplierBatch, models.Supplier.name)
        .join(models.Supplier, models.Supplier.id == models.SupplierBatch.supplier_id)
        .where(
            or_(
                models.SupplierBatch.store_id == store_id,
                models.SupplierBatch.store_id.is_(None),
            )
        )
        .order_by(
            models.SupplierBatch.purchase_date.desc(),
            models.SupplierBatch.created_at.desc(),
        )
    )
    rows = db.execute(statement).all()

    overview: dict[int, dict[str, object]] = {}
    for batch, supplier_name in rows:
        entry = overview.setdefault(
            batch.supplier_id,
            {
                "supplier_id": batch.supplier_id,
                "supplier_name": supplier_name,
                "batch_count": 0,
                "total_quantity": 0,
                "total_value": Decimal("0"),
                "latest_purchase_date": batch.purchase_date,
                "latest_batch_code": batch.batch_code,
                "latest_unit_cost": batch.unit_cost,
            },
        )
        entry["batch_count"] = int(entry["batch_count"]) + 1
        entry["total_quantity"] = int(entry["total_quantity"]) + batch.quantity
        entry["total_value"] = Decimal(entry["total_value"]) + (
            Decimal(batch.quantity) * batch.unit_cost
        )

        if batch.purchase_date > entry["latest_purchase_date"]:
            entry["latest_purchase_date"] = batch.purchase_date
            entry["latest_batch_code"] = batch.batch_code
            entry["latest_unit_cost"] = batch.unit_cost

    sorted_entries = sorted(
        overview.values(),
        key=lambda item: (
            item["latest_purchase_date"],
            Decimal(item["total_value"]),
        ),
        reverse=True,
    )

    result: list[dict[str, object]] = []
    for item in sorted_entries[:limit]:
        total_value = Decimal(item["total_value"]).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        latest_unit_cost = item.get("latest_unit_cost")
        result.append(
            {
                "supplier_id": item["supplier_id"],
                "supplier_name": item["supplier_name"],
                "batch_count": item["batch_count"],
                "total_quantity": item["total_quantity"],
                "total_value": float(total_value),
                "latest_purchase_date": item["latest_purchase_date"],
                "latest_batch_code": item.get("latest_batch_code"),
                "latest_unit_cost": float(latest_unit_cost)
                if latest_unit_cost is not None
                else None,
            }
        )

    return result


def create_supplier_batch(
    db: Session,
    supplier_id: int,
    payload: schemas.SupplierBatchCreate,
    *,
    performed_by_id: int | None = None,
) -> models.SupplierBatch:
    supplier = get_supplier(db, supplier_id)
    store = get_store(db, payload.store_id) if payload.store_id else None
    device: models.Device | None = None
    if payload.device_id:
        device = db.get(models.Device, payload.device_id)
        if device is None:
            raise LookupError("device_not_found")
        if store is not None and device.store_id != store.id:
            raise ValueError("supplier_batch_store_mismatch")
        if store is None:
            store = device.store

    batch = models.SupplierBatch(
        supplier_id=supplier.id,
        store_id=store.id if store else None,
        device_id=device.id if device else None,
        model_name=payload.model_name or (device.name if device else ""),
        batch_code=payload.batch_code,
        unit_cost=_to_decimal(payload.unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        quantity=payload.quantity,
        purchase_date=payload.purchase_date,
        notes=payload.notes,
    )
    now = datetime.utcnow()
    batch.created_at = now
    batch.updated_at = now
    db.add(batch)

    if device is not None:
        device.proveedor = supplier.name
        device.lote = payload.batch_code or device.lote
        device.fecha_compra = payload.purchase_date
        device.costo_unitario = batch.unit_cost
        _recalculate_sale_price(device)
        db.add(device)

    db.commit()
    db.refresh(batch)

    if device is not None:
        _recalculate_store_inventory_value(db, device.store_id)

    _log_action(
        db,
        action="supplier_batch_created",
        entity_type="supplier_batch",
        entity_id=str(batch.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"supplier_id": supplier.id, "batch_code": batch.batch_code}),
    )
    db.commit()
    db.refresh(batch)
    return batch


def update_supplier_batch(
    db: Session,
    batch_id: int,
    payload: schemas.SupplierBatchUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.SupplierBatch:
    statement = select(models.SupplierBatch).where(models.SupplierBatch.id == batch_id)
    batch = db.scalars(statement).first()
    if batch is None:
        raise LookupError("supplier_batch_not_found")

    updated_fields: dict[str, object] = {}

    if payload.model_name is not None:
        batch.model_name = payload.model_name
        updated_fields["model_name"] = payload.model_name
    if payload.batch_code is not None:
        batch.batch_code = payload.batch_code
        updated_fields["batch_code"] = payload.batch_code
    if payload.unit_cost is not None:
        batch.unit_cost = _to_decimal(payload.unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        updated_fields["unit_cost"] = float(batch.unit_cost)
    if payload.quantity is not None:
        batch.quantity = payload.quantity
        updated_fields["quantity"] = payload.quantity
    if payload.purchase_date is not None:
        batch.purchase_date = payload.purchase_date
        updated_fields["purchase_date"] = batch.purchase_date.isoformat()
    if payload.notes is not None:
        batch.notes = payload.notes
        updated_fields["notes"] = payload.notes
    if payload.store_id is not None:
        store = get_store(db, payload.store_id)
        batch.store_id = store.id
        updated_fields["store_id"] = store.id
    if payload.device_id is not None:
        if payload.device_id:
            device = db.get(models.Device, payload.device_id)
            if device is None:
                raise LookupError("device_not_found")
            batch.device_id = device.id
            updated_fields["device_id"] = device.id
        else:
            batch.device_id = None
            updated_fields["device_id"] = None

    batch.updated_at = datetime.utcnow()

    db.add(batch)
    db.commit()
    db.refresh(batch)

    if updated_fields:
        _log_action(
            db,
            action="supplier_batch_updated",
            entity_type="supplier_batch",
            entity_id=str(batch.id),
            performed_by_id=performed_by_id,
            details=json.dumps(updated_fields),
        )
        db.commit()
        db.refresh(batch)
    return batch


def delete_supplier_batch(
    db: Session,
    batch_id: int,
    *,
    performed_by_id: int | None = None,
) -> None:
    statement = select(models.SupplierBatch).where(models.SupplierBatch.id == batch_id)
    batch = db.scalars(statement).first()
    if batch is None:
        raise LookupError("supplier_batch_not_found")
    store_id = batch.store_id
    db.delete(batch)
    db.commit()
    if store_id:
        _recalculate_store_inventory_value(db, store_id)
    _log_action(
        db,
        action="supplier_batch_deleted",
        entity_type="supplier_batch",
        entity_id=str(batch_id),
        performed_by_id=performed_by_id,
    )
    db.commit()


def export_suppliers_csv(
    db: Session,
    *,
    query: str | None = None,
) -> str:
    suppliers = list_suppliers(db, query=query, limit=5000)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "ID",
        "Nombre",
        "Contacto",
        "Correo",
        "Teléfono",
        "Dirección",
        "Deuda",
    ])
    for supplier in suppliers:
        writer.writerow(
            [
                supplier.id,
                supplier.name,
                supplier.contact_name or "",
                supplier.email or "",
                supplier.phone or "",
                supplier.address or "",
                float(supplier.outstanding_debt),
            ]
        )
    return buffer.getvalue()


def get_store(db: Session, store_id: int) -> models.Store:
    statement = select(models.Store).where(models.Store.id == store_id)
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("store_not_found") from exc


def create_device(
    db: Session,
    store_id: int,
    payload: schemas.DeviceCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Device:
    get_store(db, store_id)
    payload_data = payload.model_dump()
    provided_fields = payload.model_fields_set
    imei = payload_data.get("imei")
    serial = payload_data.get("serial")
    _ensure_unique_identifiers(db, imei=imei, serial=serial)
    unit_price = None
    if "unit_price" in provided_fields:
        unit_price = payload_data.get("unit_price")
    elif "precio_venta" in provided_fields:
        unit_price = payload_data.get("precio_venta")
    if unit_price is None:
        payload_data.setdefault("unit_price", Decimal("0"))
        payload_data["precio_venta"] = payload_data["unit_price"]
    else:
        payload_data["unit_price"] = _to_decimal(unit_price)
        payload_data["precio_venta"] = payload_data["unit_price"]
    if payload_data.get("costo_unitario") is None:
        payload_data["costo_unitario"] = Decimal("0")
    payload_data["costo_compra"] = payload_data["costo_unitario"]
    if payload_data.get("margen_porcentaje") is None:
        payload_data["margen_porcentaje"] = Decimal("0")
    if payload_data.get("estado_comercial") is None:
        payload_data["estado_comercial"] = models.CommercialState.NUEVO
    if payload_data.get("garantia_meses") is None:
        payload_data["garantia_meses"] = 0
    if payload_data.get("estado") is None:
        payload_data["estado"] = "disponible"
    if payload_data.get("fecha_ingreso") is None:
        payload_data["fecha_ingreso"] = payload_data.get("fecha_compra") or date.today()
    device = models.Device(store_id=store_id, **payload_data)
    if unit_price is None:
        _recalculate_sale_price(device)
    else:
        device.unit_price = unit_price
        device.precio_venta = unit_price
    db.add(device)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("device_already_exists") from exc
    db.refresh(device)

    _log_action(
        db,
        action="device_created",
        entity_type="device",
        entity_id=str(device.id),
        performed_by_id=performed_by_id,
        details=f"SKU={device.sku}",
    )
    db.commit()
    db.refresh(device)
    _recalculate_store_inventory_value(db, store_id)
    enqueue_sync_outbox(
        db,
        entity_type="device",
        entity_id=str(device.id),
        operation="UPSERT",
        payload=_device_sync_payload(device),
    )
    return device


def get_device(db: Session, store_id: int, device_id: int) -> models.Device:
    statement = select(models.Device).where(
        models.Device.id == device_id,
        models.Device.store_id == store_id,
    )
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("device_not_found") from exc


def get_device_global(db: Session, device_id: int) -> models.Device:
    device = db.get(models.Device, device_id)
    if device is None:
        raise LookupError("device_not_found")
    return device


def update_device(
    db: Session,
    store_id: int,
    device_id: int,
    payload: schemas.DeviceUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.Device:
    device = get_device(db, store_id, device_id)
    updated_fields = payload.model_dump(exclude_unset=True)
    manual_price = None
    if "unit_price" in updated_fields:
        manual_price = updated_fields.pop("unit_price")
    if "precio_venta" in updated_fields:
        manual_price = updated_fields.pop("precio_venta")
    imei = updated_fields.get("imei")
    serial = updated_fields.get("serial")
    _ensure_unique_identifiers(
        db,
        imei=imei,
        serial=serial,
        exclude_device_id=device.id,
    )

    sensitive_before = {
        "costo_unitario": device.costo_unitario,
        "estado_comercial": device.estado_comercial,
        "proveedor": device.proveedor,
    }

    for key, value in updated_fields.items():
        setattr(device, key, value)
    if manual_price is not None:
        device.unit_price = manual_price
        device.precio_venta = manual_price
    elif {"costo_unitario", "margen_porcentaje"}.intersection(updated_fields):
        _recalculate_sale_price(device)
    db.commit()
    db.refresh(device)

    fields_changed = list(updated_fields.keys())
    if manual_price is not None:
        fields_changed.extend(["unit_price", "precio_venta"])
    if fields_changed:
        sensitive_after = {
            "costo_unitario": device.costo_unitario,
            "estado_comercial": device.estado_comercial,
            "proveedor": device.proveedor,
        }
        sensitive_changes = {
            key: {"before": str(sensitive_before[key]), "after": str(value)}
            for key, value in sensitive_after.items()
            if sensitive_before.get(key) != value
        }
        _log_action(
            db,
            action="device_updated",
            entity_type="device",
            entity_id=str(device.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"fields": fields_changed, "sensitive": sensitive_changes}),
        )
        db.commit()
        db.refresh(device)
    _recalculate_store_inventory_value(db, store_id)
    enqueue_sync_outbox(
        db,
        entity_type="device",
        entity_id=str(device.id),
        operation="UPSERT",
        payload=_device_sync_payload(device),
    )
    return device


def upsert_device_identifier(
    db: Session,
    store_id: int,
    device_id: int,
    payload: schemas.DeviceIdentifierRequest,
    *,
    reason: str | None = None,
    performed_by_id: int | None = None,
) -> models.DeviceIdentifier:
    device = get_device(db, store_id, device_id)
    payload_data = payload.model_dump()
    imei_1 = payload_data.get("imei_1")
    imei_2 = payload_data.get("imei_2")
    numero_serie = payload_data.get("numero_serie")
    _ensure_unique_identifier_payload(
        db,
        imei_1=imei_1,
        imei_2=imei_2,
        numero_serie=numero_serie,
        exclude_device_id=device.id,
        exclude_identifier_id=device.identifier.id if device.identifier else None,
    )

    identifier = device.identifier
    created = False
    if identifier is None:
        identifier = models.DeviceIdentifier(producto_id=device.id)
        created = True

    identifier.imei_1 = imei_1
    identifier.imei_2 = imei_2
    identifier.numero_serie = numero_serie
    identifier.estado_tecnico = payload_data.get("estado_tecnico")
    identifier.observaciones = payload_data.get("observaciones")

    db.add(identifier)
    db.commit()
    db.refresh(identifier)

    action = "device_identifier_created" if created else "device_identifier_updated"
    details_parts: list[str] = []
    if imei_1:
        details_parts.append(f"IMEI1={imei_1}")
    if imei_2:
        details_parts.append(f"IMEI2={imei_2}")
    if numero_serie:
        details_parts.append(f"SERIE={numero_serie}")
    if reason:
        details_parts.append(f"MOTIVO={reason}")
    details = ", ".join(details_parts) if details_parts else None

    _log_action(
        db,
        action=action,
        entity_type="device",
        entity_id=str(device.id),
        performed_by_id=performed_by_id,
        details=details,
    )
    db.commit()
    db.refresh(identifier)
    return identifier


def get_device_identifier(
    db: Session, store_id: int, device_id: int
) -> models.DeviceIdentifier:
    device = get_device(db, store_id, device_id)
    if device.identifier is None:
        raise LookupError("device_identifier_not_found")
    return device.identifier


def list_devices(
    db: Session,
    store_id: int,
    *,
    search: str | None = None,
    estado: models.CommercialState | None = None,
    categoria: str | None = None,
    condicion: str | None = None,
    estado_inventario: str | None = None,
    ubicacion: str | None = None,
    proveedor: str | None = None,
    fecha_ingreso_desde: date | None = None,
    fecha_ingreso_hasta: date | None = None,
) -> list[models.Device]:
    get_store(db, store_id)
    statement = (
        select(models.Device)
        .options(joinedload(models.Device.identifier))
        .where(models.Device.store_id == store_id)
    )
    if estado is not None:
        statement = statement.where(models.Device.estado_comercial == estado)
    if categoria:
        statement = statement.where(models.Device.categoria.ilike(f"%{categoria}%"))
    if condicion:
        statement = statement.where(models.Device.condicion.ilike(f"%{condicion}%"))
    if estado_inventario:
        statement = statement.where(models.Device.estado.ilike(f"%{estado_inventario}%"))
    if ubicacion:
        statement = statement.where(models.Device.ubicacion.ilike(f"%{ubicacion}%"))
    if proveedor:
        statement = statement.where(models.Device.proveedor.ilike(f"%{proveedor}%"))
    if fecha_ingreso_desde or fecha_ingreso_hasta:
        start, end = _normalize_date_range(fecha_ingreso_desde, fecha_ingreso_hasta)
        statement = statement.where(
            models.Device.fecha_ingreso >= start.date(), models.Device.fecha_ingreso <= end.date()
        )
    if search:
        normalized = f"%{search.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.Device.sku).like(normalized),
                func.lower(models.Device.name).like(normalized),
                func.lower(models.Device.modelo).like(normalized),
                func.lower(models.Device.marca).like(normalized),
                func.lower(models.Device.color).like(normalized),
                func.lower(models.Device.categoria).like(normalized),
                func.lower(models.Device.condicion).like(normalized),
                func.lower(models.Device.capacidad).like(normalized),
                func.lower(models.Device.serial).like(normalized),
                func.lower(models.Device.imei).like(normalized),
                func.lower(models.Device.estado_comercial).like(normalized),
                func.lower(models.Device.estado).like(normalized),
                func.lower(models.Device.descripcion).like(normalized),
                func.lower(models.Device.ubicacion).like(normalized),
            )
        )
    statement = statement.order_by(models.Device.sku.asc())
    return list(db.scalars(statement))


def search_devices(db: Session, filters: schemas.DeviceSearchFilters) -> list[models.Device]:
    statement = (
        select(models.Device)
        .options(
            joinedload(models.Device.store),
            joinedload(models.Device.identifier),
        )
        .join(models.Store)
    )
    if filters.imei:
        statement = statement.where(models.Device.imei == filters.imei)
    if filters.serial:
        statement = statement.where(models.Device.serial == filters.serial)
    if filters.capacidad_gb is not None:
        statement = statement.where(models.Device.capacidad_gb == filters.capacidad_gb)
    if filters.color:
        statement = statement.where(models.Device.color.ilike(f"%{filters.color}%"))
    if filters.marca:
        statement = statement.where(models.Device.marca.ilike(f"%{filters.marca}%"))
    if filters.modelo:
        statement = statement.where(models.Device.modelo.ilike(f"%{filters.modelo}%"))
    if filters.categoria:
        statement = statement.where(models.Device.categoria.ilike(f"%{filters.categoria}%"))
    if filters.condicion:
        statement = statement.where(models.Device.condicion.ilike(f"%{filters.condicion}%"))
    if filters.estado:
        statement = statement.where(models.Device.estado.ilike(f"%{filters.estado}%"))
    if filters.ubicacion:
        statement = statement.where(models.Device.ubicacion.ilike(f"%{filters.ubicacion}%"))
    if filters.proveedor:
        statement = statement.where(models.Device.proveedor.ilike(f"%{filters.proveedor}%"))
    if filters.fecha_ingreso_desde or filters.fecha_ingreso_hasta:
        start, end = _normalize_date_range(filters.fecha_ingreso_desde, filters.fecha_ingreso_hasta)
        statement = statement.where(
            models.Device.fecha_ingreso >= start.date(), models.Device.fecha_ingreso <= end.date()
        )
    statement = statement.order_by(models.Device.store_id.asc(), models.Device.sku.asc())
    return list(db.scalars(statement).unique())


def create_inventory_movement(
    db: Session,
    store_id: int,
    payload: schemas.MovementCreate,
    *,
    performed_by_id: int | None = None,
) -> models.InventoryMovement:
    store = get_store(db, store_id)
    if (
        payload.sucursal_destino_id is not None
        and payload.sucursal_destino_id != store_id
    ):
        raise ValueError("invalid_destination_store")

    source_store_id = payload.sucursal_origen_id

    device = get_device(db, store_id, payload.producto_id)

    previous_quantity = device.quantity
    if source_store_id is not None:
        get_store(db, source_store_id)

    if (
        payload.tipo_movimiento == models.MovementType.OUT
        and device.quantity < payload.cantidad
    ):
        raise ValueError("insufficient_stock")

    if payload.tipo_movimiento == models.MovementType.IN:
        device.quantity += payload.cantidad
        if payload.unit_cost is not None:
            current_total_cost = _to_decimal(device.costo_unitario) * _to_decimal(
                device.quantity - payload.cantidad
            )
            incoming_cost_total = _to_decimal(payload.unit_cost) * _to_decimal(
                payload.cantidad
            )
            divisor = _to_decimal(device.quantity or 1)
            average_cost = (current_total_cost + incoming_cost_total) / divisor
            device.costo_unitario = average_cost.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            _recalculate_sale_price(device)
    elif payload.tipo_movimiento == models.MovementType.OUT:
        device.quantity -= payload.cantidad
        if source_store_id is None:
            source_store_id = store_id
    elif payload.tipo_movimiento == models.MovementType.ADJUST:
        device.quantity = payload.cantidad
        if source_store_id is None:
            source_store_id = store_id

    new_quantity = device.quantity
    quantity_delta = new_quantity - previous_quantity
    reason_segment = f", motivo={payload.comentario}" if payload.comentario else ""
    movement_details = (
        "tipo="
        f"{payload.tipo_movimiento.value}, cantidad={payload.cantidad}, "
        f"stock_previo={previous_quantity}, stock_actual={new_quantity}{reason_segment}"
    )

    movement = models.InventoryMovement(
        store=store,
        source_store_id=source_store_id,
        device=device,
        movement_type=payload.tipo_movimiento,
        quantity=payload.cantidad,
        comment=payload.comentario,
        unit_cost=
            _to_decimal(payload.unit_cost) if payload.unit_cost is not None else None,
        performed_by_id=performed_by_id,
    )
    db.add(movement)
    db.commit()
    db.refresh(device)
    db.refresh(movement)
    # Aseguramos que las relaciones necesarias estén disponibles para la respuesta serializada.
    if movement.store is not None:
        _ = movement.store.name
    if movement.source_store is not None:
        _ = movement.source_store.name
    if movement.performed_by is not None:
        _ = movement.performed_by.username

    _log_action(
        db,
        action="inventory_movement",
        entity_type="device",
        entity_id=str(device.id),
        performed_by_id=performed_by_id,
        details=movement_details,
    )

    if (
        payload.tipo_movimiento == models.MovementType.ADJUST
        and quantity_delta != 0
        and abs(quantity_delta) >= settings.inventory_adjustment_variance_threshold
    ):
        adjustment_reason = (
            f", motivo={payload.comentario}" if payload.comentario else ""
        )
        _log_action(
            db,
            action="inventory_adjustment_alert",
            entity_type="device",
            entity_id=str(device.id),
            performed_by_id=performed_by_id,
            details=(
                "Ajuste manual registrado; inconsistencia detectada"
                f" en la sucursal {store.name}. stock_previo={previous_quantity}, "
                f"stock_actual={new_quantity}, variacion={quantity_delta:+d}"
                f", umbral={settings.inventory_adjustment_variance_threshold}{adjustment_reason}"
            ),
        )

    if new_quantity <= settings.inventory_low_stock_threshold:
        _log_action(
            db,
            action="inventory_low_stock_alert",
            entity_type="device",
            entity_id=str(device.id),
            performed_by_id=performed_by_id,
            details=(
                "Stock bajo detectado"
                f" en la sucursal {store.name}. dispositivo={device.sku}, "
                f"stock_actual={new_quantity}, umbral={settings.inventory_low_stock_threshold}"
            ),
        )

    db.commit()
    db.refresh(movement)
    total_value = _recalculate_store_inventory_value(db, store_id)
    setattr(movement, "store_inventory_value", total_value)
    enqueue_sync_outbox(
        db,
        entity_type="inventory",
        entity_id=str(movement.id),
        operation="UPSERT",
        payload=_inventory_movement_payload(movement),
    )
    if movement.device is not None:
        enqueue_sync_outbox(
            db,
            entity_type="device",
            entity_id=str(movement.device.id),
            operation="UPSERT",
            payload=_device_sync_payload(movement.device),
        )
    return movement


def list_inventory_summary(db: Session) -> list[models.Store]:
    statement = select(models.Store).options(joinedload(models.Store.devices)).order_by(models.Store.name.asc())
    return list(db.scalars(statement).unique())


def compute_inventory_metrics(db: Session, *, low_stock_threshold: int = 5) -> dict[str, object]:
    stores = list_inventory_summary(db)

    total_devices = 0
    total_units = 0
    total_value = Decimal("0")
    store_metrics: list[dict[str, object]] = []
    low_stock: list[dict[str, object]] = []

    for store in stores:
        device_count = len(store.devices)
        store_units = sum(device.quantity for device in store.devices)
        store_value = sum(_device_value(device) for device in store.devices)

        total_devices += device_count
        total_units += store_units
        total_value += store_value

        store_metrics.append(
            {
                "store_id": store.id,
                "store_name": store.name,
                "device_count": device_count,
                "total_units": store_units,
                "total_value": store_value,
            }
        )

        for device in store.devices:
            if device.quantity <= low_stock_threshold:
                low_stock.append(
                    {
                        "store_id": store.id,
                        "store_name": store.name,
                        "device_id": device.id,
                        "sku": device.sku,
                        "name": device.name,
                        "quantity": device.quantity,
                        "unit_price": device.unit_price or Decimal("0"),
                        "inventory_value": _device_value(device),
                    }
                )

    store_metrics.sort(key=lambda item: item["total_value"], reverse=True)
    low_stock.sort(key=lambda item: (item["quantity"], item["name"]))

    sales_stmt = (
        select(models.Sale)
        .options(
            joinedload(models.Sale.items).joinedload(models.SaleItem.device),
            joinedload(models.Sale.store),
        )
        .order_by(models.Sale.created_at.desc())
    )
    sales = list(db.scalars(sales_stmt).unique())

    repairs_stmt = select(models.RepairOrder)
    repairs = list(db.scalars(repairs_stmt))

    total_sales_amount = Decimal("0")
    total_profit = Decimal("0")
    sales_count = len(sales)
    sales_trend_map: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    store_profit: dict[int, dict[str, object]] = {}

    today = datetime.utcnow().date()
    window_days = [today - timedelta(days=delta) for delta in range(6, -1, -1)]
    window_set = set(window_days)

    for sale in sales:
        total_sales_amount += sale.total_amount
        sale_cost = Decimal("0")
        for item in sale.items:
            device_cost = _to_decimal(getattr(item.device, "costo_unitario", None) or item.unit_price)
            sale_cost += (device_cost * item.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        profit = (sale.total_amount - sale_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_profit += profit

        store_data = store_profit.setdefault(
            sale.store_id,
            {
                "store_id": sale.store_id,
                "store_name": sale.store.name if sale.store else "Sucursal",
                "revenue": Decimal("0"),
                "cost": Decimal("0"),
                "profit": Decimal("0"),
            },
        )
        store_data["revenue"] += sale.total_amount
        store_data["cost"] += sale_cost
        store_data["profit"] += profit

        sale_day = sale.created_at.date()
        if sale_day in window_set:
            sales_trend_map[sale_day] += sale.total_amount

    repair_status_counts: dict[str, int] = defaultdict(int)
    open_repairs = 0
    for order in repairs:
        repair_status_counts[order.status.value] += 1
        if order.status != models.RepairStatus.ENTREGADO:
            open_repairs += 1

    sales_trend = [
        {
            "label": day.strftime("%d/%m"),
            "value": float(sales_trend_map.get(day, Decimal("0"))),
        }
        for day in window_days
    ]

    stock_breakdown = [
        {"label": metric["store_name"], "value": metric["total_units"]}
        for metric in store_metrics
    ]

    profit_breakdown = [
        {
            "label": data["store_name"],
            "value": float(data["profit"]),
        }
        for data in store_profit.values()
        if data["profit"]
    ]

    repair_mix = [
        {"label": status, "value": count}
        for status, count in sorted(repair_status_counts.items())
    ]

    audit_logs_stmt = (
        select(models.AuditLog)
        .order_by(models.AuditLog.created_at.desc())
        .limit(50)
    )
    audit_logs = list(db.scalars(audit_logs_stmt).unique())
    alert_summary = audit_utils.summarize_alerts(audit_logs)
    log_keys = {(log.entity_type, log.entity_id) for log in audit_logs}
    ack_map: dict[tuple[str, str], models.AuditAlertAcknowledgement] = {}
    if log_keys:
        ack_stmt = (
            select(models.AuditAlertAcknowledgement)
            .options(joinedload(models.AuditAlertAcknowledgement.acknowledged_by))
            .where(
                tuple_(
                    models.AuditAlertAcknowledgement.entity_type,
                    models.AuditAlertAcknowledgement.entity_id,
                ).in_(log_keys)
            )
        )
        ack_map = {
            (ack.entity_type, ack.entity_id): ack for ack in db.scalars(ack_stmt)
        }

    highlight_entries: list[dict[str, object]] = []
    pending_highlights: list[audit_utils.HighlightEntry] = []
    acknowledged_highlights = 0
    for entry in alert_summary.highlights:
        acknowledgement = ack_map.get((entry["entity_type"], entry["entity_id"]))
        status = "pending"
        acknowledged_at = None
        acknowledged_by_id = None
        acknowledged_by_name = None
        acknowledged_note = None
        if acknowledgement and acknowledgement.acknowledged_at >= entry["created_at"]:
            status = "acknowledged"
            acknowledged_at = acknowledgement.acknowledged_at
            acknowledged_by_id = acknowledgement.acknowledged_by_id
            if acknowledgement.acknowledged_by is not None:
                acknowledged_by_name = (
                    acknowledgement.acknowledged_by.full_name
                    or acknowledgement.acknowledged_by.username
                )
            acknowledged_note = acknowledgement.note
            acknowledged_highlights += 1
        else:
            pending_highlights.append(entry)

        highlight_entries.append(
            {
                "id": entry["id"],
                "action": entry["action"],
                "created_at": entry["created_at"],
                "severity": entry["severity"],
                "entity_type": entry["entity_type"],
                "entity_id": entry["entity_id"],
                "status": status,
                "acknowledged_at": acknowledged_at,
                "acknowledged_by_id": acknowledged_by_id,
                "acknowledged_by_name": acknowledged_by_name,
                "acknowledged_note": acknowledged_note,
            }
        )

    critical_events: dict[tuple[str, str], datetime] = {}
    for log in audit_logs:
        severity = audit_utils.classify_severity(log.action or "", log.details)
        if severity != "critical":
            continue
        key = (log.entity_type, log.entity_id)
        if key not in critical_events or log.created_at > critical_events[key]:
            critical_events[key] = log.created_at

    acknowledged_entities: list[dict[str, object]] = []
    pending_critical = 0
    for key, last_seen in critical_events.items():
        acknowledgement = ack_map.get(key)
        if acknowledgement and acknowledgement.acknowledged_at >= last_seen:
            acknowledged_entities.append(
                {
                    "entity_type": key[0],
                    "entity_id": key[1],
                    "acknowledged_at": acknowledgement.acknowledged_at,
                    "acknowledged_by_id": acknowledgement.acknowledged_by_id,
                    "acknowledged_by_name": (
                        acknowledgement.acknowledged_by.full_name
                        if acknowledgement.acknowledged_by
                        and acknowledgement.acknowledged_by.full_name
                        else (
                            acknowledgement.acknowledged_by.username
                            if acknowledgement.acknowledged_by
                            else None
                        )
                    ),
                    "note": acknowledgement.note,
                }
            )
        else:
            pending_critical += 1

    acknowledged_entities.sort(key=lambda item: item["acknowledged_at"], reverse=True)

    audit_alerts = {
        "total": alert_summary.total,
        "critical": alert_summary.critical,
        "warning": alert_summary.warning,
        "info": alert_summary.info,
        "has_alerts": alert_summary.has_alerts,
        "pending_count": len([entry for entry in highlight_entries if entry["status"] != "acknowledged"]),
        "acknowledged_count": len(acknowledged_entities) or acknowledged_highlights,
        "highlights": highlight_entries,
        "acknowledged_entities": acknowledged_entities,
    }

    return {
        "totals": {
            "stores": len(stores),
            "devices": total_devices,
            "total_units": total_units,
            "total_value": total_value,
        },
        "top_stores": store_metrics[:5],
        "low_stock_devices": low_stock[:10],
        "global_performance": {
            "total_sales": float(total_sales_amount),
            "sales_count": sales_count,
            "total_stock": total_units,
            "open_repairs": open_repairs,
            "gross_profit": float(total_profit),
        },
        "sales_trend": sales_trend,
        "stock_breakdown": stock_breakdown,
        "repair_mix": repair_mix,
        "profit_breakdown": profit_breakdown,
        "audit_alerts": audit_alerts,
    }


def get_inventory_current_report(
    db: Session, *, store_ids: Iterable[int] | None = None
) -> schemas.InventoryCurrentReport:
    stores = list_inventory_summary(db)
    store_filter = _normalize_store_ids(store_ids)

    report_stores: list[schemas.InventoryCurrentStore] = []
    total_devices = 0
    total_units = 0
    total_value = Decimal("0")

    for store in stores:
        if store_filter and store.id not in store_filter:
            continue
        device_count = len(store.devices)
        store_units = sum(device.quantity for device in store.devices)
        store_value = sum(_device_value(device) for device in store.devices)

        report_stores.append(
            schemas.InventoryCurrentStore(
                store_id=store.id,
                store_name=store.name,
                device_count=device_count,
                total_units=store_units,
                total_value=store_value,
            )
        )

        total_devices += device_count
        total_units += store_units
        total_value += store_value

    totals = schemas.InventoryTotals(
        stores=len(report_stores),
        devices=total_devices,
        total_units=total_units,
        total_value=total_value,
    )

    return schemas.InventoryCurrentReport(stores=report_stores, totals=totals)


def get_inventory_movements_report(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    movement_type: models.MovementType | None = None,
) -> schemas.InventoryMovementsReport:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)

    movement_stmt = (
        select(models.InventoryMovement)
        .options(
            joinedload(models.InventoryMovement.store),
            joinedload(models.InventoryMovement.source_store),
            joinedload(models.InventoryMovement.device),
            joinedload(models.InventoryMovement.performed_by),
        )
        .order_by(models.InventoryMovement.created_at.desc())
    )

    if store_filter:
        movement_stmt = movement_stmt.where(models.InventoryMovement.store_id.in_(store_filter))
    movement_stmt = movement_stmt.where(models.InventoryMovement.created_at >= start_dt)
    movement_stmt = movement_stmt.where(models.InventoryMovement.created_at <= end_dt)
    if movement_type is not None:
        movement_stmt = movement_stmt.where(models.InventoryMovement.movement_type == movement_type)

    movements = list(db.scalars(movement_stmt).unique())

    totals_by_type: dict[models.MovementType, dict[str, Decimal | int]] = {}
    period_map: dict[tuple[date, models.MovementType], dict[str, Decimal | int]] = {}
    total_units = 0
    total_value = Decimal("0")
    report_entries: list[schemas.MovementReportEntry] = []

    for movement in movements:
        value = _movement_value(movement)
        total_units += movement.quantity
        total_value += value

        type_data = totals_by_type.setdefault(
            movement.movement_type,
            {"quantity": 0, "value": Decimal("0")},
        )
        type_data["quantity"] = int(type_data["quantity"]) + movement.quantity
        type_data["value"] = _to_decimal(type_data["value"]) + value

        period_key = (movement.created_at.date(), movement.movement_type)
        period_data = period_map.setdefault(
            period_key,
            {"quantity": 0, "value": Decimal("0")},
        )
        period_data["quantity"] = int(period_data["quantity"]) + movement.quantity
        period_data["value"] = _to_decimal(period_data["value"]) + value

        report_entries.append(
            schemas.MovementReportEntry(
                id=movement.id,
                tipo_movimiento=movement.movement_type,
                cantidad=movement.quantity,
                valor_total=value,
                sucursal_destino_id=movement.store_id,
                sucursal_destino=movement.tienda_destino,
                sucursal_origen_id=movement.source_store_id,
                sucursal_origen=movement.tienda_origen,
                comentario=movement.comment,
                usuario=movement.usuario,
                fecha=movement.created_at,
            )
        )

    period_summaries = [
        schemas.MovementPeriodSummary(
            periodo=period,
            tipo_movimiento=movement_type,
            total_cantidad=int(data["quantity"]),
            total_valor=_to_decimal(data["value"]),
        )
        for (period, movement_type), data in sorted(period_map.items())
    ]

    summary_by_type = [
        schemas.MovementTypeSummary(
            tipo_movimiento=movement_enum,
            total_cantidad=int(totals_by_type.get(movement_enum, {}).get("quantity", 0)),
            total_valor=_to_decimal(totals_by_type.get(movement_enum, {}).get("value", 0)),
        )
        for movement_enum in models.MovementType
    ]

    resumen = schemas.InventoryMovementsSummary(
        total_movimientos=len(movements),
        total_unidades=total_units,
        total_valor=total_value,
        por_tipo=summary_by_type,
    )

    return schemas.InventoryMovementsReport(
        resumen=resumen,
        periodos=period_summaries,
        movimientos=report_entries,
    )


def get_top_selling_products(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    limit: int = 10,
) -> schemas.TopProductsReport:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)

    sold_units = func.sum(models.SaleItem.quantity).label("sold_units")
    total_revenue = func.sum(models.SaleItem.total_line).label("total_revenue")
    estimated_cost = func.sum(
        models.SaleItem.quantity
        * func.coalesce(models.Device.costo_unitario, models.SaleItem.unit_price)
    ).label("total_cost")

    stmt = (
        select(
            models.SaleItem.device_id,
            models.Device.sku,
            models.Device.name.label("device_name"),
            models.Sale.store_id,
            models.Store.name.label("store_name"),
            sold_units,
            total_revenue,
            estimated_cost,
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .where(models.Sale.created_at >= start_dt)
        .where(models.Sale.created_at <= end_dt)
        .group_by(
            models.SaleItem.device_id,
            models.Device.sku,
            models.Device.name,
            models.Sale.store_id,
            models.Store.name,
        )
        .order_by(sold_units.desc(), total_revenue.desc())
        .limit(limit)
    )

    if store_filter:
        stmt = stmt.where(models.Sale.store_id.in_(store_filter))

    rows = list(db.execute(stmt).mappings())

    items: list[schemas.TopProductReportItem] = []
    total_units = 0
    total_income = Decimal("0")

    for row in rows:
        units = int(row["sold_units"] or 0)
        income = _to_decimal(row["total_revenue"])
        cost = _to_decimal(row["total_cost"])
        margin = income - cost

        items.append(
            schemas.TopProductReportItem(
                device_id=row["device_id"],
                sku=row["sku"],
                nombre=row["device_name"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                unidades_vendidas=units,
                ingresos_totales=income,
                margen_estimado=margin,
            )
        )

        total_units += units
        total_income += income

    return schemas.TopProductsReport(
        items=items,
        total_unidades=total_units,
        total_ingresos=total_income,
    )


def get_inventory_value_report(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    categories: Iterable[str] | None = None,
) -> schemas.InventoryValueReport:
    valuations = calculate_inventory_valuation(
        db, store_ids=store_ids, categories=categories
    )

    store_map: dict[int, dict[str, Decimal | str]] = {}

    for entry in valuations:
        store_entry = store_map.setdefault(
            entry.store_id,
            {
                "store_name": entry.store_name,
                "valor_total": Decimal("0"),
                "valor_costo": Decimal("0"),
                "margen_total": Decimal("0"),
            },
        )
        store_entry["valor_total"] = _to_decimal(store_entry["valor_total"]) + _to_decimal(
            entry.valor_total_producto
        )
        store_entry["valor_costo"] = _to_decimal(store_entry["valor_costo"]) + _to_decimal(
            entry.valor_costo_producto
        )
        store_entry["margen_total"] = _to_decimal(store_entry["margen_total"]) + (
            _to_decimal(entry.valor_total_producto) - _to_decimal(entry.valor_costo_producto)
        )

    stores = [
        schemas.InventoryValueStore(
            store_id=store_id,
            store_name=data["store_name"],
            valor_total=_to_decimal(data["valor_total"]),
            valor_costo=_to_decimal(data["valor_costo"]),
            margen_total=_to_decimal(data["margen_total"]),
        )
        for store_id, data in sorted(store_map.items(), key=lambda item: item[1]["store_name"])
    ]

    total_valor = sum((store.valor_total for store in stores), Decimal("0"))
    total_costo = sum((store.valor_costo for store in stores), Decimal("0"))
    total_margen = sum((store.margen_total for store in stores), Decimal("0"))

    totals = schemas.InventoryValueTotals(
        valor_total=total_valor,
        valor_costo=total_costo,
        margen_total=total_margen,
    )

    return schemas.InventoryValueReport(stores=stores, totals=totals)


def calculate_rotation_analytics(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()

    sale_stats = (
        select(
            models.SaleItem.device_id,
            func.sum(models.SaleItem.quantity).label("sold_units"),
            models.Sale.store_id,
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(models.SaleItem.device_id, models.Sale.store_id)
    )
    if store_filter:
        sale_stats = sale_stats.where(models.Sale.store_id.in_(store_filter))
    if start_dt:
        sale_stats = sale_stats.where(models.Sale.created_at >= start_dt)
    if end_dt:
        sale_stats = sale_stats.where(models.Sale.created_at <= end_dt)
    if category:
        sale_stats = sale_stats.where(category_expr == category)

    purchase_stats = (
        select(
            models.PurchaseOrderItem.device_id,
            func.sum(models.PurchaseOrderItem.quantity_received).label("received_units"),
            models.PurchaseOrder.store_id,
        )
        .join(models.PurchaseOrder, models.PurchaseOrder.id == models.PurchaseOrderItem.purchase_order_id)
        .join(models.Device, models.Device.id == models.PurchaseOrderItem.device_id)
        .group_by(models.PurchaseOrderItem.device_id, models.PurchaseOrder.store_id)
    )
    if store_filter:
        purchase_stats = purchase_stats.where(models.PurchaseOrder.store_id.in_(store_filter))
    if start_dt:
        purchase_stats = purchase_stats.where(models.PurchaseOrder.created_at >= start_dt)
    if end_dt:
        purchase_stats = purchase_stats.where(models.PurchaseOrder.created_at <= end_dt)
    if category:
        purchase_stats = purchase_stats.where(category_expr == category)

    sold_map = {row.device_id: int(row.sold_units or 0) for row in db.execute(sale_stats)}
    received_map = {row.device_id: int(row.received_units or 0) for row in db.execute(purchase_stats)}

    device_stmt = (
        select(
            models.Device.id,
            models.Device.sku,
            models.Device.name,
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
        .order_by(models.Store.name.asc(), models.Device.name.asc())
    )
    if store_filter:
        device_stmt = device_stmt.where(models.Device.store_id.in_(store_filter))
    if category:
        device_stmt = device_stmt.where(category_expr == category)

    results: list[dict[str, object]] = []
    for row in db.execute(device_stmt):
        sold_units = sold_map.get(row.id, 0)
        received_units = received_map.get(row.id, 0)
        denominator = received_units if received_units > 0 else max(sold_units, 1)
        rotation_rate = sold_units / denominator if denominator else 0
        results.append(
            {
                "store_id": row.store_id,
                "store_name": row.store_name,
                "device_id": row.id,
                "sku": row.sku,
                "name": row.name,
                "sold_units": sold_units,
                "received_units": received_units,
                "rotation_rate": float(round(rotation_rate, 2)),
            }
        )
    return results


def calculate_aging_analytics(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    now_date = datetime.utcnow().date()
    category_expr = _device_category_expr()
    device_stmt = (
        select(
            models.Device.id,
            models.Device.sku,
            models.Device.name,
            models.Device.fecha_compra,
            models.Device.quantity,
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
    )
    if store_filter:
        device_stmt = device_stmt.where(models.Device.store_id.in_(store_filter))
    if date_from:
        device_stmt = device_stmt.where(models.Device.fecha_compra >= date_from)
    if date_to:
        device_stmt = device_stmt.where(models.Device.fecha_compra <= date_to)
    if category:
        device_stmt = device_stmt.where(category_expr == category)

    metrics: list[dict[str, object]] = []
    for row in db.execute(device_stmt):
        purchase_date = row.fecha_compra
        days_in_stock = (now_date - purchase_date).days if purchase_date else 0
        metrics.append(
            {
                "device_id": row.id,
                "sku": row.sku,
                "name": row.name,
                "store_id": row.store_id,
                "store_name": row.store_name,
                "days_in_stock": max(days_in_stock, 0),
                "quantity": int(row.quantity or 0),
            }
        )
    metrics.sort(key=lambda item: item["days_in_stock"], reverse=True)
    return metrics


def calculate_stockout_forecast(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()

    sales_summary_stmt = (
        select(
            models.SaleItem.device_id,
            models.Sale.store_id,
            func.sum(models.SaleItem.quantity).label("sold_units"),
            func.min(models.Sale.created_at).label("first_sale"),
            func.max(models.Sale.created_at).label("last_sale"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(models.SaleItem.device_id, models.Sale.store_id)
    )
    if store_filter:
        sales_summary_stmt = sales_summary_stmt.where(models.Sale.store_id.in_(store_filter))
    if start_dt:
        sales_summary_stmt = sales_summary_stmt.where(models.Sale.created_at >= start_dt)
    if end_dt:
        sales_summary_stmt = sales_summary_stmt.where(models.Sale.created_at <= end_dt)
    if category:
        sales_summary_stmt = sales_summary_stmt.where(category_expr == category)

    day_column = func.date(models.Sale.created_at)
    daily_sales_stmt = (
        select(
            models.SaleItem.device_id,
            day_column.label("day"),
            func.sum(models.SaleItem.quantity).label("sold_units"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(models.SaleItem.device_id, day_column)
    )
    if store_filter:
        daily_sales_stmt = daily_sales_stmt.where(models.Sale.store_id.in_(store_filter))
    if start_dt:
        daily_sales_stmt = daily_sales_stmt.where(models.Sale.created_at >= start_dt)
    if end_dt:
        daily_sales_stmt = daily_sales_stmt.where(models.Sale.created_at <= end_dt)
    if category:
        daily_sales_stmt = daily_sales_stmt.where(category_expr == category)

    sales_map: dict[int, dict[str, object]] = {}
    for row in db.execute(sales_summary_stmt):
        sales_map[row.device_id] = {
            "sold_units": int(row.sold_units or 0),
            "first_sale": row.first_sale,
            "last_sale": row.last_sale,
            "store_id": int(row.store_id),
        }

    daily_sales_map: defaultdict[int, list[tuple[datetime, float]]] = defaultdict(list)
    for row in db.execute(daily_sales_stmt):
        day: datetime | None = row.day
        if day is None:
            continue
        daily_sales_map[row.device_id].append((day, float(row.sold_units or 0)))

    device_stmt = (
        select(
            models.Device.id,
            models.Device.sku,
            models.Device.name,
            models.Device.quantity,
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
    )
    if store_filter:
        device_stmt = device_stmt.where(models.Device.store_id.in_(store_filter))
    if category:
        device_stmt = device_stmt.where(category_expr == category)

    metrics: list[dict[str, object]] = []
    for row in db.execute(device_stmt):
        stats = sales_map.get(row.id)
        quantity = int(row.quantity or 0)
        daily_points_raw = sorted(
            daily_sales_map.get(row.id, []), key=lambda item: item[0]
        )
        points = [(float(index), value) for index, (_, value) in enumerate(daily_points_raw)]
        slope, intercept, r_squared = _linear_regression(points)
        historical_avg = (
            sum(value for _, value in daily_points_raw) / len(daily_points_raw)
            if daily_points_raw
            else 0.0
        )
        predicted_next = max(0.0, slope * len(points) + intercept) if points else 0.0
        expected_daily = max(historical_avg, predicted_next)

        if stats is None:
            sold_units = 0
        else:
            sold_units = int(stats.get("sold_units", 0))

        if expected_daily <= 0:
            projected_days: int | None = None
        else:
            projected_days = max(int(math.ceil(quantity / expected_daily)), 0)

        if slope > 0.25:
            trend_label = "acelerando"
        elif slope < -0.25:
            trend_label = "desacelerando"
        else:
            trend_label = "estable"

        alert_level: str | None
        if projected_days is None:
            alert_level = None
        elif projected_days <= 3:
            alert_level = "critical"
        elif projected_days <= 7:
            alert_level = "warning"
        else:
            alert_level = "ok"

        metrics.append(
            {
                "device_id": row.id,
                "sku": row.sku,
                "name": row.name,
                "store_id": row.store_id,
                "store_name": row.store_name,
                "average_daily_sales": round(float(expected_daily), 2),
                "projected_days": projected_days,
                "quantity": quantity,
                "trend": trend_label,
                "trend_score": round(float(slope), 4),
                "confidence": round(float(r_squared), 3),
                "alert_level": alert_level,
                "sold_units": sold_units,
            }
        )

    metrics.sort(key=lambda item: (item["projected_days"] is None, item["projected_days"] or 0))
    return metrics


def calculate_store_comparatives(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    rotation = calculate_rotation_analytics(
        db,
        store_ids=store_filter,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    aging = calculate_aging_analytics(
        db,
        store_ids=store_filter,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()
    rotation_totals: dict[int, tuple[float, int]] = {}
    aging_totals: dict[int, tuple[float, int]] = {}

    for item in rotation:
        store_id = int(item["store_id"])
        total, count = rotation_totals.get(store_id, (0.0, 0))
        rotation_totals[store_id] = (total + float(item["rotation_rate"]), count + 1)

    for item in aging:
        store_id_value = item.get("store_id")
        if store_id_value is None:
            continue
        store_id = int(store_id_value)
        total, count = aging_totals.get(store_id, (0.0, 0))
        aging_totals[store_id] = (total + float(item["days_in_stock"]), count + 1)

    rotation_avg = {
        store_id: (total / count if count else 0.0)
        for store_id, (total, count) in rotation_totals.items()
    }
    aging_avg = {
        store_id: (total / count if count else 0.0)
        for store_id, (total, count) in aging_totals.items()
    }

    inventory_stmt = (
        select(
            models.Store.id,
            models.Store.name,
            func.coalesce(func.count(models.Device.id), 0).label("device_count"),
            func.coalesce(func.sum(models.Device.quantity), 0).label("total_units"),
            func.coalesce(
                func.sum(models.Device.quantity * models.Device.unit_price),
                0,
            ).label("inventory_value"),
        )
        .outerjoin(models.Device, models.Device.store_id == models.Store.id)
        .group_by(models.Store.id)
        .order_by(models.Store.name.asc())
    )
    if store_filter:
        inventory_stmt = inventory_stmt.where(models.Store.id.in_(store_filter))
    if category:
        inventory_stmt = inventory_stmt.where(category_expr == category)
    window_start = start_dt or (datetime.utcnow() - timedelta(days=30))
    sales_stmt = (
        select(
            models.Sale.store_id,
            func.coalesce(func.count(models.Sale.id), 0).label("orders"),
            func.coalesce(func.sum(models.Sale.total_amount), 0).label("revenue"),
        )
        .join(models.SaleItem, models.SaleItem.sale_id == models.Sale.id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .where(models.Sale.created_at >= window_start)
        .group_by(models.Sale.store_id)
    )
    if store_filter:
        sales_stmt = sales_stmt.where(models.Sale.store_id.in_(store_filter))
    if end_dt:
        sales_stmt = sales_stmt.where(models.Sale.created_at <= end_dt)
    if category:
        sales_stmt = sales_stmt.where(category_expr == category)
    sales_map: dict[int, dict[str, Decimal]] = {}
    for row in db.execute(sales_stmt):
        sales_map[int(row.store_id)] = {
            "orders": Decimal(row.orders or 0),
            "revenue": Decimal(row.revenue or 0),
        }

    comparatives: list[dict[str, object]] = []
    for row in db.execute(inventory_stmt):
        store_id = int(row.id)
        sales = sales_map.get(store_id, {"orders": Decimal(0), "revenue": Decimal(0)})
        comparatives.append(
            {
                "store_id": store_id,
                "store_name": row.name,
                "device_count": int(row.device_count or 0),
                "total_units": int(row.total_units or 0),
                "inventory_value": float(row.inventory_value or 0),
                "average_rotation": round(rotation_avg.get(store_id, 0.0), 2),
                "average_aging_days": round(aging_avg.get(store_id, 0.0), 1),
                "sales_last_30_days": float(sales["revenue"]),
                "sales_count_last_30_days": int(sales["orders"]),
            }
        )

    comparatives.sort(key=lambda item: item["inventory_value"], reverse=True)
    return comparatives


def calculate_profit_margin(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()
    stmt = (
        select(
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
            func.coalesce(func.sum(models.SaleItem.total_line), 0).label("revenue"),
            func.coalesce(
                func.sum(models.SaleItem.quantity * models.Device.costo_unitario),
                0,
            ).label("cost"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(models.Store.id)
        .order_by(models.Store.name.asc())
    )
    if store_filter:
        stmt = stmt.where(models.Store.id.in_(store_filter))
    if start_dt:
        stmt = stmt.where(models.Sale.created_at >= start_dt)
    if end_dt:
        stmt = stmt.where(models.Sale.created_at <= end_dt)
    if category:
        stmt = stmt.where(category_expr == category)

    metrics: list[dict[str, object]] = []
    for row in db.execute(stmt):
        revenue = Decimal(row.revenue or 0)
        cost = Decimal(row.cost or 0)
        profit = revenue - cost
        margin_percent = float((profit / revenue * 100) if revenue else 0)
        metrics.append(
            {
                "store_id": int(row.store_id),
                "store_name": row.store_name,
                "revenue": float(revenue),
                "cost": float(cost),
                "profit": float(profit),
                "margin_percent": round(margin_percent, 2),
            }
        )

    metrics.sort(key=lambda item: item["profit"], reverse=True)
    return metrics


def calculate_sales_projection(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    horizon_days: int = 30,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()
    lookback_days = max(horizon_days, 30)
    since = start_dt or (datetime.utcnow() - timedelta(days=lookback_days))

    day_bucket = func.date(models.Sale.created_at)
    daily_stmt = (
        select(
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
            day_bucket.label("sale_day"),
            func.coalesce(func.sum(models.SaleItem.quantity), 0).label("units"),
            func.coalesce(func.sum(models.SaleItem.total_line), 0).label("revenue"),
            func.coalesce(func.count(func.distinct(models.Sale.id)), 0).label("orders"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .where(models.Sale.created_at >= since)
        .group_by(
            models.Store.id,
            models.Store.name,
            day_bucket,
        )
        .order_by(models.Store.name.asc())
    )
    if store_filter:
        daily_stmt = daily_stmt.where(models.Store.id.in_(store_filter))
    if end_dt:
        daily_stmt = daily_stmt.where(models.Sale.created_at <= end_dt)
    if category:
        daily_stmt = daily_stmt.where(category_expr == category)

    stores_data: dict[int, dict[str, object]] = {}
    for row in db.execute(daily_stmt):
        store_entry = stores_data.setdefault(
            int(row.store_id),
            {
                "store_name": row.store_name,
                "daily": [],
                "orders": 0,
                "total_units": 0.0,
                "total_revenue": 0.0,
            },
        )
        day_value: datetime | None = row.sale_day
        if day_value is None:
            continue
        units_value = float(row.units or 0)
        revenue_value = float(row.revenue or 0)
        orders_value = int(row.orders or 0)
        store_entry["daily"].append(
            {
                "day": day_value,
                "units": units_value,
                "revenue": revenue_value,
                "orders": orders_value,
            }
        )
        store_entry["orders"] += orders_value
        store_entry["total_units"] += units_value
        store_entry["total_revenue"] += revenue_value

    projections: list[dict[str, object]] = []
    for store_id, payload in stores_data.items():
        daily_points = sorted(payload["daily"], key=lambda item: item["day"])
        if not daily_points:
            continue

        unit_points = [
            (float(index), item["units"])
            for index, item in enumerate(daily_points)
        ]
        revenue_points = [
            (float(index), item["revenue"])
            for index, item in enumerate(daily_points)
        ]
        slope_units, intercept_units, r2_units = _linear_regression(unit_points)
        slope_revenue, intercept_revenue, r2_revenue = _linear_regression(
            revenue_points
        )
        historical_avg_units = (
            payload["total_units"] / len(unit_points) if unit_points else 0.0
        )
        predicted_next_units = (
            max(0.0, slope_units * len(unit_points) + intercept_units)
            if unit_points
            else 0.0
        )
        average_daily_units = max(historical_avg_units, predicted_next_units)
        projected_units = _project_linear_sum(
            slope_units, intercept_units, len(unit_points), horizon_days
        )
        projected_revenue = _project_linear_sum(
            slope_revenue, intercept_revenue, len(revenue_points), horizon_days
        )
        average_ticket = (
            payload["total_revenue"] / payload["total_units"]
            if payload["total_units"] > 0
            else 0.0
        )
        orders = payload["orders"]
        sample_days = len(unit_points)
        confidence = 0.0
        if sample_days > 0:
            coverage = min(1.0, orders / sample_days)
            confidence = max(0.0, min(1.0, (r2_units + coverage) / 2))

        if slope_units > 0.5:
            trend = "creciendo"
        elif slope_units < -0.5:
            trend = "cayendo"
        else:
            trend = "estable"

        projections.append(
            {
                "store_id": store_id,
                "store_name": payload["store_name"],
                "average_daily_units": round(float(average_daily_units), 2),
                "average_ticket": round(float(average_ticket), 2),
                "projected_units": round(float(projected_units), 2),
                "projected_revenue": round(float(projected_revenue), 2),
                "confidence": round(float(confidence), 2),
                "trend": trend,
                "trend_score": round(float(slope_units), 4),
                "revenue_trend_score": round(float(slope_revenue), 4),
                "r2_revenue": round(float(r2_revenue), 3),
            }
        )

    projections.sort(key=lambda item: item["projected_revenue"], reverse=True)
    return projections


def list_analytics_categories(db: Session) -> list[str]:
    category_expr = _device_category_expr()
    stmt = (
        select(func.distinct(category_expr).label("category"))
        .where(category_expr.is_not(None))
        .order_by(category_expr.asc())
    )
    return [row.category for row in db.execute(stmt) if row.category]


def generate_analytics_alerts(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
) -> list[dict[str, object]]:
    alerts: list[dict[str, object]] = []
    forecast = calculate_stockout_forecast(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )
    for item in forecast:
        level = item.get("alert_level")
        if level in {"critical", "warning"}:
            projected_days = item.get("projected_days")
            if projected_days is None:
                continue
            message = (
                f"{item['sku']} en {item['store_name']} se agotará en {projected_days} días"
                if projected_days > 0
                else f"{item['sku']} en {item['store_name']} está agotado"
            )
            alerts.append(
                {
                    "type": "stock",
                    "level": level,
                    "message": message,
                    "store_id": item.get("store_id"),
                    "store_name": item["store_name"],
                    "device_id": item["device_id"],
                    "sku": item["sku"],
                }
            )

    projections = calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        horizon_days=14,
    )
    for item in projections:
        trend = item.get("trend")
        trend_score = float(item.get("trend_score", 0))
        if trend == "cayendo" and trend_score < -0.5:
            level = "warning" if trend_score > -1.0 else "critical"
            message = (
                f"Ventas en {item['store_name']} muestran caída (tendencia {trend_score:.2f})"
            )
            alerts.append(
                {
                    "type": "sales",
                    "level": level,
                    "message": message,
                    "store_id": item["store_id"],
                    "store_name": item["store_name"],
                    "device_id": None,
                    "sku": None,
                }
            )

    alerts.sort(key=lambda alert: (alert["level"] != "critical", alert["level"] != "warning"))
    return alerts


def calculate_realtime_store_widget(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    category: str | None = None,
    low_stock_threshold: int = 5,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    category_expr = _device_category_expr()
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    stores_stmt = select(models.Store.id, models.Store.name, models.Store.inventory_value)
    if store_filter:
        stores_stmt = stores_stmt.where(models.Store.id.in_(store_filter))
    stores_stmt = stores_stmt.order_by(models.Store.name.asc())

    low_stock_stmt = (
        select(models.Device.store_id, func.count(models.Device.id).label("low_stock"))
        .where(models.Device.quantity <= low_stock_threshold)
        .group_by(models.Device.store_id)
    )
    if store_filter:
        low_stock_stmt = low_stock_stmt.where(models.Device.store_id.in_(store_filter))
    if category:
        low_stock_stmt = low_stock_stmt.where(category_expr == category)

    sales_today_stmt = (
        select(
            models.Store.id.label("store_id"),
            func.coalesce(func.sum(models.SaleItem.total_line), 0).label("revenue"),
            func.max(models.Sale.created_at).label("last_sale_at"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .where(models.Sale.created_at >= today_start)
        .group_by(models.Store.id)
    )
    if store_filter:
        sales_today_stmt = sales_today_stmt.where(models.Store.id.in_(store_filter))
    if category:
        sales_today_stmt = sales_today_stmt.where(category_expr == category)

    repairs_stmt = (
        select(
            models.RepairOrder.store_id,
            func.count(models.RepairOrder.id).label("pending"),
        )
        .where(models.RepairOrder.status != models.RepairStatus.ENTREGADO)
        .group_by(models.RepairOrder.store_id)
    )
    if store_filter:
        repairs_stmt = repairs_stmt.where(models.RepairOrder.store_id.in_(store_filter))

    sync_stmt = (
        select(
            models.SyncSession.store_id,
            func.max(models.SyncSession.finished_at).label("last_sync"),
        )
        .group_by(models.SyncSession.store_id)
    )
    if store_filter:
        sync_stmt = sync_stmt.where(models.SyncSession.store_id.in_(store_filter))

    low_stock_map = {
        int(row.store_id): int(row.low_stock or 0)
        for row in db.execute(low_stock_stmt)
    }
    sales_today_map = {
        int(row.store_id): {
            "revenue": float(row.revenue or 0),
            "last_sale_at": row.last_sale_at,
        }
        for row in db.execute(sales_today_stmt)
    }
    repairs_map = {
        int(row.store_id): int(row.pending or 0)
        for row in db.execute(repairs_stmt)
    }
    sync_map: dict[int | None, datetime | None] = {
        row.store_id: row.last_sync for row in db.execute(sync_stmt)
    }
    global_sync = sync_map.get(None)

    projection_map = {
        item["store_id"]: item
        for item in calculate_sales_projection(
            db,
            store_ids=store_ids,
            category=category,
            horizon_days=7,
        )
    }

    widgets: list[dict[str, object]] = []
    for row in db.execute(stores_stmt):
        store_id = int(row.id)
        sales_info = sales_today_map.get(store_id, {"revenue": 0.0, "last_sale_at": None})
        projection = projection_map.get(store_id, {})
        widgets.append(
            {
                "store_id": store_id,
                "store_name": row.name,
                "inventory_value": float(row.inventory_value or 0),
                "sales_today": round(float(sales_info["revenue"]), 2),
                "last_sale_at": sales_info.get("last_sale_at"),
                "low_stock_devices": low_stock_map.get(store_id, 0),
                "pending_repairs": repairs_map.get(store_id, 0),
                "last_sync_at": sync_map.get(store_id) or global_sync,
                "trend": projection.get("trend", "estable"),
                "trend_score": projection.get("trend_score", 0.0),
                "confidence": projection.get("confidence", 0.0),
            }
        )

    return widgets


def record_sync_session(
    db: Session,
    *,
    store_id: int | None,
    mode: models.SyncMode,
    status: models.SyncStatus,
    triggered_by_id: int | None,
    error_message: str | None = None,
    processed_events: int = 0,
    differences_detected: int = 0,
) -> models.SyncSession:
    session = models.SyncSession(
        store_id=store_id,
        mode=mode,
        status=status,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
        error_message=error_message,
        triggered_by_id=triggered_by_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    _log_action(
        db,
        action="sync_session",
        entity_type="store" if store_id else "global",
        entity_id=str(store_id or 0),
        performed_by_id=triggered_by_id,
        details=json.dumps(
            {
                "estado": status.value,
                "modo": mode.value,
                "eventos_procesados": processed_events,
                "diferencias_detectadas": differences_detected,
            },
            ensure_ascii=False,
        ),
    )
    db.commit()
    db.refresh(session)
    return session


def log_sync_discrepancies(
    db: Session,
    discrepancies: Sequence[dict[str, object]],
    *,
    performed_by_id: int | None = None,
) -> None:
    """Registra discrepancias detectadas entre sucursales en la bitácora."""

    if not discrepancies:
        return

    for discrepancy in discrepancies:
        entity_id = str(discrepancy.get("sku") or discrepancy.get("entity", "global"))
        _log_action(
            db,
            action="sync_discrepancy",
            entity_type="inventory",
            entity_id=entity_id,
            performed_by_id=performed_by_id,
            details=json.dumps(discrepancy, ensure_ascii=False, default=str),
        )
    db.commit()


def mark_outbox_entries_sent(
    db: Session,
    entry_ids: Iterable[int],
    *,
    performed_by_id: int | None = None,
) -> list[models.SyncOutbox]:
    """Marca entradas de la cola de sincronización como enviadas y las audita."""

    ids_tuple = tuple({int(entry_id) for entry_id in entry_ids})
    if not ids_tuple:
        return []

    statement = select(models.SyncOutbox).where(models.SyncOutbox.id.in_(ids_tuple))
    entries = list(db.scalars(statement))
    if not entries:
        return []

    now = datetime.utcnow()
    for entry in entries:
        entry.status = models.SyncOutboxStatus.SENT
        entry.last_attempt_at = now
        entry.attempt_count = (entry.attempt_count or 0) + 1
        entry.error_message = None
        entry.updated_at = now
    db.commit()

    for entry in entries:
        db.refresh(entry)
        _log_action(
            db,
            action="sync_outbox_sent",
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            performed_by_id=performed_by_id,
            details=json.dumps(
                {"operation": entry.operation, "status": entry.status.value},
                ensure_ascii=False,
            ),
        )
    db.commit()
    for entry in entries:
        db.refresh(entry)
    return entries


def list_sync_sessions(db: Session, limit: int = 50) -> list[models.SyncSession]:
    statement = (
        select(models.SyncSession)
        .order_by(models.SyncSession.started_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def list_sync_history_by_store(
    db: Session,
    *,
    limit_per_store: int = 5,
) -> list[dict[str, object]]:
    statement = (
        select(models.SyncSession)
        .options(joinedload(models.SyncSession.store))
        .order_by(models.SyncSession.started_at.desc())
    )
    sessions = list(db.scalars(statement).unique())
    grouped: dict[int | None, list[models.SyncSession]] = {}
    for session in sessions:
        key = session.store_id
        bucket = grouped.setdefault(key, [])
        if len(bucket) < limit_per_store:
            bucket.append(session)

    history: list[dict[str, object]] = []
    for store_id, entries in grouped.items():
        if not entries:
            continue
        reference = entries[0]
        store_name = reference.store.name if reference.store else "Global"
        history.append(
            {
                "store_id": store_id,
                "store_name": store_name,
                "sessions": [
                    {
                        "id": entry.id,
                        "mode": entry.mode,
                        "status": entry.status,
                        "started_at": entry.started_at,
                        "finished_at": entry.finished_at,
                        "error_message": entry.error_message,
                    }
                    for entry in entries
                ],
            }
        )

    history.sort(key=lambda item: (item["store_name"].lower(), item["store_id"] or 0))
    return history


def enqueue_sync_outbox(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    operation: str,
    payload: dict[str, object],
    priority: models.SyncOutboxPriority | None = None,
) -> models.SyncOutbox:
    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    resolved_priority = _resolve_outbox_priority(entity_type, priority)
    statement = select(models.SyncOutbox).where(
        models.SyncOutbox.entity_type == entity_type,
        models.SyncOutbox.entity_id == entity_id,
    )
    entry = db.scalars(statement).first()
    if entry is None:
        entry = models.SyncOutbox(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            payload=serialized,
            status=models.SyncOutboxStatus.PENDING,
            priority=resolved_priority,
        )
        db.add(entry)
    else:
        entry.operation = operation
        entry.payload = serialized
        entry.status = models.SyncOutboxStatus.PENDING
        entry.attempt_count = 0
        entry.error_message = None
        entry.last_attempt_at = None
        if _priority_weight(resolved_priority) < _priority_weight(entry.priority):
            entry.priority = resolved_priority
    db.commit()
    db.refresh(entry)
    return entry


def list_sync_outbox(
    db: Session,
    *,
    statuses: Iterable[models.SyncOutboxStatus] | None = None,
    limit: int = 100,
) -> list[models.SyncOutbox]:
    priority_order = case(
        (models.SyncOutbox.priority == models.SyncOutboxPriority.HIGH, 0),
        (models.SyncOutbox.priority == models.SyncOutboxPriority.NORMAL, 1),
        (models.SyncOutbox.priority == models.SyncOutboxPriority.LOW, 2),
        else_=2,
    )
    statement = (
        select(models.SyncOutbox)
        .order_by(priority_order, models.SyncOutbox.updated_at.desc())
        .limit(limit)
    )
    if statuses is not None:
        status_tuple = tuple(statuses)
        if status_tuple:
            statement = statement.where(models.SyncOutbox.status.in_(status_tuple))
    return list(db.scalars(statement))


def reset_outbox_entries(
    db: Session,
    entry_ids: Iterable[int],
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> list[models.SyncOutbox]:
    ids_tuple = tuple({int(entry_id) for entry_id in entry_ids})
    if not ids_tuple:
        return []

    statement = select(models.SyncOutbox).where(models.SyncOutbox.id.in_(ids_tuple))
    entries = list(db.scalars(statement))
    if not entries:
        return []

    now = datetime.utcnow()
    for entry in entries:
        entry.status = models.SyncOutboxStatus.PENDING
        entry.attempt_count = 0
        entry.last_attempt_at = None
        entry.error_message = None
        entry.updated_at = now
    db.commit()
    for entry in entries:
        db.refresh(entry)
        details_payload = {"operation": entry.operation}
        if reason:
            details_payload["reason"] = reason
        _log_action(
            db,
            action="sync_outbox_reset",
            entity_type=entry.entity_type,
            entity_id=str(entry.id),
            performed_by_id=performed_by_id,
            details=json.dumps(details_payload, ensure_ascii=False),
        )
    db.commit()
    refreshed = list(db.scalars(statement))
    return refreshed


def get_sync_outbox_statistics(db: Session) -> list[dict[str, object]]:
    statement = (
        select(
            models.SyncOutbox.entity_type,
            models.SyncOutbox.priority,
            func.count(models.SyncOutbox.id).label("total"),
            func.sum(
                case(
                    (models.SyncOutbox.status == models.SyncOutboxStatus.PENDING, 1),
                    else_=0,
                )
            ).label("pending"),
            func.sum(
                case(
                    (models.SyncOutbox.status == models.SyncOutboxStatus.FAILED, 1),
                    else_=0,
                )
            ).label("failed"),
            func.max(models.SyncOutbox.updated_at).label("latest_update"),
            func.min(
                case(
                    (
                        models.SyncOutbox.status == models.SyncOutboxStatus.PENDING,
                        models.SyncOutbox.created_at,
                    ),
                    else_=None,
                )
            ).label("oldest_pending"),
        )
        .group_by(models.SyncOutbox.entity_type, models.SyncOutbox.priority)
    )
    results: list[dict[str, object]] = []
    for row in db.execute(statement):
        priority = row.priority or models.SyncOutboxPriority.NORMAL
        results.append(
            {
                "entity_type": row.entity_type,
                "priority": priority,
                "total": int(row.total or 0),
                "pending": int(row.pending or 0),
                "failed": int(row.failed or 0),
                "latest_update": row.latest_update,
                "oldest_pending": row.oldest_pending,
            }
        )
    results.sort(key=lambda item: (_priority_weight(item["priority"]), item["entity_type"]))
    return results


def get_store_sync_overview(
    db: Session,
    *,
    store_id: int | None = None,
) -> list[dict[str, object]]:
    stores_stmt = (
        select(
            models.Store.id,
            models.Store.name,
            models.Store.code,
            models.Store.timezone,
            models.Store.inventory_value,
        )
        .order_by(models.Store.name)
    )
    if store_id is not None:
        stores_stmt = stores_stmt.where(models.Store.id == store_id)

    store_rows = list(db.execute(stores_stmt))
    if not store_rows:
        return []

    session_stmt = select(models.SyncSession).order_by(
        models.SyncSession.finished_at.desc(),
        models.SyncSession.started_at.desc(),
    )
    sessions = list(db.scalars(session_stmt))
    latest_by_store: dict[int, models.SyncSession] = {}
    latest_global: models.SyncSession | None = None
    for session in sessions:
        if session.store_id is None:
            if latest_global is None:
                latest_global = session
            continue
        key = int(session.store_id)
        if store_id is not None and key != store_id:
            continue
        if key not in latest_by_store:
            latest_by_store[key] = session

    active_statuses = (
        models.TransferStatus.SOLICITADA,
        models.TransferStatus.EN_TRANSITO,
    )
    transfer_counts: dict[int, int] = defaultdict(int)
    pending_stmt = select(
        models.TransferOrder.origin_store_id,
        models.TransferOrder.destination_store_id,
    ).where(models.TransferOrder.status.in_(active_statuses))
    if store_id is not None:
        pending_stmt = pending_stmt.where(
            (models.TransferOrder.origin_store_id == store_id)
            | (models.TransferOrder.destination_store_id == store_id)
        )
    for row in db.execute(pending_stmt):
        if row.origin_store_id is not None:
            transfer_counts[int(row.origin_store_id)] += 1
        if row.destination_store_id is not None:
            transfer_counts[int(row.destination_store_id)] += 1

    conflict_counts: dict[int, int] = defaultdict(int)
    conflict_stmt = (
        select(models.AuditLog)
        .where(models.AuditLog.action == "sync_discrepancy")
        .order_by(models.AuditLog.created_at.desc())
        .limit(500)
    )
    for log in db.scalars(conflict_stmt):
        try:
            payload = json.loads(log.details or "{}") if log.details else {}
        except json.JSONDecodeError:
            payload = {}
        for key in ("max", "min"):
            entries = payload.get(key) or []
            if not isinstance(entries, list):
                continue
            for entry in entries:
                store_candidate = entry.get("store_id") or entry.get("sucursal_id")
                if store_candidate is None:
                    continue
                try:
                    candidate_id = int(store_candidate)
                except (TypeError, ValueError):
                    continue
                if store_id is not None and candidate_id != store_id:
                    continue
                conflict_counts[candidate_id] += 1

    results: list[dict[str, object]] = []
    now = datetime.utcnow()
    stale_threshold = timedelta(hours=12)
    for row in store_rows:
        key = int(row.id)
        session = latest_by_store.get(key) or latest_global
        last_status = session.status if session else None
        last_mode = session.mode if session else None
        last_timestamp = None
        if session:
            last_timestamp = session.finished_at or session.started_at

        health = schemas.SyncBranchHealth.UNKNOWN
        label = "Sin registros de sincronización"
        if session:
            timestamp_label = (
                last_timestamp.astimezone().strftime("%d/%m/%Y %H:%M")
                if last_timestamp
                else "sin hora"
            )
            if session.status is models.SyncStatus.FAILED:
                health = schemas.SyncBranchHealth.CRITICAL
                label = f"Fallo registrado el {timestamp_label}"
            else:
                health = schemas.SyncBranchHealth.OPERATIVE
                label = f"Actualizado el {timestamp_label}"
                if last_timestamp and now - last_timestamp > stale_threshold:
                    health = schemas.SyncBranchHealth.WARNING
                    label = f"Sincronización antigua ({timestamp_label})"

        pending_transfers = transfer_counts.get(key, 0)
        open_conflicts = conflict_counts.get(key, 0)
        if health is schemas.SyncBranchHealth.OPERATIVE:
            if open_conflicts > 0:
                health = schemas.SyncBranchHealth.WARNING
                label = "Conflictos de inventario pendientes"
            elif pending_transfers > 0:
                health = schemas.SyncBranchHealth.WARNING
                label = "Transferencias activas requieren seguimiento"

        results.append(
            {
                "store_id": key,
                "store_name": row.name,
                "store_code": row.code,
                "timezone": row.timezone,
                "inventory_value": row.inventory_value,
                "last_sync_at": last_timestamp,
                "last_sync_mode": last_mode,
                "last_sync_status": last_status,
                "health": health,
                "health_label": label,
                "pending_transfers": pending_transfers,
                "open_conflicts": open_conflicts,
            }
        )

    return results


def list_sync_conflicts(
    db: Session,
    *,
    store_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    severity: schemas.SyncBranchHealth | None = None,
    limit: int = 100,
) -> list[schemas.SyncConflictLog]:
    statement = (
        select(models.AuditLog)
        .where(models.AuditLog.action == "sync_discrepancy")
        .order_by(models.AuditLog.created_at.desc())
    )
    if date_from is not None:
        statement = statement.where(models.AuditLog.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(models.AuditLog.created_at <= date_to)

    raw_logs = list(db.scalars(statement.limit(max(limit * 3, 200))))
    results: list[schemas.SyncConflictLog] = []

    def _build_store_detail(data: dict[str, object]) -> tuple[schemas.SyncBranchStoreDetail, int | None]:
        candidate = data.get("store_id") or data.get("sucursal_id")
        store_identifier: int | None = None
        if candidate is not None:
            try:
                store_identifier = int(candidate)
            except (TypeError, ValueError):
                store_identifier = None
        quantity_raw = data.get("quantity") or data.get("qty") or 0
        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            quantity = 0
        name = (
            data.get("store_name")
            or data.get("nombre")
            or data.get("store")
            or (f"Sucursal #{store_identifier}" if store_identifier else "Sucursal no identificada")
        )
        detail = schemas.SyncBranchStoreDetail(
            store_id=store_identifier or 0,
            store_name=str(name),
            quantity=quantity,
        )
        return detail, store_identifier

    for log in raw_logs:
        try:
            payload = json.loads(log.details or "{}") if log.details else {}
        except json.JSONDecodeError:
            payload = {}

        sku = str(
            payload.get("sku")
            or payload.get("device_sku")
            or payload.get("entity")
            or f"SYNC-{log.id}"
        )
        product_name = payload.get("product_name") or payload.get("nombre")
        difference_raw = payload.get("diferencia") or payload.get("difference") or 0
        try:
            difference = int(difference_raw)
        except (TypeError, ValueError):
            difference = 0

        stores_max: list[schemas.SyncBranchStoreDetail] = []
        stores_min: list[schemas.SyncBranchStoreDetail] = []
        related_store_ids: set[int] = set()

        for entry in payload.get("max", []) or []:
            if not isinstance(entry, dict):
                continue
            detail, identifier = _build_store_detail(entry)
            stores_max.append(detail)
            if identifier is not None:
                related_store_ids.add(identifier)

        for entry in payload.get("min", []) or []:
            if not isinstance(entry, dict):
                continue
            detail, identifier = _build_store_detail(entry)
            stores_min.append(detail)
            if identifier is not None:
                related_store_ids.add(identifier)

        if store_id is not None and store_id not in related_store_ids:
            continue

        severity_value = schemas.SyncBranchHealth.WARNING
        severity_hint = str(payload.get("severity") or "").lower()
        if severity_hint == "critical" or difference >= 10:
            severity_value = schemas.SyncBranchHealth.CRITICAL

        if severity is not None and severity_value != severity:
            continue

        conflict = schemas.SyncConflictLog(
            id=log.id,
            sku=sku,
            product_name=product_name,
            detected_at=log.created_at,
            difference=difference,
            severity=severity_value,
            stores_max=stores_max,
            stores_min=stores_min,
        )
        results.append(conflict)
        if len(results) >= limit:
            break

    return results


def get_store_membership(db: Session, *, user_id: int, store_id: int) -> models.StoreMembership | None:
    statement = select(models.StoreMembership).where(
        models.StoreMembership.user_id == user_id,
        models.StoreMembership.store_id == store_id,
    )
    return db.scalars(statement).first()


def upsert_store_membership(
    db: Session,
    *,
    user_id: int,
    store_id: int,
    can_create_transfer: bool,
    can_receive_transfer: bool,
) -> models.StoreMembership:
    membership = get_store_membership(db, user_id=user_id, store_id=store_id)
    if membership is None:
        membership = models.StoreMembership(
            user_id=user_id,
            store_id=store_id,
            can_create_transfer=can_create_transfer,
            can_receive_transfer=can_receive_transfer,
        )
        db.add(membership)
    else:
        membership.can_create_transfer = can_create_transfer
        membership.can_receive_transfer = can_receive_transfer
    db.commit()
    db.refresh(membership)
    return membership


def _require_store_permission(
    db: Session,
    *,
    user_id: int,
    store_id: int,
    permission: str,
) -> models.StoreMembership:
    membership = get_store_membership(db, user_id=user_id, store_id=store_id)
    if membership is None:
        raise PermissionError("store_membership_required")
    if permission == "create" and not membership.can_create_transfer:
        raise PermissionError("store_create_forbidden")
    if permission == "receive" and not membership.can_receive_transfer:
        raise PermissionError("store_receive_forbidden")
    return membership


def _user_can_override_transfer(
    db: Session,
    *,
    user_id: int,
    store_id: int,
) -> bool:
    user = get_user(db, user_id)
    user_roles = {assignment.role.name for assignment in user.roles}
    if ADMIN in user_roles:
        return True
    if GERENTE in user_roles and user.store_id == store_id:
        return True
    return False


def list_store_memberships(db: Session, store_id: int) -> list[models.StoreMembership]:
    statement = (
        select(models.StoreMembership)
        .options(joinedload(models.StoreMembership.user))
        .where(models.StoreMembership.store_id == store_id)
        .order_by(models.StoreMembership.user_id.asc())
    )
    return list(db.scalars(statement))


def create_transfer_order(
    db: Session,
    payload: schemas.TransferOrderCreate,
    *,
    requested_by_id: int,
) -> models.TransferOrder:
    if payload.origin_store_id == payload.destination_store_id:
        raise ValueError("transfer_same_store")

    origin_store = get_store(db, payload.origin_store_id)
    destination_store = get_store(db, payload.destination_store_id)

    try:
        _require_store_permission(
            db,
            user_id=requested_by_id,
            store_id=origin_store.id,
            permission="create",
        )
    except PermissionError:
        normalized_reason = (payload.reason or "").strip()
        if len(normalized_reason) < 5 or not _user_can_override_transfer(
            db, user_id=requested_by_id, store_id=origin_store.id
        ):
            raise

    if not payload.items:
        raise ValueError("transfer_items_required")

    order = models.TransferOrder(
        origin_store=origin_store,
        destination_store=destination_store,
        status=models.TransferStatus.SOLICITADA,
        requested_by_id=requested_by_id,
        reason=payload.reason,
    )
    db.add(order)
    db.flush()

    for item in payload.items:
        device = get_device(db, origin_store.id, item.device_id)
        if item.quantity <= 0:
            raise ValueError("transfer_invalid_quantity")
        order_item = models.TransferOrderItem(
            transfer_order=order,
            device=device,
            quantity=item.quantity,
        )
        db.add(order_item)

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="transfer_created",
        entity_type="transfer_order",
        entity_id=str(order.id),
        performed_by_id=requested_by_id,
        details=json.dumps({
            "origin": origin_store.id,
            "destination": destination_store.id,
            "reason": payload.reason,
        }),
    )
    db.commit()
    db.refresh(order)
    return order


def get_transfer_order(db: Session, transfer_id: int) -> models.TransferOrder:
    statement = (
        select(models.TransferOrder)
        .options(
            joinedload(models.TransferOrder.items).joinedload(models.TransferOrderItem.device),
            joinedload(models.TransferOrder.origin_store),
            joinedload(models.TransferOrder.destination_store),
        )
        .where(models.TransferOrder.id == transfer_id)
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("transfer_not_found") from exc


def dispatch_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
) -> models.TransferOrder:
    order = get_transfer_order(db, transfer_id)
    if order.status not in {models.TransferStatus.SOLICITADA}:
        raise ValueError("transfer_invalid_transition")

    _require_store_permission(
        db,
        user_id=performed_by_id,
        store_id=order.origin_store_id,
        permission="create",
    )

    order.status = models.TransferStatus.EN_TRANSITO
    order.dispatched_by_id = performed_by_id
    order.dispatched_at = datetime.utcnow()
    order.reason = reason or order.reason

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="transfer_dispatched",
        entity_type="transfer_order",
        entity_id=str(order.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"status": order.status.value, "reason": reason}),
    )
    db.commit()
    db.refresh(order)
    return order


def _apply_transfer_reception(
    db: Session,
    order: models.TransferOrder,
    *,
    performed_by_id: int,
) -> None:
    for item in order.items:
        device = item.device
        if device.store_id != order.origin_store_id:
            raise ValueError("transfer_device_mismatch")
        if item.quantity <= 0:
            raise ValueError("transfer_invalid_quantity")
        if device.quantity < item.quantity:
            raise ValueError("transfer_insufficient_stock")

        if (device.imei or device.serial) and device.quantity != item.quantity:
            raise ValueError("transfer_requires_full_unit")

        if device.imei or device.serial:
            device.store_id = order.destination_store_id
        else:
            device.quantity -= item.quantity
            destination_statement = select(models.Device).where(
                models.Device.store_id == order.destination_store_id,
                models.Device.sku == device.sku,
            )
            destination_device = db.scalars(destination_statement).first()
            if destination_device is None:
                clone = models.Device(
                    store_id=order.destination_store_id,
                    sku=device.sku,
                    name=device.name,
                    quantity=item.quantity,
                    unit_price=device.unit_price,
                    marca=device.marca,
                    modelo=device.modelo,
                    color=device.color,
                    capacidad_gb=device.capacidad_gb,
                    estado_comercial=device.estado_comercial,
                    proveedor=device.proveedor,
                    costo_unitario=device.costo_unitario,
                    margen_porcentaje=device.margen_porcentaje,
                    garantia_meses=device.garantia_meses,
                    lote=device.lote,
                    fecha_compra=device.fecha_compra,
                )
                db.add(clone)
            else:
                destination_device.quantity += item.quantity

    _recalculate_store_inventory_value(db, order.origin_store_id)
    _recalculate_store_inventory_value(db, order.destination_store_id)


def receive_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
) -> models.TransferOrder:
    order = get_transfer_order(db, transfer_id)
    if order.status not in {models.TransferStatus.SOLICITADA, models.TransferStatus.EN_TRANSITO}:
        raise ValueError("transfer_invalid_transition")

    _require_store_permission(
        db,
        user_id=performed_by_id,
        store_id=order.destination_store_id,
        permission="receive",
    )

    _apply_transfer_reception(db, order, performed_by_id=performed_by_id)

    order.status = models.TransferStatus.RECIBIDA
    order.received_by_id = performed_by_id
    order.received_at = datetime.utcnow()
    order.reason = reason or order.reason

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="transfer_received",
        entity_type="transfer_order",
        entity_id=str(order.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"status": order.status.value, "reason": reason}),
    )
    db.commit()
    db.refresh(order)
    return order


def cancel_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
) -> models.TransferOrder:
    order = get_transfer_order(db, transfer_id)
    if order.status in {models.TransferStatus.RECIBIDA, models.TransferStatus.CANCELADA}:
        raise ValueError("transfer_invalid_transition")

    _require_store_permission(
        db,
        user_id=performed_by_id,
        store_id=order.origin_store_id,
        permission="create",
    )

    order.status = models.TransferStatus.CANCELADA
    order.cancelled_by_id = performed_by_id
    order.cancelled_at = datetime.utcnow()
    order.reason = reason or order.reason

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="transfer_cancelled",
        entity_type="transfer_order",
        entity_id=str(order.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"status": order.status.value, "reason": reason}),
    )
    db.commit()
    db.refresh(order)
    return order


def list_transfer_orders(
    db: Session,
    *,
    store_id: int | None = None,
    origin_store_id: int | None = None,
    destination_store_id: int | None = None,
    status: models.TransferStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int | None = 50,
) -> list[models.TransferOrder]:
    statement = (
        select(models.TransferOrder)
        .options(
            joinedload(models.TransferOrder.items).joinedload(models.TransferOrderItem.device),
            joinedload(models.TransferOrder.origin_store),
            joinedload(models.TransferOrder.destination_store),
            joinedload(models.TransferOrder.requested_by),
            joinedload(models.TransferOrder.dispatched_by),
            joinedload(models.TransferOrder.received_by),
            joinedload(models.TransferOrder.cancelled_by),
        )
        .order_by(models.TransferOrder.created_at.desc())
    )
    if store_id is not None:
        statement = statement.where(
            (models.TransferOrder.origin_store_id == store_id)
            | (models.TransferOrder.destination_store_id == store_id)
        )
    if origin_store_id is not None:
        statement = statement.where(models.TransferOrder.origin_store_id == origin_store_id)
    if destination_store_id is not None:
        statement = statement.where(models.TransferOrder.destination_store_id == destination_store_id)
    if status is not None:
        statement = statement.where(models.TransferOrder.status == status)
    if date_from is not None:
        statement = statement.where(models.TransferOrder.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(models.TransferOrder.created_at <= date_to)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def count_users(db: Session) -> int:
    return db.scalar(select(func.count(models.User.id))) or 0


def create_backup_job(
    db: Session,
    *,
    mode: models.BackupMode,
    pdf_path: str,
    archive_path: str,
    json_path: str,
    sql_path: str,
    config_path: str,
    metadata_path: str,
    critical_directory: str,
    components: list[str],
    total_size_bytes: int,
    notes: str | None,
    triggered_by_id: int | None,
) -> models.BackupJob:
    job = models.BackupJob(
        mode=mode,
        pdf_path=pdf_path,
        archive_path=archive_path,
        json_path=json_path,
        sql_path=sql_path,
        config_path=config_path,
        metadata_path=metadata_path,
        critical_directory=critical_directory,
        components=components,
        total_size_bytes=total_size_bytes,
        notes=notes,
        triggered_by_id=triggered_by_id,
    )
    db.add(job)
    db.flush()

    componentes = ",".join(components)
    detalles = (
        f"modo={mode.value}; tamaño={total_size_bytes}; componentes={componentes}; archivos={archive_path}"
    )
    _log_action(
        db,
        action="backup_generated",
        entity_type="backup",
        entity_id=str(job.id),
        performed_by_id=triggered_by_id,
        details=detalles,
    )
    db.commit()
    db.refresh(job)
    return job


def get_backup_job(db: Session, backup_id: int) -> models.BackupJob | None:
    return db.get(models.BackupJob, backup_id)


def register_backup_restore(
    db: Session,
    *,
    backup_id: int,
    triggered_by_id: int | None,
    components: list[str],
    destination: str,
    applied_database: bool,
) -> None:
    detalles = (
        f"componentes={','.join(components)}; destino={destination}; aplicar_db={applied_database}"
    )
    _log_action(
        db,
        action="backup_restored",
        entity_type="backup",
        entity_id=str(backup_id),
        performed_by_id=triggered_by_id,
        details=detalles,
    )


def _purchase_record_statement():
    return (
        select(models.Compra)
        .options(
            joinedload(models.Compra.proveedor),
            joinedload(models.Compra.usuario),
            joinedload(models.Compra.detalles).joinedload(models.DetalleCompra.producto),
        )
        .order_by(models.Compra.fecha.desc(), models.Compra.id_compra.desc())
    )


def _apply_purchase_record_filters(
    statement,
    *,
    proveedor_id: int | None,
    usuario_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    estado: str | None,
    query: str | None,
):
    if proveedor_id is not None:
        statement = statement.where(models.Compra.proveedor_id == proveedor_id)
    if usuario_id is not None:
        statement = statement.where(models.Compra.usuario_id == usuario_id)
    if date_from is not None:
        statement = statement.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        statement = statement.where(models.Compra.fecha <= date_to)
    if estado is not None:
        statement = statement.where(func.lower(models.Compra.estado) == estado.lower())
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.join(models.Proveedor).where(
            func.lower(models.Proveedor.nombre).like(normalized)
        )
    return statement


def _fetch_purchase_records(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
    limit: int | None = 100,
    offset: int = 0,
) -> list[models.Compra]:
    statement = _purchase_record_statement()
    statement = _apply_purchase_record_filters(
        statement,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado,
        query=query,
    )
    if limit is not None:
        statement = statement.limit(limit)
    if offset:
        statement = statement.offset(offset)
    return list(db.scalars(statement).unique())


def _build_purchase_record_response(purchase: models.Compra) -> schemas.PurchaseRecordResponse:
    vendor_name = (
        purchase.proveedor.nombre if purchase.proveedor else f"Proveedor #{purchase.proveedor_id}"
    )
    user_name = None
    if purchase.usuario:
        user_name = purchase.usuario.full_name or purchase.usuario.username

    items = []
    for detail in purchase.detalles:
        product_name = detail.producto.name if detail.producto else None
        items.append(
            schemas.PurchaseRecordItemResponse(
                id_detalle=detail.id_detalle,
                producto_id=detail.producto_id,
                cantidad=detail.cantidad,
                costo_unitario=detail.costo_unitario,
                subtotal=detail.subtotal,
                producto_nombre=product_name,
            )
        )

    subtotal_value = purchase.total - purchase.impuesto
    return schemas.PurchaseRecordResponse(
        id_compra=purchase.id_compra,
        proveedor_id=purchase.proveedor_id,
        proveedor_nombre=vendor_name,
        usuario_id=purchase.usuario_id,
        usuario_nombre=user_name,
        fecha=purchase.fecha,
        forma_pago=purchase.forma_pago,
        estado=purchase.estado,
        subtotal=subtotal_value,
        impuesto=purchase.impuesto,
        total=purchase.total,
        items=items,
    )


def list_purchase_records(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[schemas.PurchaseRecordResponse]:
    purchases = _fetch_purchase_records(
        db,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado,
        query=query,
        limit=limit,
        offset=offset,
    )
    return [_build_purchase_record_response(purchase) for purchase in purchases]


def get_purchase_record(db: Session, record_id: int) -> schemas.PurchaseRecordResponse:
    statement = _purchase_record_statement().where(models.Compra.id_compra == record_id)
    purchase = db.scalars(statement).unique().first()
    if purchase is None:
        raise LookupError("purchase_record_not_found")
    return _build_purchase_record_response(purchase)


def create_purchase_record(
    db: Session,
    payload: schemas.PurchaseRecordCreate,
    *,
    performed_by_id: int,
    reason: str | None = None,
) -> schemas.PurchaseRecordResponse:
    if not payload.items:
        raise ValueError("purchase_record_items_required")

    vendor = get_purchase_vendor(db, payload.proveedor_id)
    subtotal_total = Decimal("0")
    purchase = models.Compra(
        proveedor_id=vendor.id_proveedor,
        usuario_id=performed_by_id,
        fecha=payload.fecha or datetime.utcnow(),
        total=Decimal("0"),
        impuesto=Decimal("0"),
        forma_pago=payload.forma_pago,
        estado=payload.estado or "REGISTRADA",
    )
    db.add(purchase)
    db.flush()

    for item in payload.items:
        if item.cantidad <= 0:
            raise ValueError("purchase_record_invalid_quantity")
        if item.costo_unitario < 0:
            raise ValueError("purchase_record_invalid_cost")

        device = get_device_global(db, item.producto_id)
        unit_cost = _to_decimal(item.costo_unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal = (
            unit_cost * _to_decimal(item.cantidad)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        db.add(
            models.DetalleCompra(
                compra_id=purchase.id_compra,
                producto_id=device.id,
                cantidad=item.cantidad,
                costo_unitario=unit_cost,
                subtotal=subtotal,
            )
        )
        subtotal_total += subtotal

    tax_rate = _to_decimal(payload.impuesto_tasa)
    impuesto = (subtotal_total * tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (subtotal_total + impuesto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    purchase.total = total
    purchase.impuesto = impuesto

    db.commit()

    _log_action(
        db,
        action="purchase_record_created",
        entity_type="purchase_record",
        entity_id=str(purchase.id_compra),
        performed_by_id=performed_by_id,
        details=json.dumps(
            {
                "proveedor_id": vendor.id_proveedor,
                "total": float(total),
                "impuesto": float(impuesto),
                "motivo": reason,
            }
        ),
    )
    db.commit()

    return get_purchase_record(db, purchase.id_compra)


def list_purchase_records_for_report(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
) -> list[models.Compra]:
    return _fetch_purchase_records(
        db,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        date_from=date_from,
        date_to=date_to,
        estado=estado,
        query=query,
        limit=None,
    )


def list_vendor_purchase_history(
    db: Session,
    vendor_id: int,
    *,
    limit: int = 20,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> schemas.PurchaseVendorHistory:
    vendor = get_purchase_vendor(db, vendor_id)
    purchases = _fetch_purchase_records(
        db,
        proveedor_id=vendor.id_proveedor,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    records = [_build_purchase_record_response(purchase) for purchase in purchases]

    summary_stmt = select(
        func.coalesce(func.sum(models.Compra.total), 0),
        func.coalesce(func.sum(models.Compra.impuesto), 0),
        func.count(models.Compra.id_compra),
        func.max(models.Compra.fecha),
    ).where(models.Compra.proveedor_id == vendor.id_proveedor)
    if date_from is not None:
        summary_stmt = summary_stmt.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        summary_stmt = summary_stmt.where(models.Compra.fecha <= date_to)
    total_value, tax_value, count_value, last_purchase = db.execute(summary_stmt).one()

    vendor_response = schemas.PurchaseVendorResponse(
        id_proveedor=vendor.id_proveedor,
        nombre=vendor.nombre,
        telefono=vendor.telefono,
        correo=vendor.correo,
        direccion=vendor.direccion,
        tipo=vendor.tipo,
        notas=vendor.notas,
        estado=vendor.estado,
        total_compras=_to_decimal(total_value or 0),
        total_impuesto=_to_decimal(tax_value or 0),
        compras_registradas=int(count_value or 0),
        ultima_compra=last_purchase,
    )

    return schemas.PurchaseVendorHistory(
        proveedor=vendor_response,
        compras=records,
        total=_to_decimal(total_value or 0),
        impuesto=_to_decimal(tax_value or 0),
        registros=int(count_value or 0),
    )


def get_purchase_statistics(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    top_limit: int = 5,
) -> schemas.PurchaseStatistics:
    base_stmt = select(
        func.count(models.Compra.id_compra),
        func.coalesce(func.sum(models.Compra.total), 0),
        func.coalesce(func.sum(models.Compra.impuesto), 0),
    )
    if date_from is not None:
        base_stmt = base_stmt.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        base_stmt = base_stmt.where(models.Compra.fecha <= date_to)
    total_count, total_amount, total_tax = db.execute(base_stmt).one()

    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""
    if dialect_name == "sqlite":
        month_expression = func.strftime("%Y-%m-01", models.Compra.fecha)
    else:
        month_expression = func.date_trunc("month", models.Compra.fecha)

    monthly_stmt = select(
        month_expression.label("mes"),
        func.coalesce(func.sum(models.Compra.total), 0).label("total"),
    )
    if date_from is not None:
        monthly_stmt = monthly_stmt.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        monthly_stmt = monthly_stmt.where(models.Compra.fecha <= date_to)
    monthly_stmt = monthly_stmt.group_by("mes").order_by("mes")
    monthly_rows = db.execute(monthly_stmt).all()
    monthly_totals: list[schemas.DashboardChartPoint] = []
    for row in monthly_rows:
        month_value = row.mes
        if isinstance(month_value, str):
            label = month_value[:7]
        else:
            label = month_value.strftime("%Y-%m")
        monthly_totals.append(
            schemas.DashboardChartPoint(
                label=label,
                value=float(row.total),
            )
        )

    top_vendors_stmt = (
        select(
            models.Proveedor.id_proveedor,
            models.Proveedor.nombre,
            func.coalesce(func.sum(models.Compra.total), 0).label("total"),
            func.count(models.Compra.id_compra).label("ordenes"),
        )
        .join(models.Compra, models.Compra.proveedor_id == models.Proveedor.id_proveedor)
    )
    if date_from is not None:
        top_vendors_stmt = top_vendors_stmt.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        top_vendors_stmt = top_vendors_stmt.where(models.Compra.fecha <= date_to)
    top_vendors_stmt = (
        top_vendors_stmt.group_by(models.Proveedor.id_proveedor, models.Proveedor.nombre)
        .order_by(func.sum(models.Compra.total).desc())
        .limit(top_limit)
    )
    vendor_rows = db.execute(top_vendors_stmt).all()
    top_vendors = [
        schemas.PurchaseVendorRanking(
            vendor_id=row.id_proveedor,
            vendor_name=row.nombre,
            total=_to_decimal(row.total),
            orders=int(row.ordenes or 0),
        )
        for row in vendor_rows
    ]

    top_users_stmt = (
        select(
            models.User.id,
            func.coalesce(models.User.full_name, models.User.username).label("nombre"),
            func.coalesce(func.sum(models.Compra.total), 0).label("total"),
            func.count(models.Compra.id_compra).label("ordenes"),
        )
        .join(models.Compra, models.Compra.usuario_id == models.User.id)
    )
    if date_from is not None:
        top_users_stmt = top_users_stmt.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        top_users_stmt = top_users_stmt.where(models.Compra.fecha <= date_to)
    top_users_stmt = (
        top_users_stmt.group_by(models.User.id, models.User.full_name, models.User.username)
        .order_by(func.sum(models.Compra.total).desc())
        .limit(top_limit)
    )
    user_rows = db.execute(top_users_stmt).all()
    top_users = [
        schemas.PurchaseUserRanking(
            user_id=row.id,
            user_name=row.nombre,
            total=_to_decimal(row.total),
            orders=int(row.ordenes or 0),
        )
        for row in user_rows
    ]

    return schemas.PurchaseStatistics(
        updated_at=datetime.utcnow(),
        compras_registradas=int(total_count or 0),
        total=_to_decimal(total_amount or 0),
        impuesto=_to_decimal(total_tax or 0),
        monthly_totals=monthly_totals,
        top_vendors=top_vendors,
        top_users=top_users,
    )


def list_purchase_orders(
    db: Session, *, store_id: int | None = None, limit: int = 50
) -> list[models.PurchaseOrder]:
    statement = (
        select(models.PurchaseOrder)
        .options(
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.returns),
        )
        .order_by(models.PurchaseOrder.created_at.desc())
        .limit(limit)
    )
    if store_id is not None:
        statement = statement.where(models.PurchaseOrder.store_id == store_id)
    return list(db.scalars(statement).unique())


def get_purchase_order(db: Session, order_id: int) -> models.PurchaseOrder:
    statement = (
        select(models.PurchaseOrder)
        .where(models.PurchaseOrder.id == order_id)
        .options(
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.returns),
        )
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("purchase_not_found") from exc


def create_purchase_order(
    db: Session,
    payload: schemas.PurchaseOrderCreate,
    *,
    created_by_id: int | None = None,
) -> models.PurchaseOrder:
    if not payload.items:
        raise ValueError("purchase_items_required")

    get_store(db, payload.store_id)

    order = models.PurchaseOrder(
        store_id=payload.store_id,
        supplier=payload.supplier,
        notes=payload.notes,
        created_by_id=created_by_id,
    )
    db.add(order)
    db.flush()

    for item in payload.items:
        if item.quantity_ordered <= 0:
            raise ValueError("purchase_invalid_quantity")
        if item.unit_cost < 0:
            raise ValueError("purchase_invalid_quantity")

        device = get_device(db, payload.store_id, item.device_id)
        order_item = models.PurchaseOrderItem(
            purchase_order_id=order.id,
            device_id=device.id,
            quantity_ordered=item.quantity_ordered,
            unit_cost=_to_decimal(item.unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )
        db.add(order_item)

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="purchase_order_created",
        entity_type="purchase_order",
        entity_id=str(order.id),
        performed_by_id=created_by_id,
        details=json.dumps({"store_id": order.store_id, "supplier": order.supplier}),
    )
    db.commit()
    db.refresh(order)
    enqueue_sync_outbox(
        db,
        entity_type="purchase_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_purchase_order_payload(order),
    )
    return order


def _build_purchase_movement_comment(
    action: str,
    order: models.PurchaseOrder,
    device: models.Device,
    reason: str | None,
) -> str:
    """Genera una descripción legible para los movimientos de compras."""

    parts: list[str] = [action, f"OC #{order.id}", f"Proveedor: {order.supplier}"]
    if device.imei:
        parts.append(f"IMEI: {device.imei}")
    if device.serial:
        parts.append(f"Serie: {device.serial}")
    if reason:
        normalized_reason = reason.strip()
        if normalized_reason:
            parts.append(normalized_reason)
    comment = " | ".join(part for part in parts if part)
    return comment[:255]


def receive_purchase_order(
    db: Session,
    order_id: int,
    payload: schemas.PurchaseReceiveRequest,
    *,
    received_by_id: int,
    reason: str | None = None,
) -> models.PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order.status in {models.PurchaseStatus.CANCELADA, models.PurchaseStatus.COMPLETADA}:
        raise ValueError("purchase_not_receivable")
    if not payload.items:
        raise ValueError("purchase_items_required")

    items_by_device = {item.device_id: item for item in order.items}
    reception_details: dict[str, int] = {}

    for receive_item in payload.items:
        order_item = items_by_device.get(receive_item.device_id)
        if order_item is None:
            raise LookupError("purchase_item_not_found")
        pending = order_item.quantity_ordered - order_item.quantity_received
        if receive_item.quantity <= 0 or receive_item.quantity > pending:
            raise ValueError("purchase_invalid_quantity")

        order_item.quantity_received += receive_item.quantity

        device = get_device(db, order.store_id, order_item.device_id)
        device.proveedor = order.supplier
        current_quantity = device.quantity
        new_quantity = current_quantity + receive_item.quantity
        current_cost_total = _to_decimal(device.costo_unitario) * _to_decimal(current_quantity)
        incoming_cost_total = _to_decimal(order_item.unit_cost) * _to_decimal(receive_item.quantity)
        divisor = _to_decimal(new_quantity or 1)
        average_cost = (current_cost_total + incoming_cost_total) / divisor
        device.quantity = new_quantity
        device.costo_unitario = average_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        _recalculate_sale_price(device)

        db.add(
            models.InventoryMovement(
                store_id=order.store_id,
                source_store_id=None,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=receive_item.quantity,
                comment=_build_purchase_movement_comment(
                    "Recepción OC",
                    order,
                    device,
                    reason,
                ),
                unit_cost=order_item.unit_cost,
                performed_by_id=received_by_id,
            )
        )
        reception_details[str(device.id)] = receive_item.quantity

    if all(item.quantity_received == item.quantity_ordered for item in order.items):
        order.status = models.PurchaseStatus.COMPLETADA
        order.closed_at = datetime.utcnow()
    else:
        order.status = models.PurchaseStatus.PARCIAL

    db.commit()
    db.refresh(order)
    _recalculate_store_inventory_value(db, order.store_id)

    _log_action(
        db,
        action="purchase_order_received",
        entity_type="purchase_order",
        entity_id=str(order.id),
        performed_by_id=received_by_id,
        details=json.dumps({"items": reception_details, "status": order.status.value}),
    )
    db.commit()
    db.refresh(order)
    enqueue_sync_outbox(
        db,
        entity_type="purchase_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_purchase_order_payload(order),
    )
    return order


def _revert_purchase_inventory(
    db: Session,
    order: models.PurchaseOrder,
    *,
    cancelled_by_id: int,
    reason: str | None,
) -> dict[str, int]:
    """Revierte el inventario recibido cuando se cancela una compra."""

    reversal_details: dict[str, int] = {}
    adjustments_performed = False

    for order_item in order.items:
        received_qty = order_item.quantity_received
        if received_qty <= 0:
            continue

        device = get_device(db, order.store_id, order_item.device_id)
        if device.quantity < received_qty:
            raise ValueError("purchase_cancellation_insufficient_stock")

        current_quantity = device.quantity
        current_cost_total = _to_decimal(device.costo_unitario) * _to_decimal(current_quantity)
        outgoing_cost_total = _to_decimal(order_item.unit_cost) * _to_decimal(received_qty)
        remaining_quantity = current_quantity - received_qty
        remaining_cost_total = current_cost_total - outgoing_cost_total
        if remaining_cost_total < Decimal("0.00"):
            remaining_cost_total = Decimal("0.00")

        device.quantity = remaining_quantity
        if remaining_quantity > 0:
            divisor = _to_decimal(remaining_quantity)
            new_average = remaining_cost_total / divisor
            device.costo_unitario = new_average.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            device.costo_unitario = Decimal("0.00")

        _recalculate_sale_price(device)

        db.add(
            models.InventoryMovement(
                store_id=order.store_id,
                source_store_id=order.store_id,
                device_id=device.id,
                movement_type=models.MovementType.OUT,
                quantity=received_qty,
                comment=_build_purchase_movement_comment(
                    "Reversión OC",
                    order,
                    device,
                    reason,
                ),
                unit_cost=order_item.unit_cost,
                performed_by_id=cancelled_by_id,
            )
        )

        reversal_details[str(device.id)] = received_qty
        order_item.quantity_received = 0
        adjustments_performed = True

    if adjustments_performed:
        _recalculate_store_inventory_value(db, order.store_id)

    return reversal_details


def cancel_purchase_order(
    db: Session,
    order_id: int,
    *,
    cancelled_by_id: int,
    reason: str | None = None,
) -> models.PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order.status == models.PurchaseStatus.CANCELADA:
        raise ValueError("purchase_not_cancellable")

    reversal_details = _revert_purchase_inventory(
        db,
        order,
        cancelled_by_id=cancelled_by_id,
        reason=reason,
    )

    order.status = models.PurchaseStatus.CANCELADA
    order.closed_at = datetime.utcnow()
    if reason:
        order.notes = (order.notes or "") + f" | Cancelación: {reason}" if order.notes else reason

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="purchase_order_cancelled",
        entity_type="purchase_order",
        entity_id=str(order.id),
        performed_by_id=cancelled_by_id,
        details=json.dumps(
            {
                "status": order.status.value,
                "reason": reason,
                "reversed_items": reversal_details,
            }
        ),
    )
    db.commit()
    db.refresh(order)
    enqueue_sync_outbox(
        db,
        entity_type="purchase_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_purchase_order_payload(order),
    )
    return order


def register_purchase_return(
    db: Session,
    order_id: int,
    payload: schemas.PurchaseReturnCreate,
    *,
    processed_by_id: int,
    reason: str | None = None,
) -> models.PurchaseReturn:
    order = get_purchase_order(db, order_id)
    order_item = next((item for item in order.items if item.device_id == payload.device_id), None)
    if order_item is None:
        raise LookupError("purchase_item_not_found")
    if payload.quantity <= 0:
        raise ValueError("purchase_invalid_quantity")

    received_total = order_item.quantity_received
    returned_total = sum(ret.quantity for ret in order.returns if ret.device_id == payload.device_id)
    if payload.quantity > received_total - returned_total:
        raise ValueError("purchase_return_exceeds_received")

    device = get_device(db, order.store_id, payload.device_id)
    if device.quantity < payload.quantity:
        raise ValueError("purchase_return_insufficient_stock")
    device.quantity -= payload.quantity

    order_cost = _to_decimal(order_item.unit_cost)
    current_quantity = device.quantity + payload.quantity
    current_cost_total = _to_decimal(device.costo_unitario) * _to_decimal(current_quantity)
    remaining_cost_total = current_cost_total - (order_cost * _to_decimal(payload.quantity))
    if remaining_cost_total < Decimal("0.00"):
        remaining_cost_total = Decimal("0.00")
    if device.quantity > 0:
        device.costo_unitario = (
            remaining_cost_total / _to_decimal(device.quantity)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        device.costo_unitario = Decimal("0.00")

    _recalculate_sale_price(device)

    db.add(
        models.InventoryMovement(
            store_id=order.store_id,
            source_store_id=order.store_id,
            device_id=device.id,
            movement_type=models.MovementType.OUT,
            quantity=payload.quantity,
            comment=_build_purchase_movement_comment(
                "Devolución proveedor",
                order,
                device,
                payload.reason or reason,
            ),
            unit_cost=order_item.unit_cost,
            performed_by_id=processed_by_id,
        )
    )

    _recalculate_store_inventory_value(db, order.store_id)

    purchase_return = models.PurchaseReturn(
        purchase_order_id=order.id,
        device_id=device.id,
        quantity=payload.quantity,
        reason=payload.reason,
        processed_by_id=processed_by_id,
    )
    db.add(purchase_return)
    db.commit()
    db.refresh(purchase_return)

    _log_action(
        db,
        action="purchase_return_registered",
        entity_type="purchase_order",
        entity_id=str(order.id),
        performed_by_id=processed_by_id,
        details=json.dumps({"device_id": payload.device_id, "quantity": payload.quantity}),
    )
    db.commit()
    db.refresh(order)
    enqueue_sync_outbox(
        db,
        entity_type="purchase_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_purchase_order_payload(order),
    )
    return purchase_return


def import_purchase_orders_from_csv(
    db: Session,
    csv_content: str,
    *,
    created_by_id: int | None = None,
    reason: str | None = None,
) -> tuple[list[models.PurchaseOrder], list[str]]:
    reader = csv.DictReader(StringIO(csv_content))
    fieldnames = [
        (header or "").strip().lower() for header in (reader.fieldnames or []) if header
    ]
    required_headers = {"store_id", "supplier", "device_id", "quantity", "unit_cost"}
    if not fieldnames or required_headers.difference(fieldnames):
        raise ValueError("purchase_import_invalid_headers")

    groups: dict[
        tuple[int, str, str],
        dict[str, object],
    ] = {}
    errors: list[str] = []

    for row in reader:
        line_number = reader.line_num
        normalized = {
            (key or "").strip().lower(): (value or "").strip()
            for key, value in row.items()
        }

        try:
            store_id = int(normalized.get("store_id", ""))
        except ValueError:
            errors.append(f"Fila {line_number}: store_id inválido")
            continue

        supplier = normalized.get("supplier", "").strip()
        if not supplier:
            errors.append(f"Fila {line_number}: proveedor requerido")
            continue

        try:
            device_id = int(normalized.get("device_id", ""))
        except ValueError:
            errors.append(f"Fila {line_number}: device_id inválido")
            continue

        try:
            quantity = int(normalized.get("quantity", ""))
        except ValueError:
            errors.append(f"Fila {line_number}: cantidad inválida")
            continue

        if quantity <= 0:
            errors.append(f"Fila {line_number}: la cantidad debe ser mayor a cero")
            continue

        try:
            unit_cost_value = _to_decimal(normalized.get("unit_cost"))
        except Exception:  # pragma: no cover - validaciones de Decimal
            errors.append(f"Fila {line_number}: costo unitario inválido")
            continue

        if unit_cost_value < Decimal("0"):
            errors.append(f"Fila {line_number}: el costo unitario no puede ser negativo")
            continue

        reference = normalized.get("reference") or f"{store_id}-{supplier}"
        notes = normalized.get("notes") or None

        group = groups.setdefault(
            (store_id, supplier, reference),
            {
                "items": defaultdict(lambda: {"quantity": 0, "unit_cost": Decimal("0.00")}),
                "notes": None,
            },
        )

        items_map: defaultdict[int, dict[str, Decimal | int]] = group["items"]  # type: ignore[assignment]
        bucket = items_map[device_id]
        bucket["quantity"] += quantity
        bucket["unit_cost"] = unit_cost_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if notes and not group["notes"]:
            group["notes"] = notes

    orders: list[models.PurchaseOrder] = []

    for (store_id, supplier, reference), data in groups.items():
        items_map = data["items"]  # type: ignore[index]
        items_payload = [
            schemas.PurchaseOrderItemCreate(
                device_id=device_id,
                quantity_ordered=int(values["quantity"]),
                unit_cost=Decimal(values["unit_cost"]),
            )
            for device_id, values in items_map.items()
        ]
        notes = data.get("notes")  # type: ignore[assignment]
        normalized_notes = notes if isinstance(notes, str) else None
        if reason:
            reason_note = f"Importación CSV: {reason}"
            normalized_notes = (
                f"{normalized_notes} | {reason_note}"
                if normalized_notes
                else reason_note
            )

        try:
            order_payload = schemas.PurchaseOrderCreate(
                store_id=store_id,
                supplier=supplier,
                notes=normalized_notes,
                items=items_payload,
            )
            order = create_purchase_order(
                db,
                order_payload,
                created_by_id=created_by_id,
            )
        except (LookupError, ValueError) as exc:
            db.rollback()
            errors.append(f"Orden {reference}: {exc}")
            continue
        orders.append(order)

    if orders:
        _log_action(
            db,
            action="purchase_orders_imported",
            entity_type="purchase_order",
            entity_id="bulk",
            performed_by_id=created_by_id,
            details=json.dumps({"imported": len(orders), "errors": len(errors)}),
        )
        db.commit()

    return orders, errors


def list_recurring_orders(
    db: Session,
    *,
    order_type: models.RecurringOrderType | None = None,
) -> list[models.RecurringOrder]:
    statement = (
        select(models.RecurringOrder)
        .options(
            joinedload(models.RecurringOrder.store),
            joinedload(models.RecurringOrder.created_by),
            joinedload(models.RecurringOrder.last_used_by),
        )
        .order_by(models.RecurringOrder.updated_at.desc())
    )
    if order_type is not None:
        statement = statement.where(models.RecurringOrder.order_type == order_type)
    return list(db.scalars(statement).unique())


def get_recurring_order(db: Session, template_id: int) -> models.RecurringOrder:
    statement = (
        select(models.RecurringOrder)
        .options(
            joinedload(models.RecurringOrder.store),
            joinedload(models.RecurringOrder.created_by),
            joinedload(models.RecurringOrder.last_used_by),
        )
        .where(models.RecurringOrder.id == template_id)
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("recurring_order_not_found") from exc


def create_recurring_order(
    db: Session,
    payload: schemas.RecurringOrderCreate,
    *,
    created_by_id: int | None = None,
    reason: str | None = None,
) -> models.RecurringOrder:
    payload_data = payload.payload
    store_scope: int | None = None

    if payload.order_type is models.RecurringOrderType.PURCHASE:
        store_scope = int(payload_data.get("store_id")) if payload_data.get("store_id") is not None else None
        if store_scope is not None:
            get_store(db, store_scope)
    elif payload.order_type is models.RecurringOrderType.TRANSFER:
        origin_store_id = int(payload_data["origin_store_id"])
        destination_store_id = int(payload_data["destination_store_id"])
        get_store(db, origin_store_id)
        get_store(db, destination_store_id)
        store_scope = origin_store_id

    template = models.RecurringOrder(
        name=payload.name,
        description=payload.description,
        order_type=payload.order_type,
        store_id=store_scope,
        payload=payload_data,
        created_by_id=created_by_id,
    )
    db.add(template)
    db.flush()
    _log_action(
        db,
        action="recurring_order_created",
        entity_type="recurring_order",
        entity_id=str(template.id),
        performed_by_id=created_by_id,
        details=json.dumps(
            {
                "name": payload.name,
                "order_type": payload.order_type.value,
                "reason": reason,
            }
        ),
    )
    db.commit()
    db.refresh(template)
    return template


def execute_recurring_order(
    db: Session,
    template_id: int,
    *,
    performed_by_id: int,
    reason: str | None = None,
) -> schemas.RecurringOrderExecutionResult:
    template = get_recurring_order(db, template_id)
    now = datetime.utcnow()

    if template.order_type is models.RecurringOrderType.PURCHASE:
        purchase_payload = schemas.PurchaseOrderCreate.model_validate(template.payload)
        notes = purchase_payload.notes or None
        if reason:
            reason_note = f"Plantilla #{template.id}: {reason}"
            notes = f"{notes} | {reason_note}" if notes else reason_note
        purchase_payload.notes = notes
        order = create_purchase_order(
            db,
            purchase_payload,
            created_by_id=performed_by_id,
        )
        summary = f"Orden de compra #{order.id} para {order.supplier}"
        reference_id = order.id
        store_scope = order.store_id
    elif template.order_type is models.RecurringOrderType.TRANSFER:
        transfer_payload = schemas.TransferOrderCreate.model_validate(template.payload)
        transfer_payload.reason = reason or transfer_payload.reason
        order = create_transfer_order(
            db,
            transfer_payload,
            requested_by_id=performed_by_id,
        )
        summary = (
            f"Transferencia #{order.id} de {order.origin_store_id} a {order.destination_store_id}"
        )
        reference_id = order.id
        store_scope = order.origin_store_id
    else:  # pragma: no cover - enum exhaustivo
        raise ValueError("Tipo de orden recurrente no soportado")

    template.last_used_at = now
    template.last_used_by_id = performed_by_id

    _log_action(
        db,
        action="recurring_order_executed",
        entity_type="recurring_order",
        entity_id=str(template.id),
        performed_by_id=performed_by_id,
        details=json.dumps(
            {
                "order_type": template.order_type.value,
                "reference_id": reference_id,
            }
        ),
    )
    db.commit()
    db.refresh(template)

    return schemas.RecurringOrderExecutionResult(
        template_id=template.id,
        order_type=template.order_type,
        reference_id=reference_id,
        store_id=store_scope,
        created_at=now,
        summary=summary,
    )


def list_repair_orders(
    db: Session,
    *,
    store_id: int | None = None,
    status: models.RepairStatus | None = None,
    query: str | None = None,
    limit: int = 100,
) -> list[models.RepairOrder]:
    statement = (
        select(models.RepairOrder)
        .options(joinedload(models.RepairOrder.parts))
        .order_by(models.RepairOrder.opened_at.desc())
        .limit(limit)
    )
    if store_id is not None:
        statement = statement.where(models.RepairOrder.store_id == store_id)
    if status is not None:
        statement = statement.where(models.RepairOrder.status == status)
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.RepairOrder.customer_name).like(normalized),
                func.lower(models.RepairOrder.technician_name).like(normalized),
                func.lower(models.RepairOrder.damage_type).like(normalized),
            )
        )
    return list(db.scalars(statement).unique())


def get_repair_order(db: Session, order_id: int) -> models.RepairOrder:
    statement = (
        select(models.RepairOrder)
        .where(models.RepairOrder.id == order_id)
        .options(
            joinedload(models.RepairOrder.parts),
            joinedload(models.RepairOrder.customer),
        )
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("repair_order_not_found") from exc


def _apply_repair_parts(
    db: Session,
    order: models.RepairOrder,
    parts_payload: list[schemas.RepairOrderPartPayload],
    *,
    performed_by_id: int | None,
    reason: str | None,
) -> Decimal:
    existing_parts = {part.device_id: part for part in order.parts}
    processed_devices: set[int] = set()
    total_cost = Decimal("0")
    snapshot: list[dict[str, object]] = []
    for payload in parts_payload:
        if payload.quantity <= 0:
            raise ValueError("repair_invalid_quantity")
        device = get_device(db, order.store_id, payload.device_id)
        unit_cost = _resolve_part_unit_cost(device, getattr(payload, "unit_cost", None))
        previous_part = existing_parts.get(device.id)
        previous_quantity = previous_part.quantity if previous_part else 0
        delta = payload.quantity - previous_quantity
        if delta > 0:
            if device.quantity < delta:
                raise ValueError("repair_insufficient_stock")
            device.quantity -= delta
            db.add(
                models.InventoryMovement(
                    store_id=order.store_id,
                    source_store_id=order.store_id,
                    device_id=device.id,
                    movement_type=models.MovementType.OUT,
                    quantity=delta,
                    comment=reason or f"Reparación #{order.id}",
                    performed_by_id=performed_by_id,
                )
            )
        elif delta < 0:
            device.quantity += abs(delta)
            db.add(
                models.InventoryMovement(
                    store_id=order.store_id,
                    source_store_id=None,
                    device_id=device.id,
                    movement_type=models.MovementType.IN,
                    quantity=abs(delta),
                    comment=reason or f"Ajuste reparación #{order.id}",
                    performed_by_id=performed_by_id,
                )
            )

        if previous_part is None:
            part = models.RepairOrderPart(
                repair_order_id=order.id,
                device_id=device.id,
                quantity=payload.quantity,
                unit_cost=unit_cost,
            )
            db.add(part)
            order.parts.append(part)
        else:
            previous_part.quantity = payload.quantity
            previous_part.unit_cost = unit_cost
        processed_devices.add(device.id)

        line_total = (unit_cost * Decimal(payload.quantity)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_cost += line_total
        snapshot.append(
            {
                "device_id": device.id,
                "quantity": payload.quantity,
                "unit_cost": float(unit_cost),
            }
        )

    for part in list(order.parts):
        if part.device_id not in processed_devices:
            device = get_device(db, order.store_id, part.device_id)
            device.quantity += part.quantity
            db.add(
                models.InventoryMovement(
                    store_id=order.store_id,
                    source_store_id=None,
                    device_id=device.id,
                    movement_type=models.MovementType.IN,
                    quantity=part.quantity,
                    comment=reason or f"Reverso reparación #{order.id}",
                    performed_by_id=performed_by_id,
                )
            )
            db.delete(part)

    order.parts_cost = total_cost
    order.parts_snapshot = snapshot
    order.inventory_adjusted = bool(processed_devices)
    _recalculate_store_inventory_value(db, order.store_id)
    return total_cost


def create_repair_order(
    db: Session,
    payload: schemas.RepairOrderCreate,
    *,
    performed_by_id: int | None,
    reason: str | None = None,
) -> models.RepairOrder:
    get_store(db, payload.store_id)
    customer = None
    if payload.customer_id:
        customer = get_customer(db, payload.customer_id)
    labor_cost = _to_decimal(payload.labor_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    customer_name = payload.customer_name or (customer.name if customer else None)
    order = models.RepairOrder(
        store_id=payload.store_id,
        customer_id=payload.customer_id,
        customer_name=customer_name,
        technician_name=payload.technician_name,
        damage_type=payload.damage_type,
        device_description=payload.device_description,
        notes=payload.notes,
        labor_cost=labor_cost,
    )
    db.add(order)
    db.flush()

    parts_cost = Decimal("0")
    if payload.parts:
        parts_cost = _apply_repair_parts(
            db,
            order,
            payload.parts,
            performed_by_id=performed_by_id,
            reason=reason,
        )
    order.total_cost = (labor_cost + parts_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    db.add(order)
    db.commit()
    db.refresh(order)

    if customer:
        _append_customer_history(customer, f"Orden de reparación #{order.id} creada")
        db.add(customer)
        db.commit()
        db.refresh(customer)

    _log_action(
        db,
        action="repair_order_created",
        entity_type="repair_order",
        entity_id=str(order.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"store_id": order.store_id, "status": order.status.value}),
    )
    db.commit()
    db.refresh(order)
    enqueue_sync_outbox(
        db,
        entity_type="repair_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_repair_payload(order),
    )
    return order


def update_repair_order(
    db: Session,
    order_id: int,
    payload: schemas.RepairOrderUpdate,
    *,
    performed_by_id: int | None,
    reason: str | None = None,
) -> models.RepairOrder:
    order = get_repair_order(db, order_id)
    updated_fields: dict[str, object] = {}
    if payload.customer_id is not None:
        if payload.customer_id:
            customer = get_customer(db, payload.customer_id)
            order.customer_id = customer.id
            order.customer_name = customer.name
            _append_customer_history(customer, f"Orden de reparación #{order.id} actualizada")
            db.add(customer)
            updated_fields["customer_id"] = customer.id
        else:
            order.customer_id = None
            updated_fields["customer_id"] = None
    if payload.customer_name is not None:
        order.customer_name = payload.customer_name
        updated_fields["customer_name"] = payload.customer_name
    if payload.technician_name is not None:
        order.technician_name = payload.technician_name
        updated_fields["technician_name"] = payload.technician_name
    if payload.damage_type is not None:
        order.damage_type = payload.damage_type
        updated_fields["damage_type"] = payload.damage_type
    if payload.device_description is not None:
        order.device_description = payload.device_description
        updated_fields["device_description"] = payload.device_description
    if payload.notes is not None:
        order.notes = payload.notes
        updated_fields["notes"] = payload.notes
    if payload.status is not None and payload.status != order.status:
        order.status = payload.status
        updated_fields["status"] = payload.status.value
        if payload.status == models.RepairStatus.ENTREGADO:
            order.delivered_at = datetime.utcnow()
        elif payload.status in {models.RepairStatus.PENDIENTE, models.RepairStatus.EN_PROCESO}:
            order.delivered_at = None
    if payload.labor_cost is not None:
        order.labor_cost = _to_decimal(payload.labor_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        updated_fields["labor_cost"] = float(order.labor_cost)
    if payload.parts is not None:
        parts_cost = _apply_repair_parts(
            db,
            order,
            payload.parts,
            performed_by_id=performed_by_id,
            reason=reason,
        )
        updated_fields["parts_cost"] = float(parts_cost)
    order.total_cost = (order.labor_cost + order.parts_cost).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    if updated_fields:
        _log_action(
            db,
            action="repair_order_updated",
            entity_type="repair_order",
            entity_id=str(order.id),
            performed_by_id=performed_by_id,
            details=json.dumps(updated_fields),
        )
        db.commit()
        db.refresh(order)
    enqueue_sync_outbox(
        db,
        entity_type="repair_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_repair_payload(order),
    )
    return order


def delete_repair_order(
    db: Session,
    order_id: int,
    *,
    performed_by_id: int | None,
    reason: str | None = None,
) -> None:
    order = get_repair_order(db, order_id)
    for part in list(order.parts):
        device = get_device(db, order.store_id, part.device_id)
        device.quantity += part.quantity
        db.add(
            models.InventoryMovement(
                store_id=order.store_id,
                source_store_id=None,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=part.quantity,
                comment=reason or f"Cancelación reparación #{order.id}",
                performed_by_id=performed_by_id,
            )
        )
    _recalculate_store_inventory_value(db, order.store_id)
    db.delete(order)
    db.commit()
    _log_action(
        db,
        action="repair_order_deleted",
        entity_type="repair_order",
        entity_id=str(order_id),
        performed_by_id=performed_by_id,
    )
    db.commit()
    enqueue_sync_outbox(
        db,
        entity_type="repair_order",
        entity_id=str(order_id),
        operation="DELETE",
        payload={"id": order_id},
    )


def list_sales(
    db: Session,
    *,
    store_id: int | None = None,
    limit: int | None = 50,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    customer_id: int | None = None,
    performed_by_id: int | None = None,
    query: str | None = None,
) -> list[models.Sale]:
    statement = (
        select(models.Sale)
        .options(
            joinedload(models.Sale.store),
            joinedload(models.Sale.items).joinedload(models.SaleItem.device),
            joinedload(models.Sale.returns),
            joinedload(models.Sale.customer),
            joinedload(models.Sale.cash_session),
            joinedload(models.Sale.performed_by),
        )
        .order_by(models.Sale.created_at.desc())
    )
    if store_id is not None:
        statement = statement.where(models.Sale.store_id == store_id)
    if customer_id is not None:
        statement = statement.where(models.Sale.customer_id == customer_id)
    if performed_by_id is not None:
        statement = statement.where(models.Sale.performed_by_id == performed_by_id)
    if date_from is not None or date_to is not None:
        start, end = _normalize_date_range(date_from, date_to)
        statement = statement.where(
            models.Sale.created_at >= start, models.Sale.created_at <= end
        )
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.join(models.Sale.items).join(models.SaleItem.device)
        statement = statement.where(
            or_(
                func.lower(models.Device.sku).like(normalized),
                func.lower(models.Device.name).like(normalized),
                func.lower(models.Device.modelo).like(normalized),
                func.lower(models.Device.imei).like(normalized),
                func.lower(models.Device.serial).like(normalized),
            )
        )
    results = list(db.scalars(statement).unique())
    if limit is not None:
        return results[:limit]
    return results


def get_sale(db: Session, sale_id: int) -> models.Sale:
    statement = (
        select(models.Sale)
        .where(models.Sale.id == sale_id)
        .options(
            joinedload(models.Sale.store),
            joinedload(models.Sale.items).joinedload(models.SaleItem.device),
            joinedload(models.Sale.returns),
            joinedload(models.Sale.customer),
            joinedload(models.Sale.cash_session),
            joinedload(models.Sale.performed_by),
        )
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("sale_not_found") from exc


def _ensure_device_available_for_sale(
    device: models.Device, quantity: int
) -> None:
    if quantity <= 0:
        raise ValueError("sale_invalid_quantity")
    if device.quantity < quantity:
        raise ValueError("sale_insufficient_stock")
    if device.imei or device.serial:
        if device.estado and device.estado.lower() == "vendido":
            raise ValueError("sale_device_already_sold")
        if quantity > 1:
            raise ValueError("sale_requires_single_unit")


def _mark_device_sold(device: models.Device) -> None:
    if device.imei or device.serial:
        device.estado = "vendido"


def _restore_device_availability(device: models.Device) -> None:
    if device.imei or device.serial:
        device.estado = "disponible"


def _ensure_device_available_for_preview(
    device: models.Device, quantity: int, *, reserved_quantity: int = 0
) -> None:
    if quantity <= 0:
        raise ValueError("sale_invalid_quantity")
    available_quantity = device.quantity + reserved_quantity
    if available_quantity < quantity:
        raise ValueError("sale_insufficient_stock")
    if device.imei or device.serial:
        if (
            device.estado
            and device.estado.lower() == "vendido"
            and reserved_quantity <= 0
        ):
            raise ValueError("sale_device_already_sold")
        if quantity > 1:
            raise ValueError("sale_requires_single_unit")


def _preview_sale_totals(
    db: Session,
    store_id: int,
    items: list[schemas.SaleItemCreate],
    *,
    sale_discount_percent: Decimal,
    reserved_quantities: dict[int, int] | None = None,
) -> tuple[Decimal, Decimal]:
    gross_total = Decimal("0")
    total_discount = Decimal("0")
    reserved = reserved_quantities or {}

    for item in items:
        device = get_device(db, store_id, item.device_id)
        reserved_quantity = reserved.get(device.id, 0)
        _ensure_device_available_for_preview(
            device, item.quantity, reserved_quantity=reserved_quantity
        )

        line_unit_price = _to_decimal(device.unit_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        quantity_decimal = _to_decimal(item.quantity)
        line_total = (line_unit_price * quantity_decimal).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        gross_total += line_total

        line_discount_percent = _to_decimal(getattr(item, "discount_percent", None))
        if line_discount_percent == Decimal("0"):
            line_discount_percent = sale_discount_percent
        discount_fraction = line_discount_percent / Decimal("100")
        line_discount_amount = (line_total * discount_fraction).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_discount += line_discount_amount

    return gross_total, total_discount


def _apply_sale_items(
    db: Session,
    sale: models.Sale,
    items: list[schemas.SaleItemCreate],
    *,
    sale_discount_percent: Decimal,
    performed_by_id: int,
    reason: str | None,
) -> tuple[Decimal, Decimal]:
    gross_total = Decimal("0")
    total_discount = Decimal("0")
    for item in items:
        device = get_device(db, sale.store_id, item.device_id)
        _ensure_device_available_for_sale(device, item.quantity)

        line_unit_price = _to_decimal(device.unit_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        quantity_decimal = _to_decimal(item.quantity)
        line_total = (line_unit_price * quantity_decimal).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        gross_total += line_total

        line_discount_percent = _to_decimal(getattr(item, "discount_percent", None))
        if line_discount_percent == Decimal("0"):
            line_discount_percent = sale_discount_percent
        discount_fraction = line_discount_percent / Decimal("100")
        line_discount_amount = (line_total * discount_fraction).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_discount += line_discount_amount
        net_line_total = (line_total - line_discount_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        device.quantity -= item.quantity
        if device.quantity <= 0:
            _mark_device_sold(device)

        sale_item = models.SaleItem(
            sale_id=sale.id,
            device_id=device.id,
            quantity=item.quantity,
            unit_price=line_unit_price,
            discount_amount=line_discount_amount,
            total_line=net_line_total,
        )
        sale.items.append(sale_item)

        db.add(
            models.InventoryMovement(
                store_id=sale.store_id,
                source_store_id=sale.store_id,
                device_id=device.id,
                movement_type=models.MovementType.OUT,
                quantity=item.quantity,
                comment=reason,
                performed_by_id=performed_by_id,
            )
        )
    return gross_total, total_discount


def create_sale(
    db: Session,
    payload: schemas.SaleCreate,
    *,
    performed_by_id: int,
    tax_rate: Decimal | float | int | None = None,
    reason: str | None = None,
) -> models.Sale:
    if not payload.items:
        raise ValueError("sale_items_required")

    get_store(db, payload.store_id)

    customer = None
    customer_name = payload.customer_name
    if payload.customer_id:
        customer = get_customer(db, payload.customer_id)
        customer_name = customer_name or customer.name

    sale_discount_percent = _to_decimal(payload.discount_percent or 0)
    sale_status = (payload.status or "COMPLETADA").strip() or "COMPLETADA"
    normalized_status = sale_status.upper()
    sale = models.Sale(
        store_id=payload.store_id,
        customer_id=customer.id if customer else None,
        customer_name=customer_name,
        payment_method=models.PaymentMethod(payload.payment_method),
        discount_percent=sale_discount_percent.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        status=normalized_status,
        notes=payload.notes,
        performed_by_id=performed_by_id,
    )
    db.add(sale)

    tax_value = _to_decimal(tax_rate)
    if tax_value < Decimal("0"):
        tax_value = Decimal("0")
    tax_fraction = tax_value / Decimal("100") if tax_value else Decimal("0")

    try:
        preview_gross_total, preview_discount = _preview_sale_totals(
            db,
            sale.store_id,
            payload.items,
            sale_discount_percent=sale_discount_percent,
        )
        preview_subtotal = (preview_gross_total - preview_discount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        preview_tax_amount = (preview_subtotal * tax_fraction).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        preview_total = (preview_subtotal + preview_tax_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if customer and sale.payment_method == models.PaymentMethod.CREDITO:
            _validate_customer_credit(customer, preview_total)
    except ValueError:
        db.expunge(sale)
        raise

    db.flush()

    ledger_entry: models.CustomerLedgerEntry | None = None
    customer_to_sync: models.Customer | None = None

    gross_total, total_discount = _apply_sale_items(
        db,
        sale,
        payload.items,
        sale_discount_percent=sale_discount_percent,
        performed_by_id=performed_by_id,
        reason=reason,
    )

    subtotal = (gross_total - total_discount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    sale.subtotal_amount = subtotal
    tax_amount = (subtotal * tax_fraction).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sale.tax_amount = tax_amount
    sale.total_amount = (subtotal + tax_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    _recalculate_store_inventory_value(db, sale.store_id)

    if customer:
        if sale.payment_method == models.PaymentMethod.CREDITO:
            customer.outstanding_debt = (
                _to_decimal(customer.outstanding_debt) + sale.total_amount
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ledger_entry = _create_customer_ledger_entry(
                db,
                customer=customer,
                entry_type=models.CustomerLedgerEntryType.SALE,
                amount=sale.total_amount,
                note=f"Venta #{sale.id} registrada ({sale.payment_method.value})",
                reference_type="sale",
                reference_id=str(sale.id),
                details={
                    "store_id": sale.store_id,
                    "payment_method": sale.payment_method.value,
                    "status": sale.status,
                },
                created_by_id=performed_by_id,
            )
        _append_customer_history(
            customer,
            f"Venta #{sale.id} registrada ({sale.payment_method.value})",
        )
        db.add(customer)

    db.commit()
    db.refresh(sale)

    if customer and sale.payment_method == models.PaymentMethod.CREDITO:
        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer.id),
            operation="UPSERT",
            payload=_customer_payload(customer),
        )
    if ledger_entry:
        _sync_customer_ledger_entry(db, ledger_entry)

    _log_action(
        db,
        action="sale_registered",
        entity_type="sale",
        entity_id=str(sale.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"store_id": sale.store_id, "total_amount": float(sale.total_amount)}),
    )
    db.commit()
    db.refresh(sale)
    sale_payload = {
        "sale_id": sale.id,
        "store_id": sale.store_id,
        "customer_id": sale.customer_id,
        "customer_name": sale.customer_name,
        "payment_method": sale.payment_method.value,
        "discount_percent": float(sale.discount_percent),
        "subtotal_amount": float(sale.subtotal_amount),
        "tax_amount": float(sale.tax_amount),
        "total_amount": float(sale.total_amount),
        "created_at": sale.created_at.isoformat(),
        "items": [
            {
                "device_id": item.device_id,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "discount_amount": float(item.discount_amount),
                "total_line": float(item.total_line),
            }
            for item in sale.items
        ],
    }
    enqueue_sync_outbox(
        db,
        entity_type="sale",
        entity_id=str(sale.id),
        operation="UPSERT",
        payload=sale_payload,
    )
    return sale


def update_sale(
    db: Session,
    sale_id: int,
    payload: schemas.SaleUpdate,
    *,
    performed_by_id: int,
    reason: str | None = None,
) -> models.Sale:
    sale = get_sale(db, sale_id)
    if sale.status and sale.status.upper() == "CANCELADA":
        raise ValueError("sale_already_cancelled")
    if not payload.items:
        raise ValueError("sale_items_required")
    if sale.returns:
        raise ValueError("sale_has_returns")

    previous_customer = sale.customer
    previous_payment_method = sale.payment_method
    previous_total_amount = _to_decimal(sale.total_amount)
    reserved_quantities: dict[int, int] = {}
    for existing_item in sale.items:
        reserved_quantities[existing_item.device_id] = (
            reserved_quantities.get(existing_item.device_id, 0) + existing_item.quantity
        )
    ledger_reversal: models.CustomerLedgerEntry | None = None
    ledger_new: models.CustomerLedgerEntry | None = None
    customers_to_sync: dict[int, models.Customer] = {}

    sale_discount_percent = _to_decimal(payload.discount_percent or 0)
    new_payment_method = models.PaymentMethod(payload.payment_method)
    sale_status = (payload.status or sale.status or "COMPLETADA").strip() or "COMPLETADA"
    normalized_status = sale_status.upper()

    customer = None
    customer_name = payload.customer_name
    if payload.customer_id:
        customer = get_customer(db, payload.customer_id)
        customer_name = customer_name or customer.name

    preview_gross_total, preview_discount = _preview_sale_totals(
        db,
        sale.store_id,
        payload.items,
        sale_discount_percent=sale_discount_percent,
        reserved_quantities=reserved_quantities,
    )
    preview_subtotal = (preview_gross_total - preview_discount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    tax_value = _to_decimal(None)
    tax_fraction = tax_value / Decimal("100") if tax_value else Decimal("0")
    preview_tax_amount = (preview_subtotal * tax_fraction).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    preview_total = (preview_subtotal + preview_tax_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    validation_customer = customer or previous_customer
    if new_payment_method == models.PaymentMethod.CREDITO and validation_customer:
        _validate_customer_credit(validation_customer, preview_total)

    sale.discount_percent = sale_discount_percent.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    sale.status = normalized_status
    sale.notes = payload.notes
    sale.customer_id = customer.id if customer else None
    sale.customer_name = customer_name

    reversal_comment = reason or f"Edición venta #{sale.id}"
    for existing_item in list(sale.items):
        device = get_device(db, sale.store_id, existing_item.device_id)
        device.quantity += existing_item.quantity
        _restore_device_availability(device)
        db.add(
            models.InventoryMovement(
                store_id=sale.store_id,
                source_store_id=None,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=existing_item.quantity,
                comment=reversal_comment,
                performed_by_id=performed_by_id,
            )
        )
    sale.items.clear()
    db.flush()

    if (
        previous_customer
        and previous_payment_method == models.PaymentMethod.CREDITO
        and previous_total_amount > Decimal("0")
    ):
        updated_debt = (
            _to_decimal(previous_customer.outstanding_debt) - previous_total_amount
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if updated_debt < Decimal("0"):
            updated_debt = Decimal("0")
        previous_customer.outstanding_debt = updated_debt
        db.add(previous_customer)
        customers_to_sync[previous_customer.id] = previous_customer
        ledger_reversal = _create_customer_ledger_entry(
            db,
            customer=previous_customer,
            entry_type=models.CustomerLedgerEntryType.ADJUSTMENT,
            amount=-previous_total_amount,
            note=f"Ajuste por edición de venta #{sale.id}",
            reference_type="sale",
            reference_id=str(sale.id),
            details={
                "event": "sale_edit_reversal",
                "previous_amount": float(previous_total_amount),
            },
            created_by_id=performed_by_id,
        )

    gross_total, total_discount = _apply_sale_items(
        db,
        sale,
        payload.items,
        sale_discount_percent=sale_discount_percent,
        performed_by_id=performed_by_id,
        reason=reason,
    )

    subtotal = (gross_total - total_discount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    sale.subtotal_amount = subtotal
    sale.tax_amount = (subtotal * tax_fraction).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    sale.payment_method = new_payment_method
    sale.total_amount = (subtotal + sale.tax_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    target_customer = customer or (
        previous_customer if previous_customer and previous_customer.id == sale.customer_id else None
    )
    if target_customer:
        if sale.payment_method == models.PaymentMethod.CREDITO:
            target_customer.outstanding_debt = (
                _to_decimal(target_customer.outstanding_debt) + sale.total_amount
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            customers_to_sync[target_customer.id] = target_customer
            ledger_new = _create_customer_ledger_entry(
                db,
                customer=target_customer,
                entry_type=models.CustomerLedgerEntryType.SALE,
                amount=sale.total_amount,
                note=f"Venta #{sale.id} actualizada ({sale.payment_method.value})",
                reference_type="sale",
                reference_id=str(sale.id),
                details={
                    "event": "sale_updated",
                    "payment_method": sale.payment_method.value,
                    "status": sale.status,
                },
                created_by_id=performed_by_id,
            )
        _append_customer_history(
            target_customer,
            f"Venta #{sale.id} actualizada ({sale.payment_method.value})",
        )
        db.add(target_customer)

    _recalculate_store_inventory_value(db, sale.store_id)

    db.commit()
    db.refresh(sale)

    for customer_to_sync in customers_to_sync.values():
        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer_to_sync.id),
            operation="UPSERT",
            payload=_customer_payload(customer_to_sync),
        )
    if ledger_reversal:
        _sync_customer_ledger_entry(db, ledger_reversal)
    if ledger_new:
        _sync_customer_ledger_entry(db, ledger_new)

    _log_action(
        db,
        action="sale_updated",
        entity_type="sale",
        entity_id=str(sale.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"store_id": sale.store_id, "reason": reason}),
    )
    db.commit()
    db.refresh(sale)

    sale_payload = {
        "sale_id": sale.id,
        "store_id": sale.store_id,
        "customer_id": sale.customer_id,
        "customer_name": sale.customer_name,
        "payment_method": sale.payment_method.value,
        "discount_percent": float(sale.discount_percent),
        "subtotal_amount": float(sale.subtotal_amount),
        "tax_amount": float(sale.tax_amount),
        "total_amount": float(sale.total_amount),
        "created_at": sale.created_at.isoformat(),
        "items": [
            {
                "device_id": item.device_id,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "discount_amount": float(item.discount_amount),
                "total_line": float(item.total_line),
            }
            for item in sale.items
        ],
    }
    enqueue_sync_outbox(
        db,
        entity_type="sale",
        entity_id=str(sale.id),
        operation="UPSERT",
        payload=sale_payload,
    )
    return sale


def cancel_sale(
    db: Session,
    sale_id: int,
    *,
    performed_by_id: int,
    reason: str | None = None,
) -> models.Sale:
    sale = get_sale(db, sale_id)
    if sale.status and sale.status.upper() == "CANCELADA":
        raise ValueError("sale_already_cancelled")

    cancel_reason = reason or f"Anulación venta #{sale.id}"
    ledger_entry: models.CustomerLedgerEntry | None = None
    customer_to_sync: models.Customer | None = None
    for item in sale.items:
        device = get_device(db, sale.store_id, item.device_id)
        device.quantity += item.quantity
        if device.quantity > 0:
            _restore_device_availability(device)
        db.add(
            models.InventoryMovement(
                store_id=sale.store_id,
                source_store_id=None,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=item.quantity,
                comment=cancel_reason,
                performed_by_id=performed_by_id,
            )
        )

    if sale.customer and sale.payment_method == models.PaymentMethod.CREDITO and sale.total_amount > Decimal("0"):
        updated_debt = (
            _to_decimal(sale.customer.outstanding_debt) - _to_decimal(sale.total_amount)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if updated_debt < Decimal("0"):
            updated_debt = Decimal("0")
        sale.customer.outstanding_debt = updated_debt
        _append_customer_history(
            sale.customer,
            f"Venta #{sale.id} anulada",
        )
        db.add(sale.customer)
        customer_to_sync = sale.customer
        ledger_entry = _create_customer_ledger_entry(
            db,
            customer=sale.customer,
            entry_type=models.CustomerLedgerEntryType.ADJUSTMENT,
            amount=-_to_decimal(sale.total_amount),
            note=f"Venta #{sale.id} anulada",
            reference_type="sale",
            reference_id=str(sale.id),
            details={"event": "sale_cancelled", "store_id": sale.store_id},
            created_by_id=performed_by_id,
        )

    sale.status = "CANCELADA"
    _recalculate_store_inventory_value(db, sale.store_id)

    db.commit()
    db.refresh(sale)

    if customer_to_sync:
        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer_to_sync.id),
            operation="UPSERT",
            payload=_customer_payload(customer_to_sync),
        )
    if ledger_entry:
        _sync_customer_ledger_entry(db, ledger_entry)

    _log_action(
        db,
        action="sale_cancelled",
        entity_type="sale",
        entity_id=str(sale.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"reason": cancel_reason}),
    )
    db.commit()
    db.refresh(sale)

    sale_payload = {
        "sale_id": sale.id,
        "store_id": sale.store_id,
        "status": sale.status,
    }
    enqueue_sync_outbox(
        db,
        entity_type="sale",
        entity_id=str(sale.id),
        operation="UPSERT",
        payload=sale_payload,
    )
    return sale


def register_sale_return(
    db: Session,
    payload: schemas.SaleReturnCreate,
    *,
    processed_by_id: int,
    reason: str | None = None,
) -> list[models.SaleReturn]:
    sale = get_sale(db, payload.sale_id)
    if not payload.items:
        raise ValueError("sale_return_items_required")

    returns: list[models.SaleReturn] = []
    refund_total = Decimal("0")
    items_by_device = {item.device_id: item for item in sale.items}
    ledger_entry: models.CustomerLedgerEntry | None = None
    customer_to_sync: models.Customer | None = None

    for item in payload.items:
        sale_item = items_by_device.get(item.device_id)
        if sale_item is None:
            raise LookupError("sale_item_not_found")
        if item.quantity <= 0:
            raise ValueError("sale_return_invalid_quantity")

        returned_total = sum(
            existing.quantity for existing in sale.returns if existing.device_id == item.device_id
        )
        if item.quantity > sale_item.quantity - returned_total:
            raise ValueError("sale_return_invalid_quantity")

        device = get_device(db, sale.store_id, item.device_id)
        device.quantity += item.quantity
        if device.quantity > 0:
            _restore_device_availability(device)

        sale_return = models.SaleReturn(
            sale_id=sale.id,
            device_id=item.device_id,
            quantity=item.quantity,
            reason=item.reason,
            processed_by_id=processed_by_id,
        )
        db.add(sale_return)
        returns.append(sale_return)

        unit_refund = (sale_item.total_line / Decimal(sale_item.quantity)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        refund_total += (unit_refund * Decimal(item.quantity)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        db.add(
            models.InventoryMovement(
                store_id=sale.store_id,
                source_store_id=None,
                device_id=item.device_id,
                movement_type=models.MovementType.IN,
                quantity=item.quantity,
                comment=item.reason or reason,
                performed_by_id=processed_by_id,
            )
        )

    _recalculate_store_inventory_value(db, sale.store_id)

    db.commit()
    for sale_return in returns:
        db.refresh(sale_return)

    _log_action(
        db,
        action="sale_return_registered",
        entity_type="sale",
        entity_id=str(sale.id),
        performed_by_id=processed_by_id,
        details=json.dumps({"items": [item.model_dump() for item in payload.items]}),
    )
    db.commit()

    if sale.customer and sale.payment_method == models.PaymentMethod.CREDITO and refund_total > 0:
        sale.customer.outstanding_debt = (
            _to_decimal(sale.customer.outstanding_debt) - refund_total
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if sale.customer.outstanding_debt < Decimal("0"):
            sale.customer.outstanding_debt = Decimal("0")
        _append_customer_history(
            sale.customer,
            f"Devolución aplicada a venta #{sale.id} por ${float(refund_total):.2f}",
        )
        db.add(sale.customer)
        db.commit()
        ledger_entry = _create_customer_ledger_entry(
            db,
            customer=sale.customer,
            entry_type=models.CustomerLedgerEntryType.ADJUSTMENT,
            amount=-refund_total,
            note=f"Devolución venta #{sale.id}",
            reference_type="sale",
            reference_id=str(sale.id),
            details={"event": "sale_return", "store_id": sale.store_id},
            created_by_id=processed_by_id,
        )
        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(sale.customer.id),
            operation="UPSERT",
            payload=_customer_payload(sale.customer),
        )
        if ledger_entry:
            _sync_customer_ledger_entry(db, ledger_entry)
    return returns


def list_operations_history(
    db: Session,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    store_id: int | None = None,
    technician_id: int | None = None,
) -> schemas.OperationsHistoryResponse:
    start_dt = start or (datetime.utcnow() - timedelta(days=30))
    end_dt = end or datetime.utcnow()
    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    records: list[schemas.OperationHistoryEntry] = []
    technicians: dict[int, str] = {}

    def register_technician(user: models.User | None) -> None:
        if user is None or user.id is None:
            return
        name = _user_display_name(user) or f"Usuario {user.id}"
        technicians.setdefault(user.id, name)

    purchase_stmt = (
        select(models.PurchaseOrder)
        .options(
            joinedload(models.PurchaseOrder.store),
            joinedload(models.PurchaseOrder.created_by),
            joinedload(models.PurchaseOrder.items),
        )
        .where(
            models.PurchaseOrder.created_at >= start_dt,
            models.PurchaseOrder.created_at <= end_dt,
        )
    )
    if store_id is not None:
        purchase_stmt = purchase_stmt.where(models.PurchaseOrder.store_id == store_id)
    for order in db.scalars(purchase_stmt).unique():
        if technician_id is not None and order.created_by_id != technician_id:
            continue
        register_technician(order.created_by)
        total_amount = sum(
            _to_decimal(item.unit_cost) * _to_decimal(item.quantity_ordered)
            for item in order.items
        )
        records.append(
            schemas.OperationHistoryEntry(
                id=f"purchase-{order.id}",
                operation_type=schemas.OperationHistoryType.PURCHASE,
                occurred_at=order.created_at,
                store_id=order.store_id,
                store_name=order.store.name if order.store else None,
                technician_id=order.created_by_id,
                technician_name=_user_display_name(order.created_by),
                reference=f"PO-{order.id}",
                description=f"Orden de compra para {order.supplier}",
                amount=total_amount,
            )
        )

    transfer_stmt = (
        select(models.TransferOrder)
        .options(
            joinedload(models.TransferOrder.origin_store),
            joinedload(models.TransferOrder.destination_store),
            joinedload(models.TransferOrder.dispatched_by),
            joinedload(models.TransferOrder.received_by),
            joinedload(models.TransferOrder.items),
        )
        .where(
            or_(
                models.TransferOrder.dispatched_at.between(start_dt, end_dt),
                models.TransferOrder.received_at.between(start_dt, end_dt),
            )
        )
    )

    for transfer in db.scalars(transfer_stmt).unique():
        if (
            transfer.dispatched_at
            and start_dt <= transfer.dispatched_at <= end_dt
            and (store_id is None or transfer.origin_store_id == store_id)
            and (technician_id is None or transfer.dispatched_by_id == technician_id)
        ):
            register_technician(transfer.dispatched_by)
            records.append(
                schemas.OperationHistoryEntry(
                    id=f"transfer-dispatch-{transfer.id}",
                    operation_type=schemas.OperationHistoryType.TRANSFER_DISPATCH,
                    occurred_at=transfer.dispatched_at,
                    store_id=transfer.origin_store_id,
                    store_name=transfer.origin_store.name if transfer.origin_store else None,
                    technician_id=transfer.dispatched_by_id,
                    technician_name=_user_display_name(transfer.dispatched_by),
                    reference=f"TR-{transfer.id}",
                    description=(
                        f"Despacho hacia {transfer.destination_store.name if transfer.destination_store else transfer.destination_store_id}"
                    ),
                )
            )

        if (
            transfer.received_at
            and start_dt <= transfer.received_at <= end_dt
            and (store_id is None or transfer.destination_store_id == store_id)
            and (technician_id is None or transfer.received_by_id == technician_id)
        ):
            register_technician(transfer.received_by)
            records.append(
                schemas.OperationHistoryEntry(
                    id=f"transfer-receive-{transfer.id}",
                    operation_type=schemas.OperationHistoryType.TRANSFER_RECEIVE,
                    occurred_at=transfer.received_at,
                    store_id=transfer.destination_store_id,
                    store_name=transfer.destination_store.name if transfer.destination_store else None,
                    technician_id=transfer.received_by_id,
                    technician_name=_user_display_name(transfer.received_by),
                    reference=f"TR-{transfer.id}",
                    description=(
                        f"Recepción desde {transfer.origin_store.name if transfer.origin_store else transfer.origin_store_id}"
                    ),
                )
            )

    sale_stmt = (
        select(models.Sale)
        .options(
            joinedload(models.Sale.store),
            joinedload(models.Sale.performed_by),
        )
        .where(
            models.Sale.created_at >= start_dt,
            models.Sale.created_at <= end_dt,
        )
    )
    if store_id is not None:
        sale_stmt = sale_stmt.where(models.Sale.store_id == store_id)
    for sale in db.scalars(sale_stmt).unique():
        if technician_id is not None and sale.performed_by_id != technician_id:
            continue
        register_technician(sale.performed_by)
        records.append(
            schemas.OperationHistoryEntry(
                id=f"sale-{sale.id}",
                operation_type=schemas.OperationHistoryType.SALE,
                occurred_at=sale.created_at,
                store_id=sale.store_id,
                store_name=sale.store.name if sale.store else None,
                technician_id=sale.performed_by_id,
                technician_name=_user_display_name(sale.performed_by),
                reference=f"VNT-{sale.id}",
                description="Venta registrada en POS",
                amount=_to_decimal(sale.total_amount),
            )
        )

    records.sort(key=lambda entry: entry.occurred_at, reverse=True)
    technicians_list = [
        schemas.OperationHistoryTechnician(id=tech_id, name=name)
        for tech_id, name in sorted(technicians.items(), key=lambda item: item[1].lower())
    ]

    return schemas.OperationsHistoryResponse(records=records, technicians=technicians_list)


def list_cash_sessions(
    db: Session,
    *,
    store_id: int,
    limit: int = 30,
) -> list[models.CashRegisterSession]:
    statement = (
        select(models.CashRegisterSession)
        .where(models.CashRegisterSession.store_id == store_id)
        .order_by(models.CashRegisterSession.opened_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).unique())


def get_cash_session(db: Session, session_id: int) -> models.CashRegisterSession:
    statement = select(models.CashRegisterSession).where(models.CashRegisterSession.id == session_id)
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("cash_session_not_found") from exc


def open_cash_session(
    db: Session,
    payload: schemas.CashSessionOpenRequest,
    *,
    opened_by_id: int | None,
    reason: str | None = None,
) -> models.CashRegisterSession:
    get_store(db, payload.store_id)
    statement = select(models.CashRegisterSession).where(
        models.CashRegisterSession.store_id == payload.store_id,
        models.CashRegisterSession.status == models.CashSessionStatus.ABIERTO,
    )
    if db.scalars(statement).first() is not None:
        raise ValueError("cash_session_already_open")

    opening_amount = _to_decimal(payload.opening_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    session = models.CashRegisterSession(
        store_id=payload.store_id,
        status=models.CashSessionStatus.ABIERTO,
        opening_amount=opening_amount,
        closing_amount=Decimal("0"),
        expected_amount=opening_amount,
        difference_amount=Decimal("0"),
        payment_breakdown={},
        notes=payload.notes,
        opened_by_id=opened_by_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    _log_action(
        db,
        action="cash_session_opened",
        entity_type="cash_session",
        entity_id=str(session.id),
        performed_by_id=opened_by_id,
        details=json.dumps({"store_id": session.store_id, "reason": reason}),
    )
    db.commit()
    db.refresh(session)
    return session


def close_cash_session(
    db: Session,
    payload: schemas.CashSessionCloseRequest,
    *,
    closed_by_id: int | None,
    reason: str | None = None,
) -> models.CashRegisterSession:
    session = get_cash_session(db, payload.session_id)
    if session.status != models.CashSessionStatus.ABIERTO:
        raise ValueError("cash_session_not_open")

    sales_totals: dict[str, Decimal] = {}
    totals_stmt = (
        select(models.Sale.payment_method, func.sum(models.Sale.total_amount))
        .where(models.Sale.cash_session_id == session.id)
        .group_by(models.Sale.payment_method)
    )
    for method, total in db.execute(totals_stmt):
        totals_value = _to_decimal(total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sales_totals[method.value] = totals_value

    session.closing_amount = _to_decimal(payload.closing_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    session.closed_by_id = closed_by_id
    session.closed_at = datetime.utcnow()
    session.status = models.CashSessionStatus.CERRADO
    session.payment_breakdown = {key: float(value) for key, value in sales_totals.items()}

    for method_key, reported_amount in payload.payment_breakdown.items():
        session.payment_breakdown[f"reportado_{method_key.upper()}"] = float(
            Decimal(str(reported_amount))
        )

    expected_cash = session.opening_amount + sales_totals.get(models.PaymentMethod.EFECTIVO.value, Decimal("0"))
    session.expected_amount = expected_cash.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    session.difference_amount = (
        session.closing_amount - session.expected_amount
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if payload.notes:
        session.notes = (session.notes or "") + f"\n{payload.notes}" if session.notes else payload.notes

    db.add(session)
    db.commit()
    db.refresh(session)

    _log_action(
        db,
        action="cash_session_closed",
        entity_type="cash_session",
        entity_id=str(session.id),
        performed_by_id=closed_by_id,
        details=json.dumps(
            {
                "difference": float(session.difference_amount),
                "reason": reason,
            }
        ),
    )
    db.commit()
    db.refresh(session)
    return session


def get_pos_config(db: Session, store_id: int) -> models.POSConfig:
    store = get_store(db, store_id)
    statement = select(models.POSConfig).where(models.POSConfig.store_id == store_id)
    config = db.scalars(statement).first()
    if config is None:
        prefix = store.name[:3].upper() if store.name else "POS"
        generated_prefix = f"{prefix}-{store_id:03d}"[:12]
        config = models.POSConfig(store_id=store_id, invoice_prefix=generated_prefix)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def update_pos_config(
    db: Session,
    payload: schemas.POSConfigUpdate,
    *,
    updated_by_id: int | None,
    reason: str | None = None,
) -> models.POSConfig:
    config = get_pos_config(db, payload.store_id)
    config.tax_rate = _to_decimal(payload.tax_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    config.invoice_prefix = payload.invoice_prefix.strip().upper()
    config.printer_name = payload.printer_name.strip() if payload.printer_name else None
    config.printer_profile = (
        payload.printer_profile.strip() if payload.printer_profile else None
    )
    config.quick_product_ids = payload.quick_product_ids
    db.add(config)
    db.commit()
    db.refresh(config)

    _log_action(
        db,
        action="pos_config_update",
        entity_type="store",
        entity_id=str(payload.store_id),
        performed_by_id=updated_by_id,
        details=json.dumps(
            {
                "tax_rate": float(config.tax_rate),
                "invoice_prefix": config.invoice_prefix,
                "reason": reason,
            }
        ),
    )
    db.commit()
    db.refresh(config)
    enqueue_sync_outbox(
        db,
        entity_type="pos_config",
        entity_id=str(payload.store_id),
        operation="UPSERT",
        payload=_pos_config_payload(config),
    )
    return config


def save_pos_draft(
    db: Session,
    payload: schemas.POSSaleRequest,
    *,
    saved_by_id: int | None,
    reason: str | None = None,
) -> models.POSDraftSale:
    get_store(db, payload.store_id)
    draft: models.POSDraftSale
    if payload.draft_id:
        statement = select(models.POSDraftSale).where(models.POSDraftSale.id == payload.draft_id)
        draft = db.scalars(statement).first()
        if draft is None:
            raise LookupError("pos_draft_not_found")
        draft.store_id = payload.store_id
    else:
        draft = models.POSDraftSale(store_id=payload.store_id)
        db.add(draft)

    serialized = payload.model_dump(
        mode="json",
        exclude_none=True,
        exclude={"confirm", "save_as_draft"},
    )
    draft.payload = serialized
    db.add(draft)
    db.commit()
    db.refresh(draft)

    details = {"store_id": payload.store_id}
    if reason:
        details["reason"] = reason
    _log_action(
        db,
        action="pos_draft_saved",
        entity_type="pos_draft",
        entity_id=str(draft.id),
        performed_by_id=saved_by_id,
        details=json.dumps(details),
    )
    db.commit()
    db.refresh(draft)
    enqueue_sync_outbox(
        db,
        entity_type="pos_draft",
        entity_id=str(draft.id),
        operation="UPSERT",
        payload=_pos_draft_payload(draft),
    )
    return draft


def delete_pos_draft(db: Session, draft_id: int, *, removed_by_id: int | None = None) -> None:
    statement = select(models.POSDraftSale).where(models.POSDraftSale.id == draft_id)
    draft = db.scalars(statement).first()
    if draft is None:
        raise LookupError("pos_draft_not_found")
    store_id = draft.store_id
    db.delete(draft)
    db.commit()
    _log_action(
        db,
        action="pos_draft_removed",
        entity_type="pos_draft",
        entity_id=str(draft_id),
        performed_by_id=removed_by_id,
        details=json.dumps({"store_id": store_id}),
    )
    db.commit()
    enqueue_sync_outbox(
        db,
        entity_type="pos_draft",
        entity_id=str(draft_id),
        operation="DELETE",
        payload={"id": draft_id, "store_id": store_id},
    )


def register_pos_sale(
    db: Session,
    payload: schemas.POSSaleRequest,
    *,
    performed_by_id: int,
    reason: str | None = None,
) -> tuple[models.Sale, list[str]]:
    if not payload.confirm:
        raise ValueError("pos_confirmation_required")

    config = get_pos_config(db, payload.store_id)
    sale_payload = schemas.SaleCreate(
        store_id=payload.store_id,
        customer_id=payload.customer_id,
        customer_name=payload.customer_name,
        payment_method=payload.payment_method,
        discount_percent=payload.discount_percent,
        notes=payload.notes,
        items=[
            schemas.SaleItemCreate(
                device_id=item.device_id,
                quantity=item.quantity,
                discount_percent=item.discount_percent,
            )
            for item in payload.items
        ],
    )
    tax_value = config.tax_rate if payload.apply_taxes else Decimal("0")
    sale = create_sale(
        db,
        sale_payload,
        performed_by_id=performed_by_id,
        tax_rate=tax_value,
        reason=reason,
    )

    warnings: list[str] = []
    for item in payload.items:
        device = get_device(db, payload.store_id, item.device_id)
        if device.quantity <= 0:
            warnings.append(
                f"{device.sku} sin existencias en la sucursal"
            )
        elif device.quantity <= 2:
            warnings.append(
                f"Stock bajo de {device.sku}: quedan {device.quantity} unidades"
            )

    if payload.draft_id:
        try:
            delete_pos_draft(db, payload.draft_id, removed_by_id=performed_by_id)
        except LookupError:
            pass

    if payload.cash_session_id:
        session = get_cash_session(db, payload.cash_session_id)
        if session.status != models.CashSessionStatus.ABIERTO:
            raise ValueError("cash_session_not_open")
        sale.cash_session_id = session.id
        db.add(sale)
        db.commit()
        db.refresh(sale)

    db.refresh(sale)
    return sale, warnings

def list_backup_jobs(db: Session, limit: int = 50) -> list[models.BackupJob]:
    statement = (
        select(models.BackupJob)
        .order_by(models.BackupJob.executed_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def build_inventory_snapshot(db: Session) -> dict[str, object]:
    stores_stmt = (
        select(models.Store)
        .options(joinedload(models.Store.devices))
        .order_by(models.Store.name.asc())
    )
    stores = list(db.scalars(stores_stmt).unique())

    users_stmt = (
        select(models.User)
        .options(joinedload(models.User.roles).joinedload(models.UserRole.role))
        .order_by(models.User.username.asc())
    )
    users = list(db.scalars(users_stmt).unique())

    movements_stmt = select(models.InventoryMovement).order_by(models.InventoryMovement.created_at.desc())
    movements = list(db.scalars(movements_stmt))

    sync_stmt = select(models.SyncSession).order_by(models.SyncSession.started_at.desc())
    sync_sessions = list(db.scalars(sync_stmt))

    audit_stmt = select(models.AuditLog).order_by(models.AuditLog.created_at.desc())
    audits = list(db.scalars(audit_stmt))

    total_device_records = 0
    total_units = 0
    total_inventory_value = Decimal("0")

    stores_payload: list[dict[str, object]] = []
    for store in stores:
        devices_payload = [
            {
                "id": device.id,
                "sku": device.sku,
                "name": device.name,
                "quantity": device.quantity,
                "store_id": device.store_id,
                "unit_price": float(device.unit_price or Decimal("0")),
                "inventory_value": float(_device_value(device)),
                "imei": device.imei,
                "serial": device.serial,
                "marca": device.marca,
                "modelo": device.modelo,
                "categoria": device.categoria,
                "condicion": device.condicion,
                "color": device.color,
                "capacidad_gb": device.capacidad_gb,
                "capacidad": device.capacidad,
                "estado_comercial": device.estado_comercial.value,
                "estado": device.estado,
                "proveedor": device.proveedor,
                "costo_unitario": float(device.costo_unitario or Decimal("0")),
                "margen_porcentaje": float(device.margen_porcentaje or Decimal("0")),
                "garantia_meses": device.garantia_meses,
                "lote": device.lote,
                "fecha_compra": device.fecha_compra.isoformat()
                if device.fecha_compra
                else None,
                "fecha_ingreso": device.fecha_ingreso.isoformat()
                if device.fecha_ingreso
                else None,
                "ubicacion": device.ubicacion,
                "descripcion": device.descripcion,
                "imagen_url": device.imagen_url,
            }
            for device in store.devices
        ]
        store_units = sum(device.quantity for device in store.devices)
        store_value = _to_decimal(store.inventory_value or Decimal("0"))
        total_device_records += len(devices_payload)
        total_units += store_units
        total_inventory_value += store_value

        stores_payload.append(
            {
                "id": store.id,
                "name": store.name,
                "location": store.location,
                "timezone": store.timezone,
                "inventory_value": float(store_value),
                "device_count": len(devices_payload),
                "total_units": store_units,
                "devices": devices_payload,
            }
        )

    snapshot = {
        "stores": stores_payload,
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "roles": [role.role.name for role in user.roles],
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ],
        "movements": [
            {
                "id": movement.id,
                "sucursal_destino_id": movement.store_id,
                "sucursal_origen_id": movement.source_store_id,
                "device_id": movement.device_id,
                "movement_type": movement.movement_type.value,
                "quantity": movement.quantity,
                "comentario": movement.comment,
                "usuario_id": movement.performed_by_id,
                "fecha": movement.created_at.isoformat(),
            }
            for movement in movements
        ],
        "sync_sessions": [
            {
                "id": sync_session.id,
                "store_id": sync_session.store_id,
                "mode": sync_session.mode.value,
                "status": sync_session.status.value,
                "started_at": sync_session.started_at.isoformat(),
                "finished_at": sync_session.finished_at.isoformat()
                if sync_session.finished_at
                else None,
                "triggered_by_id": sync_session.triggered_by_id,
                "error_message": sync_session.error_message,
            }
            for sync_session in sync_sessions
        ],
        "audit_logs": [
            {
                "id": audit.id,
                "action": audit.action,
                "entity_type": audit.entity_type,
                "entity_id": audit.entity_id,
                "details": audit.details,
                "performed_by_id": audit.performed_by_id,
                "created_at": audit.created_at.isoformat(),
            }
            for audit in audits
        ],
        "summary": {
            "store_count": len(stores),
            "device_records": total_device_records,
            "total_units": total_units,
            "inventory_value": float(
                total_inventory_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
        },
    }
    return snapshot
