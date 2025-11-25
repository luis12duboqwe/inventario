"""Operaciones de base de datos para las entidades principales."""
from __future__ import annotations

import base64
import binascii
import calendar
import copy
import csv
import json
import math
import re
import secrets
import textwrap
from dataclasses import dataclass
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from io import StringIO
from typing import Any, Literal
from uuid import uuid4

from pydantic import ValidationError

from passlib.context import CryptContext
from sqlalchemy import and_, case, cast, desc, func, literal, or_, select, tuple_, String
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.sql import ColumnElement, Select

from backend.core.logging import logger as core_logger

from . import models, schemas, telemetry
from .core.roles import ADMIN, GERENTE, INVITADO, OPERADOR
from .core.transactions import flush_session, transactional_session
# // [PACK30-31-BACKEND]
from .services import (
    credit,
    inventory_accounting,
    inventory_audit,
    inventory_availability,
    purchase_documents,
    promotions,
)
from .services.purchases import assign_supplier_batch
from .services.sales import consume_supplier_batch
from .services.inventory import calculate_inventory_valuation
from .config import settings
from .core.settings import inventory_alert_settings, return_policy_settings
from . import security_tokens as token_protection
from .utils import audit as audit_utils
from .utils import audit_trail as audit_trail_utils
from .utils.cache import TTLCache

logger = core_logger.bind(component=__name__)

_PIN_CONTEXT = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt_sha256", "bcrypt"], deprecated="auto"
)


def _verify_supervisor_pin_hash(hashed: str, candidate: str) -> bool:
    try:
        return _PIN_CONTEXT.verify(candidate, hashed)
    except ValueError:
        return False


def _token_filter(column, candidate: str):
    protected = token_protection.protect_token(candidate)
    return or_(column == candidate, column == protected)


DEFAULT_SECURITY_MODULES: list[str] = [
    "usuarios",
    "seguridad",
    "inventario",
    "precios",
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

_RESTRICTED_DELETE_FOR_MANAGER = {"seguridad",
                                  "respaldos", "usuarios", "actualizaciones"}
_RESTRICTED_EDIT_FOR_OPERATOR = {
    "seguridad", "respaldos", "usuarios", "actualizaciones", "auditoria"}
_RESTRICTED_DELETE_FOR_OPERATOR = _RESTRICTED_EDIT_FOR_OPERATOR | {
    "reportes", "sincronizacion"}

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
            parsed_cost = _to_decimal(raw_cost)
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


def _to_decimal(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _get_supplier_by_name(
    db: Session, supplier_name: str | None
) -> models.Supplier | None:
    if not supplier_name:
        return None
    normalized = supplier_name.strip().lower()
    if not normalized:
        return None
    statement = (
        select(models.Supplier)
        .where(func.lower(models.Supplier.name) == normalized)
        .limit(1)
    )
    return db.scalars(statement).first()


def _quantize_currency(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _quantize_points(value: Decimal) -> Decimal:
    """Normaliza valores de puntos de lealtad con dos decimales."""

    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _quantize_rate(value: Decimal) -> Decimal:
    """Normaliza tasas de acumulación y canje a cuatro decimales."""

    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _format_currency(value: Decimal | float | int) -> str:
    normalized = _quantize_currency(_to_decimal(value))
    return f"{normalized:.2f}"


def _calculate_weighted_average_cost(
    current_quantity: int,
    current_cost: Decimal,
    incoming_quantity: int,
    incoming_cost: Decimal,
) -> Decimal:
    if incoming_quantity <= 0:
        return _to_decimal(current_cost)
    existing_quantity = _to_decimal(current_quantity)
    new_quantity = existing_quantity + _to_decimal(incoming_quantity)
    if new_quantity <= Decimal("0"):
        return Decimal("0")
    existing_total = _to_decimal(current_cost) * existing_quantity
    incoming_total = _to_decimal(incoming_cost) * \
        _to_decimal(incoming_quantity)
    return (existing_total + incoming_total) / new_quantity


def _normalize_date_range(
    date_from: date | datetime | None, date_to: date | datetime | None
) -> tuple[datetime, datetime]:
    now = datetime.utcnow()

    if isinstance(date_from, datetime):
        start_dt = date_from
        if start_dt.time() == datetime.min.time():
            start_dt = start_dt.replace(
                hour=0, minute=0, second=0, microsecond=0)
    elif isinstance(date_from, date):
        start_dt = datetime.combine(date_from, datetime.min.time())
    else:
        start_dt = now - timedelta(days=30)

    if isinstance(date_to, datetime):
        end_dt = date_to
        if end_dt.time() == datetime.min.time():
            end_dt = end_dt.replace(
                hour=23, minute=59, second=59, microsecond=999999)
    elif isinstance(date_to, date):
        end_dt = datetime.combine(date_to, datetime.max.time())
    else:
        end_dt = now

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    # Salvaguarda adicional: si tras reordenar el rango el extremo superior
    # quedó en inicio de día (00:00:00), amplíalo al final del día para no
    # perder movimientos registrados durante la jornada destino.
    if end_dt.time() == datetime.min.time():
        end_dt = end_dt.replace(
            hour=23, minute=59, second=59, microsecond=999999)

    return start_dt, end_dt


_PERSISTENT_ALERTS_CACHE: TTLCache[list[dict[str, object]]] = TTLCache(
    ttl_seconds=60.0)


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
        intercept = sum_y / n if n else 0.0
    else:
        slope = ((n * sum_xy) - (sum_x * sum_y)) / denominator
        intercept = (sum_y - (slope * sum_x)) / n

    denominator_r = ((n * sum_xx) - (sum_x**2)) * ((n * sum_yy) - (sum_y**2))
    if denominator_r <= 0 or math.isclose(denominator_r, 0.0):
        r_squared = 0.0
    else:
        numerator = ((n * sum_xy) - (sum_x * sum_y)) ** 2
        r_squared = numerator / denominator_r

    return slope, intercept, r_squared


def _project_linear_sum(
    slope: float,
    intercept: float,
    start_index: int,
    horizon: int,
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
    "customer_privacy_request": models.SyncOutboxPriority.LOW,
    "customer_ledger_entry": models.SyncOutboxPriority.NORMAL,
    "supplier_ledger_entry": models.SyncOutboxPriority.NORMAL,
    "pos_config": models.SyncOutboxPriority.NORMAL,
    "supplier": models.SyncOutboxPriority.NORMAL,
    "cash_session": models.SyncOutboxPriority.NORMAL,
    "device": models.SyncOutboxPriority.NORMAL,
    "rma_request": models.SyncOutboxPriority.NORMAL,
    "inventory": models.SyncOutboxPriority.HIGH,
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
    "config_parameter": "configuracion",
    "config_rate": "configuracion",
    "config_template": "configuracion",
    "config_sync": "configuracion",
    "user": "usuarios",
    "role": "usuarios",
    "auth": "usuarios",
    "sync_session": "sincronizacion",
    "store": "inventario",
    "pos_fiscal_print": "ventas",
    "customer": "clientes",
    "customer_privacy_request": "clientes",
    "supplier_ledger_entry": "proveedores",
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
    with transactional_session(db):
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
        flush_session(db)
    return entry


def _recalculate_sale_price(device: models.Device) -> None:
    base_cost = _to_decimal(device.costo_unitario)
    margin = _to_decimal(device.margen_porcentaje)
    sale_factor = Decimal("1") + (margin / Decimal("100"))
    recalculated = (
        base_cost * sale_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    device.unit_price = recalculated
    device.precio_venta = recalculated


def _normalize_store_ids(store_ids: Iterable[int] | None) -> set[int] | None:
    if not store_ids:
        return None
    normalized = {int(store_id) for store_id in store_ids if int(store_id) > 0}
    return normalized or None


def log_audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | int,
    performed_by_id: int | None,
    details: str | Mapping[str, object] | None = None,
) -> models.AuditLog:
    entity_id_str = str(entity_id)
    if isinstance(details, Mapping):
        try:
            serialized_details = json.dumps(details, ensure_ascii=False)
        except TypeError:
            safe_details = {
                key: value if isinstance(
                    value, (str, int, float, bool, type(None))) else str(value)
                for key, value in details.items()
            }
            serialized_details = json.dumps(safe_details, ensure_ascii=False)
    else:
        serialized_details = details
    description_text: str | None = None
    if isinstance(serialized_details, str):
        description_text, _ = audit_trail_utils.parse_audit_details(
            serialized_details)
    if description_text is None and isinstance(details, str):
        description_text = details
    if description_text is None:
        description_text = f"{action} sobre {entity_type} {entity_id}".strip()
    with transactional_session(db):
        log = models.AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id_str,
            performed_by_id=performed_by_id,
            details=serialized_details,
        )
        db.add(log)
        flush_session(db)
        usuario = None
        if performed_by_id is not None:
            user = db.get(models.User, performed_by_id)
            if user is not None:
                usuario = user.username
        module = _resolve_system_module(entity_type)
        level = _map_system_level(action, description_text)
        _create_system_log(
            db,
            audit_log=log,
            usuario=usuario,
            module=module,
            action=action,
            description=description_text,
            level=level,
        )
        invalidate_persistent_audit_alerts_cache()
    return log


_log_action = log_audit_event


def register_system_error(
    db: Session,
    *,
    mensaje: str,
    stack_trace: str | None,
    modulo: str,
    usuario: str | None,
    ip_origen: str | None = None,
) -> models.SystemError:
    with transactional_session(db):
        normalized_module = (modulo or "general").lower()
        error = models.SystemError(
            mensaje=mensaje,
            stack_trace=stack_trace,
            modulo=normalized_module,
            fecha=datetime.utcnow(),
            usuario=usuario,
        )
        db.add(error)
        flush_session(db)
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
    limit: int = 50,
    offset: int = 0,
) -> list[models.SystemLog]:
    statement = (
        select(models.SystemLog)
        .order_by(models.SystemLog.fecha.desc())
        .offset(offset)
        .limit(limit)
    )
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
    return list(db.scalars(statement))


def list_system_errors(
    db: Session,
    *,
    usuario: str | None = None,
    modulo: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.SystemError]:
    statement = (
        select(models.SystemError)
        .order_by(models.SystemError.fecha.desc())
        .offset(offset)
        .limit(limit)
    )
    if usuario:
        statement = statement.where(models.SystemError.usuario == usuario)
    if modulo:
        statement = statement.where(
            models.SystemError.modulo == modulo.lower())
    if date_from:
        statement = statement.where(models.SystemError.fecha >= date_from)
    if date_to:
        statement = statement.where(models.SystemError.fecha <= date_to)
    return list(db.scalars(statement))


def _apply_system_log_filters(
    statement,
    *,
    module: str | None,
    severity: models.SystemLogLevel | None,
    date_from: datetime | None,
    date_to: datetime | None,
):
    if module:
        statement = statement.where(models.SystemLog.modulo == module)
    if severity:
        statement = statement.where(models.SystemLog.nivel == severity)
    if date_from:
        statement = statement.where(models.SystemLog.fecha >= date_from)
    if date_to:
        statement = statement.where(models.SystemLog.fecha <= date_to)
    return statement


def _apply_system_error_filters(
    statement,
    *,
    module: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
):
    if module:
        statement = statement.where(models.SystemError.modulo == module)
    if date_from:
        statement = statement.where(models.SystemError.fecha >= date_from)
    if date_to:
        statement = statement.where(models.SystemError.fecha <= date_to)
    return statement


def purge_system_logs(
    db: Session,
    *,
    retention_days: int = 180,
    keep_critical: bool = True,
    reference: datetime | None = None,
) -> int:
    """Purga logs del sistema anteriores al cutoff de retención.

    Preserva CRITICAL si keep_critical=True.
    Devuelve cantidad eliminada.
    """
    now = reference or datetime.utcnow()
    cutoff = now - timedelta(days=retention_days)
    query = db.query(models.SystemLog).filter(models.SystemLog.fecha < cutoff)
    if keep_critical:
        query = query.filter(models.SystemLog.nivel !=
                             models.SystemLogLevel.CRITICAL)
    deleted = query.delete(synchronize_session=False)
    db.commit()
    return int(deleted or 0)


def _severity_weight(level: models.SystemLogLevel) -> int:
    if level == models.SystemLogLevel.CRITICAL:
        return 3
    if level == models.SystemLogLevel.ERROR:
        return 2
    if level == models.SystemLogLevel.WARNING:
        return 1
    return 0


def build_global_report_overview(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    module: str | None = None,
    severity: models.SystemLogLevel | None = None,
) -> schemas.GlobalReportOverview:
    module_filter = module.lower() if module else None
    severity_filter = severity

    log_stmt = select(models.SystemLog).order_by(models.SystemLog.fecha.desc())
    log_stmt = _apply_system_log_filters(
        log_stmt,
        module=module_filter,
        severity=severity_filter,
        date_from=date_from,
        date_to=date_to,
    ).limit(20)
    logs = list(db.scalars(log_stmt))

    include_errors = severity_filter in (
        None,
        models.SystemLogLevel.ERROR,
        models.SystemLogLevel.CRITICAL,
    )

    if include_errors:
        error_stmt = select(models.SystemError).order_by(
            models.SystemError.fecha.desc()).limit(10)
        error_stmt = _apply_system_error_filters(
            error_stmt,
            module=module_filter,
            date_from=date_from,
            date_to=date_to,
        )
        errors = list(db.scalars(error_stmt))
    else:
        errors = []

    totals_stmt = select(
        func.count(models.SystemLog.id).label("total"),
        func.sum(
            case((models.SystemLog.nivel == models.SystemLogLevel.INFO, 1), else_=0)
        ).label("info"),
        func.sum(
            case((models.SystemLog.nivel == models.SystemLogLevel.WARNING, 1), else_=0)
        ).label("warning"),
        func.sum(
            case((models.SystemLog.nivel == models.SystemLogLevel.ERROR, 1), else_=0)
        ).label("error"),
        func.sum(
            case((models.SystemLog.nivel == models.SystemLogLevel.CRITICAL, 1), else_=0)
        ).label("critical"),
    )
    totals_stmt = _apply_system_log_filters(
        totals_stmt,
        module=module_filter,
        severity=severity_filter,
        date_from=date_from,
        date_to=date_to,
    )
    totals_row = db.execute(totals_stmt).first()
    total_logs = int(totals_row.total or 0) if totals_row else 0
    info_count = int(totals_row.info or 0) if totals_row else 0
    warning_count = int(totals_row.warning or 0) if totals_row else 0
    error_count = int(totals_row.error or 0) if totals_row else 0
    critical_count = int(totals_row.critical or 0) if totals_row else 0

    if include_errors:
        error_total_stmt = select(func.count(models.SystemError.id))
        error_total_stmt = _apply_system_error_filters(
            error_total_stmt,
            module=module_filter,
            date_from=date_from,
            date_to=date_to,
        )
        errors_total = int(db.execute(error_total_stmt).scalar_one() or 0)
        latest_error_stmt = select(func.max(models.SystemError.fecha))
        latest_error_stmt = _apply_system_error_filters(
            latest_error_stmt,
            module=module_filter,
            date_from=date_from,
            date_to=date_to,
        )
        latest_error_at = db.execute(latest_error_stmt).scalar_one()
    else:
        errors_total = 0
        latest_error_at = None

    module_expr = models.SystemLog.modulo
    module_stmt = (
        select(module_expr, func.count(models.SystemLog.id).label("total"))
        .group_by(module_expr)
        .order_by(func.count(models.SystemLog.id).desc())
    )
    module_stmt = _apply_system_log_filters(
        module_stmt,
        module=module_filter,
        severity=severity_filter,
        date_from=date_from,
        date_to=date_to,
    )
    module_rows = db.execute(module_stmt).all()
    module_breakdown = [
        schemas.GlobalReportBreakdownItem(
            name=row[0], total=int(row.total or 0))
        for row in module_rows
    ]

    level_expr = models.SystemLog.nivel
    severity_stmt = (
        select(level_expr, func.count(models.SystemLog.id).label("total"))
        .group_by(level_expr)
        .order_by(func.count(models.SystemLog.id).desc())
    )
    severity_stmt = _apply_system_log_filters(
        severity_stmt,
        module=module_filter,
        severity=severity_filter,
        date_from=date_from,
        date_to=date_to,
    )
    severity_rows = db.execute(severity_stmt).all()
    severity_breakdown = [
        schemas.GlobalReportBreakdownItem(
            name=(row[0].value if isinstance(
                row[0], models.SystemLogLevel) else str(row[0])),
            total=int(row.total or 0),
        )
        for row in severity_rows
    ]

    latest_log_stmt = select(func.max(models.SystemLog.fecha))
    latest_log_stmt = _apply_system_log_filters(
        latest_log_stmt,
        module=module_filter,
        severity=severity_filter,
        date_from=date_from,
        date_to=date_to,
    )
    latest_log_at = db.execute(latest_log_stmt).scalar_one()

    last_activity_candidates = [
        value for value in [latest_log_at, latest_error_at] if value is not None
    ]
    last_activity_at = max(
        last_activity_candidates) if last_activity_candidates else None

    sync_stats = get_sync_outbox_statistics(db)
    sync_pending = sum(
        max(int(entry.get("pending", 0) or 0), 0) for entry in sync_stats
    )
    sync_failed = sum(int(entry.get("failed", 0) or 0) for entry in sync_stats)

    filters = schemas.GlobalReportFiltersState(
        date_from=date_from,
        date_to=date_to,
        module=module_filter,
        severity=severity_filter,
    )

    totals = schemas.GlobalReportTotals(
        logs=total_logs,
        errors=errors_total,
        info=info_count,
        warning=warning_count,
        error=error_count,
        critical=critical_count,
        sync_pending=sync_pending,
        sync_failed=sync_failed,
        last_activity_at=last_activity_at,
    )

    alerts_map: dict[tuple[str, str | None, str | None],
                     schemas.GlobalReportAlert] = {}

    for log in logs:
        if log.nivel not in (models.SystemLogLevel.ERROR, models.SystemLogLevel.CRITICAL):
            continue
        key = ("critical_log", log.modulo, log.accion)
        existing = alerts_map.get(key)
        if existing:
            existing.count += 1
            if _severity_weight(log.nivel) > _severity_weight(existing.level):
                existing.level = log.nivel
            if existing.occurred_at is None or (log.fecha and log.fecha > existing.occurred_at):
                existing.occurred_at = log.fecha
            if log.descripcion:
                existing.message = log.descripcion
        else:
            alerts_map[key] = schemas.GlobalReportAlert(
                type="critical_log",
                level=log.nivel,
                module=log.modulo,
                message=log.descripcion,
                occurred_at=log.fecha,
                reference=log.accion,
                count=1,
            )

    for error in errors:
        key = ("system_error", error.modulo, error.mensaje)
        existing = alerts_map.get(key)
        if existing:
            existing.count += 1
            if existing.occurred_at is None or (error.fecha and error.fecha > existing.occurred_at):
                existing.occurred_at = error.fecha
        else:
            error_reference = getattr(error, "id", None)
            if error_reference is None and hasattr(error, "id_error"):
                error_reference = getattr(error, "id_error")
            alerts_map[key] = schemas.GlobalReportAlert(
                type="system_error",
                level=models.SystemLogLevel.ERROR,
                module=error.modulo,
                message=error.mensaje,
                occurred_at=error.fecha,
                reference=str(
                    error_reference) if error_reference is not None else None,
                count=1,
            )

    for stat in sync_stats:
        failed = int(stat.get("failed", 0) or 0)
        pending = max(int(stat.get("pending", 0) or 0), 0)
        if failed <= 0:
            continue
        severity_level = (
            models.SystemLogLevel.CRITICAL if failed >= 5 else models.SystemLogLevel.ERROR
        )
        entity_type = str(stat.get("entity_type") or "sync")
        message = f"{failed} eventos de sincronización fallidos para {entity_type}"
        occurred_at = stat.get("latest_update")
        alerts_map[("sync_failure", entity_type, message)] = schemas.GlobalReportAlert(
            type="sync_failure",
            level=severity_level,
            module=entity_type,
            message=message,
            occurred_at=occurred_at,
            reference=str(stat.get("entity_type") or "sync"),
            count=failed,
        )
        if pending >= 25:
            pending_message = f"{pending} eventos pendientes en {entity_type}"
            alerts_map[("sync_failure", f"{entity_type}_pending", pending_message)] = (
                schemas.GlobalReportAlert(
                    type="sync_failure",
                    level=models.SystemLogLevel.WARNING,
                    module=entity_type,
                    message=pending_message,
                    occurred_at=occurred_at,
                    reference=str(stat.get("entity_type") or "sync"),
                    count=pending,
                )
            )

    alerts = sorted(
        alerts_map.values(),
        key=lambda alert: (_severity_weight(alert.level),
                           alert.occurred_at or datetime.min),
        reverse=True,
    )

    recent_logs = [schemas.SystemLogEntry.model_validate(
        item) for item in logs]
    recent_errors = [schemas.SystemErrorEntry.model_validate(
        item) for item in errors]

    return schemas.GlobalReportOverview(
        generated_at=datetime.utcnow(),
        filters=filters,
        totals=totals,
        module_breakdown=module_breakdown,
        severity_breakdown=severity_breakdown,
        recent_logs=recent_logs,
        recent_errors=recent_errors,
        alerts=alerts,
    )


def build_global_report_dashboard(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    module: str | None = None,
    severity: models.SystemLogLevel | None = None,
) -> schemas.GlobalReportDashboard:
    module_filter = module.lower() if module else None
    severity_filter = severity

    date_expr = func.date(models.SystemLog.fecha)
    activity_stmt = select(
        date_expr.label("activity_date"),
        func.sum(
            case((models.SystemLog.nivel == models.SystemLogLevel.INFO, 1), else_=0)
        ).label("info"),
        func.sum(
            case((models.SystemLog.nivel == models.SystemLogLevel.WARNING, 1), else_=0)
        ).label("warning"),
        func.sum(
            case((models.SystemLog.nivel == models.SystemLogLevel.ERROR, 1), else_=0)
        ).label("error"),
        func.sum(
            case((models.SystemLog.nivel == models.SystemLogLevel.CRITICAL, 1), else_=0)
        ).label("critical"),
    ).group_by(date_expr).order_by(date_expr)
    activity_stmt = _apply_system_log_filters(
        activity_stmt,
        module=module_filter,
        severity=severity_filter,
        date_from=date_from,
        date_to=date_to,
    )
    activity_rows = db.execute(activity_stmt).all()

    series_map: dict[date, dict[str, int]] = {}
    for row in activity_rows:
        raw_date = row.activity_date
        if isinstance(raw_date, str):
            activity_date = date.fromisoformat(raw_date)
        else:
            activity_date = raw_date
        series_map[activity_date] = {
            "info": int(row.info or 0),
            "warning": int(row.warning or 0),
            "error": int(row.error or 0),
            "critical": int(row.critical or 0),
            "system_errors": 0,
        }

    include_errors = severity_filter in (
        None,
        models.SystemLogLevel.ERROR,
        models.SystemLogLevel.CRITICAL,
    )
    if include_errors:
        error_date_expr = func.date(models.SystemError.fecha)
        error_stmt = (
            select(error_date_expr.label("activity_date"),
                   func.count(models.SystemError.id))
            .group_by(error_date_expr)
            .order_by(error_date_expr)
        )
        error_stmt = _apply_system_error_filters(
            error_stmt,
            module=module_filter,
            date_from=date_from,
            date_to=date_to,
        )
        for row in db.execute(error_stmt):
            raw_date = row.activity_date
            if isinstance(raw_date, str):
                activity_date = date.fromisoformat(raw_date)
            else:
                activity_date = raw_date
            entry = series_map.setdefault(
                activity_date,
                {"info": 0, "warning": 0, "error": 0,
                    "critical": 0, "system_errors": 0},
            )
            entry["system_errors"] = int(row[1] or 0)

    activity_series = [
        schemas.GlobalReportSeriesPoint(
            date=series_date,
            info=values["info"],
            warning=values["warning"],
            error=values["error"],
            critical=values["critical"],
            system_errors=values["system_errors"],
        )
        for series_date, values in sorted(series_map.items())
    ]

    module_expr = models.SystemLog.modulo
    module_stmt = (
        select(module_expr, func.count(models.SystemLog.id).label("total"))
        .group_by(module_expr)
        .order_by(func.count(models.SystemLog.id).desc())
    )
    module_stmt = _apply_system_log_filters(
        module_stmt,
        module=module_filter,
        severity=severity_filter,
        date_from=date_from,
        date_to=date_to,
    )
    module_rows = db.execute(module_stmt).all()
    module_distribution = [
        schemas.GlobalReportBreakdownItem(
            name=row[0], total=int(row.total or 0))
        for row in module_rows
    ]

    level_expr = models.SystemLog.nivel
    severity_stmt = (
        select(level_expr, func.count(models.SystemLog.id).label("total"))
        .group_by(level_expr)
        .order_by(func.count(models.SystemLog.id).desc())
    )
    severity_stmt = _apply_system_log_filters(
        severity_stmt,
        module=module_filter,
        severity=severity_filter,
        date_from=date_from,
        date_to=date_to,
    )
    severity_rows = db.execute(severity_stmt).all()
    severity_distribution = [
        schemas.GlobalReportBreakdownItem(
            name=(row[0].value if isinstance(
                row[0], models.SystemLogLevel) else str(row[0])),
            total=int(row.total or 0),
        )
        for row in severity_rows
    ]

    filters = schemas.GlobalReportFiltersState(
        date_from=date_from,
        date_to=date_to,
        module=module_filter,
        severity=severity_filter,
    )

    return schemas.GlobalReportDashboard(
        generated_at=datetime.utcnow(),
        filters=filters,
        activity_series=activity_series,
        module_distribution=module_distribution,
        severity_distribution=severity_distribution,
    )


# // [PACK29-*] Filtros comunes para reportes de ventas por rango y sucursal
def _apply_sales_base_filters(
    statement,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    store_id: int | None,
):
    statement = statement.where(func.upper(models.Sale.status) != "CANCELADA")
    if store_id is not None:
        statement = statement.where(models.Sale.store_id == store_id)
    if date_from is not None:
        statement = statement.where(models.Sale.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(models.Sale.created_at < date_to)
    return statement


# // [PACK29-*] Totales de devoluciones para reutilizar en reportes de ventas
def _sales_returns_totals(
    db: Session,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    store_id: int | None,
):
    returns_stmt = (
        select(
            func.coalesce(
                func.sum(
                    (models.SaleItem.total_line /
                     func.nullif(models.SaleItem.quantity, 0))
                    * models.SaleReturn.quantity
                ),
                0,
            ).label("refund_total"),
            func.count(models.SaleReturn.id).label("return_count"),
        )
        .select_from(models.SaleReturn)
        .join(models.Sale, models.Sale.id == models.SaleReturn.sale_id)
        .join(
            models.SaleItem,
            and_(
                models.SaleItem.sale_id == models.SaleReturn.sale_id,
                models.SaleItem.device_id == models.SaleReturn.device_id,
            ),
        )
        .where(func.upper(models.Sale.status) != "CANCELADA")
    )
    if store_id is not None:
        returns_stmt = returns_stmt.where(models.Sale.store_id == store_id)
    if date_from is not None:
        returns_stmt = returns_stmt.where(
            models.SaleReturn.created_at >= date_from)
    if date_to is not None:
        returns_stmt = returns_stmt.where(
            models.SaleReturn.created_at < date_to)
    row = db.execute(returns_stmt).first()
    refund_total = _to_decimal(row.refund_total if row else Decimal("0"))
    return_count = int(row.return_count or 0) if row else 0
    return (
        refund_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        return_count,
    )


# // [PACK29-*] Índice sugerido: CREATE INDEX IF NOT EXISTS ix_ventas_store_created_at ON ventas (sucursal_id, fecha)
def build_sales_summary_report(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    store_id: int | None = None,
) -> schemas.SalesSummaryReport:
    sales_stmt = (
        select(
            func.coalesce(func.sum(models.Sale.total_amount),
                          0).label("total_sales"),
            func.count(models.Sale.id).label("orders"),
        )
        .select_from(models.Sale)
    )
    sales_stmt = _apply_sales_base_filters(
        sales_stmt,
        date_from=date_from,
        date_to=date_to,
        store_id=store_id,
    )
    row = db.execute(sales_stmt).first()
    total_sales = _to_decimal(row.total_sales if row else Decimal("0"))
    total_sales = total_sales.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_orders = int(row.orders or 0) if row else 0
    avg_ticket = Decimal("0")
    if total_orders > 0:
        avg_ticket = (total_sales / Decimal(total_orders)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    refund_total, returns_count = _sales_returns_totals(
        db,
        date_from=date_from,
        date_to=date_to,
        store_id=store_id,
    )
    net_sales = (total_sales - refund_total).quantize(Decimal("0.01"),
                                                      rounding=ROUND_HALF_UP)
    return schemas.SalesSummaryReport(
        total_sales=float(total_sales),
        total_orders=total_orders,
        avg_ticket=float(avg_ticket),
        returns_count=returns_count,
        net=float(net_sales),
    )


# // [PACK29-*] Índice sugerido: CREATE INDEX IF NOT EXISTS ix_detalle_ventas_store_fecha ON detalle_ventas (venta_id)
def build_sales_by_product_report(
    db: Session,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    store_id: int | None = None,
    limit: int = 20,
) -> list[schemas.SalesByProductItem]:
    items_stmt = (
        select(
            models.Device.id.label("device_id"),
            models.Device.sku,
            models.Device.name,
            func.coalesce(func.sum(models.SaleItem.quantity),
                          0).label("quantity"),
            func.coalesce(func.sum(models.SaleItem.total_line),
                          0).label("gross"),
        )
        .select_from(models.SaleItem)
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .where(func.upper(models.Sale.status) != "CANCELADA")
        .group_by(models.Device.id, models.Device.sku, models.Device.name)
        .order_by(func.coalesce(func.sum(models.SaleItem.total_line), 0).desc())
        .limit(limit)
    )
    if store_id is not None:
        items_stmt = items_stmt.where(models.Sale.store_id == store_id)
    if date_from is not None:
        items_stmt = items_stmt.where(models.Sale.created_at >= date_from)
    if date_to is not None:
        items_stmt = items_stmt.where(models.Sale.created_at < date_to)
    product_rows = db.execute(items_stmt).all()

    returns_stmt = (
        select(
            models.SaleReturn.device_id,
            func.coalesce(
                func.sum(
                    (models.SaleItem.total_line /
                     func.nullif(models.SaleItem.quantity, 0))
                    * models.SaleReturn.quantity
                ),
                0,
            ).label("refund_total"),
        )
        .select_from(models.SaleReturn)
        .join(models.Sale, models.Sale.id == models.SaleReturn.sale_id)
        .join(
            models.SaleItem,
            and_(
                models.SaleItem.sale_id == models.SaleReturn.sale_id,
                models.SaleItem.device_id == models.SaleReturn.device_id,
            ),
        )
        .where(func.upper(models.Sale.status) != "CANCELADA")
        .group_by(models.SaleReturn.device_id)
    )
    if store_id is not None:
        returns_stmt = returns_stmt.where(models.Sale.store_id == store_id)
    if date_from is not None:
        returns_stmt = returns_stmt.where(
            models.SaleReturn.created_at >= date_from)
    if date_to is not None:
        returns_stmt = returns_stmt.where(
            models.SaleReturn.created_at < date_to)
    refund_rows = db.execute(returns_stmt).all()
    refunds_by_device = {
        row.device_id: _to_decimal(row.refund_total or Decimal("0")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        for row in refund_rows
    }

    items: list[schemas.SalesByProductItem] = []
    for row in product_rows:
        gross_total = _to_decimal(row.gross or Decimal("0")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        net_total = (gross_total - refunds_by_device.get(row.device_id, Decimal("0"))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        quantity = int(row.quantity or 0)
        items.append(
            schemas.SalesByProductItem(
                sku=row.sku,
                name=row.name,
                quantity=quantity,
                gross=float(gross_total),
                net=float(net_total),
            )
        )
    return items


# // [PACK29-*] Resumen sugerido para cierre de caja diario
def build_cash_close_report(
    db: Session,
    *,
    date_from: datetime,
    date_to: datetime,
    store_id: int | None = None,
) -> schemas.CashCloseReport:
    opening_stmt = select(
        func.coalesce(
            func.sum(models.CashRegisterSession.opening_amount), 0).label("opening")
    ).where(
        models.CashRegisterSession.opened_at >= date_from,
        models.CashRegisterSession.opened_at < date_to,
    )
    if store_id is not None:
        opening_stmt = opening_stmt.where(
            models.CashRegisterSession.store_id == store_id)
    opening_row = db.execute(opening_stmt).first()
    opening_total = _to_decimal(opening_row.opening if opening_row else Decimal("0")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    sales_stmt = (
        select(func.coalesce(
            func.sum(models.Sale.total_amount), 0).label("total_sales"))
        .select_from(models.Sale)
    )
    sales_stmt = _apply_sales_base_filters(
        sales_stmt,
        date_from=date_from,
        date_to=date_to,
        store_id=store_id,
    )
    sales_row = db.execute(sales_stmt).first()
    sales_total = _to_decimal(sales_row.total_sales if sales_row else Decimal("0")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    refund_total, _ = _sales_returns_totals(
        db,
        date_from=date_from,
        date_to=date_to,
        store_id=store_id,
    )

    entries_stmt = (
        select(
            models.CashRegisterEntry.entry_type,
            func.coalesce(func.sum(models.CashRegisterEntry.amount), 0),
        )
        .select_from(models.CashRegisterEntry)
        .join(
            models.CashRegisterSession,
            models.CashRegisterEntry.session_id == models.CashRegisterSession.id,
        )
        .where(
            models.CashRegisterEntry.created_at >= date_from,
            models.CashRegisterEntry.created_at < date_to,
        )
    )
    if store_id is not None:
        entries_stmt = entries_stmt.where(
            models.CashRegisterSession.store_id == store_id
        )
    entries_stmt = entries_stmt.group_by(models.CashRegisterEntry.entry_type)
    incomes_total = Decimal("0.00")
    expenses_total = Decimal("0.00")
    for entry_type, total in db.execute(entries_stmt):
        normalized_total = _to_decimal(total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if entry_type == models.CashEntryType.INGRESO:
            incomes_total = normalized_total
        elif entry_type == models.CashEntryType.EGRESO:
            expenses_total = normalized_total

    closing_suggested = (
        opening_total + sales_total + incomes_total - refund_total - expenses_total
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return schemas.CashCloseReport(
        opening=float(opening_total),
        sales_gross=float(sales_total),
        refunds=float(refund_total),
        incomes=float(incomes_total),
        expenses=float(expenses_total),
        closing_suggested=float(closing_suggested),
    )


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
    flush_session(db)
    total_value = db.scalar(
        select(func.coalesce(
            func.sum(models.Device.quantity * models.Device.unit_price), 0))
        .where(models.Device.store_id == store_obj.id)
    )
    normalized_total = _to_decimal(total_value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    store_obj.inventory_value = normalized_total
    db.add(store_obj)
    flush_session(db)
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
        "segment_category": customer.segment_category,
        "tags": customer.tags,
        "tax_id": customer.tax_id,
        "credit_limit": float(customer.credit_limit or Decimal("0")),
        "outstanding_debt": float(customer.outstanding_debt or Decimal("0")),
        "last_interaction_at": customer.last_interaction_at.isoformat() if customer.last_interaction_at else None,
        "privacy_consents": dict(customer.privacy_consents or {}),
        "privacy_metadata": dict(customer.privacy_metadata or {}),
        "privacy_last_request_at": customer.privacy_last_request_at.isoformat()
        if customer.privacy_last_request_at
        else None,
        "updated_at": customer.updated_at.isoformat(),
        "annual_purchase_amount": float(customer.annual_purchase_amount),
        "orders_last_year": customer.orders_last_year,
        "purchase_frequency": customer.purchase_frequency,
        "segment_labels": list(customer.segment_labels),
        "last_purchase_at": customer.last_purchase_at.isoformat()
        if customer.last_purchase_at
        else None,
    }


def _customer_privacy_request_payload(
    request: models.CustomerPrivacyRequest,
) -> dict[str, object]:
    return {
        "id": request.id,
        "customer_id": request.customer_id,
        "request_type": request.request_type.value,
        "status": request.status.value,
        "details": request.details,
        "consent_snapshot": request.consent_snapshot,
        "masked_fields": request.masked_fields,
        "created_at": request.created_at.isoformat(),
        "processed_at": request.processed_at.isoformat()
        if request.processed_at
        else None,
        "processed_by_id": request.processed_by_id,
    }


def _device_sync_payload(device: models.Device) -> dict[str, object]:
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
        "unit_price": float(_to_decimal(device.unit_price)),
        "costo_unitario": float(_to_decimal(device.costo_unitario)),
        "margen_porcentaje": float(_to_decimal(device.margen_porcentaje)),
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


def _inventory_movement_payload(movement: models.InventoryMovement) -> dict[str, object]:
    """Genera el payload de sincronización para un movimiento de inventario."""

    store_name = movement.store.name if movement.store else None
    source_name = movement.source_store.name if movement.source_store else None
    warehouse_name = movement.warehouse.name if movement.warehouse else None
    source_warehouse_name = (
        movement.source_warehouse.name if movement.source_warehouse else None
    )
    device = movement.device
    performed_by = _user_display_name(movement.performed_by)
    created_at = movement.created_at.isoformat() if movement.created_at else None
    reference_type = getattr(movement, "reference_type", None)
    reference_id = getattr(movement, "reference_id", None)
    return {
        "id": movement.id,
        "store_id": movement.store_id,
        "store_name": store_name,
        "source_store_id": movement.source_store_id,
        "source_store_name": source_name,
        "warehouse_id": movement.warehouse_id,
        "warehouse_name": warehouse_name,
        "source_warehouse_id": movement.source_warehouse_id,
        "source_warehouse_name": source_warehouse_name,
        "device_id": movement.device_id,
        "device_sku": device.sku if device else None,
        "movement_type": movement.movement_type.value,
        "quantity": movement.quantity,
        "comment": movement.comment,
        "unit_cost": float(_to_decimal(movement.unit_cost)) if movement.unit_cost is not None else None,
        "performed_by_id": movement.performed_by_id,
        "performed_by_name": performed_by,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "created_at": created_at,
    }


def _normalize_optional_note(note: str | None) -> str | None:
    if note is None:
        return None
    normalized = note.strip()
    return normalized or None


def _register_purchase_status_event(
    db: Session,
    order: models.PurchaseOrder,
    *,
    status: models.PurchaseStatus,
    note: str | None = None,
    created_by_id: int | None = None,
) -> models.PurchaseOrderStatusEvent:
    event = models.PurchaseOrderStatusEvent(
        purchase_order_id=order.id,
        status=status,
        note=_normalize_optional_note(note),
        created_by_id=created_by_id,
    )
    db.add(event)
    flush_session(db)
    db.refresh(event)
    return event


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
        "requires_approval": getattr(order, "requires_approval", False),
        "approved_by_id": getattr(order, "approved_by_id", None),
        "items": items_payload,
        "documents": [
            {
                "id": document.id,
                "filename": document.filename,
                "content_type": document.content_type,
                "storage_backend": document.storage_backend,
                "uploaded_at": document.uploaded_at.isoformat(),
            }
            for document in getattr(order, "documents", [])
        ],
        "status_history": [
            {
                "id": event.id,
                "status": getattr(event.status, "value", event.status),
                "note": event.note,
                "created_at": event.created_at.isoformat(),
                "created_by_id": event.created_by_id,
            }
            for event in getattr(order, "status_events", [])
        ],
    }


def _transfer_order_payload(order: models.TransferOrder) -> dict[str, object]:
    """Serializa una orden de transferencia para la cola híbrida."""

    origin_store = getattr(order, "origin_store", None)
    destination_store = getattr(order, "destination_store", None)
    requested_by = getattr(order, "requested_by", None)
    dispatched_by = getattr(order, "dispatched_by", None)
    received_by = getattr(order, "received_by", None)
    cancelled_by = getattr(order, "cancelled_by", None)
    items_payload = []
    for item in getattr(order, "items", []) or []:
        device = getattr(item, "device", None)
        items_payload.append(
            {
                "device_id": item.device_id,
                "quantity": item.quantity,
                "dispatched_quantity": item.dispatched_quantity,
                "received_quantity": item.received_quantity,
                "dispatched_unit_cost": float(item.dispatched_unit_cost)
                if item.dispatched_unit_cost is not None
                else None,
                "sku": getattr(device, "sku", None),
                "imei": getattr(device, "imei", None),
                "serial": getattr(device, "serial", None),
            }
        )
    status_value = getattr(order.status, "value", order.status)
    return {
        "id": order.id,
        "origin_store_id": order.origin_store_id,
        "origin_store_name": getattr(origin_store, "name", None),
        "destination_store_id": order.destination_store_id,
        "destination_store_name": getattr(destination_store, "name", None),
        "status": status_value,
        "reason": order.reason,
        "requested_by_id": order.requested_by_id,
        "requested_by_name": _user_display_name(requested_by),
        "dispatched_by_id": order.dispatched_by_id,
        "dispatched_by_name": _user_display_name(dispatched_by),
        "received_by_id": order.received_by_id,
        "received_by_name": _user_display_name(received_by),
        "cancelled_by_id": order.cancelled_by_id,
        "cancelled_by_name": _user_display_name(cancelled_by),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "dispatched_at": order.dispatched_at.isoformat() if order.dispatched_at else None,
        "received_at": order.received_at.isoformat() if order.received_at else None,
        "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
        "items": items_payload,
    }


def _hydrate_movement_references(
    db: Session, movements: Sequence[models.InventoryMovement]
) -> None:
    """Asocia los metadatos de referencia a los movimientos recuperados."""

    movement_ids = [
        movement.id for movement in movements if movement.id is not None]
    if not movement_ids:
        return

    str_ids = [str(movement_id) for movement_id in movement_ids]
    statement = (
        select(models.AuditLog)
        .where(
            models.AuditLog.entity_type == "inventory_movement",
            models.AuditLog.action == "inventory_movement_reference",
            models.AuditLog.entity_id.in_(str_ids),
        )
        .order_by(models.AuditLog.created_at.desc())
    )
    logs = list(db.scalars(statement))
    reference_map: dict[str, tuple[str | None, str | None]] = {}
    for log in logs:
        if log.entity_id in reference_map:
            continue
        data: dict[str, object]
        try:
            data = json.loads(log.details or "{}")
        except json.JSONDecodeError:
            data = {}
        reference_map[log.entity_id] = (
            str(data.get("reference_type")) if data.get(
                "reference_type") else None,
            str(data.get("reference_id")) if data.get(
                "reference_id") else None,
        )

    for movement in movements:
        reference = reference_map.get(str(movement.id))
        if not reference:
            continue
        reference_type, reference_id = reference
        if reference_type:
            setattr(movement, "reference_type", reference_type)
        if reference_id:
            setattr(movement, "reference_id", reference_id)


def _repair_payload(order: models.RepairOrder) -> dict[str, object]:
    return {
        "id": order.id,
        "store_id": order.store_id,
        "status": order.status.value,
        "technician_name": order.technician_name,
        "customer_id": order.customer_id,
        "customer_name": order.customer_name,
        "customer_contact": order.customer_contact,
        "damage_type": order.damage_type,
        "diagnosis": order.diagnosis,
        "device_model": order.device_model,
        "imei": order.imei,
        "labor_cost": float(order.labor_cost),
        "parts_cost": float(order.parts_cost),
        "total_cost": float(order.total_cost),
        "updated_at": order.updated_at.isoformat(),
        "parts_snapshot": order.parts_snapshot,
    }


def _merge_defaults(default: object, provided: object) -> object:
    if isinstance(default, dict) and isinstance(provided, dict):
        merged: dict[str, object] = {key: _merge_defaults(value, provided.get(key)) for key, value in default.items()}
        for key, value in provided.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(value, (dict, list)):
                merged[key] = _merge_defaults(merged[key], value)
            elif value is not None:
                merged[key] = value
        return merged
    if isinstance(default, list) and isinstance(provided, list):
        return provided or default
    return provided if provided is not None else default


def _normalize_hardware_settings(
    raw: dict[str, object] | None,
) -> dict[str, object]:
    default_settings = schemas.POSHardwareSettings().model_dump()
    if not raw:
        return default_settings
    return _merge_defaults(default_settings, raw)


def _pos_config_payload(config: models.POSConfig) -> dict[str, object]:
    return {
        "store_id": config.store_id,
        "tax_rate": float(config.tax_rate),
        "invoice_prefix": config.invoice_prefix,
        "printer_name": config.printer_name,
        "printer_profile": config.printer_profile,
        "quick_product_ids": config.quick_product_ids,
        "promotions_config": config.promotions_config,
        "hardware_settings": config.hardware_settings,
        "updated_at": config.updated_at.isoformat(),
    }


def _build_pos_promotions_response(
    config: models.POSConfig,
) -> schemas.POSPromotionsResponse:
    normalized = promotions.load_config(config.promotions_config)
    return schemas.POSPromotionsResponse(
        store_id=config.store_id,
        feature_flags=normalized.feature_flags,
        volume_promotions=normalized.volume_promotions,
        combo_promotions=normalized.combo_promotions,
        coupons=normalized.coupons,
        updated_at=config.updated_at,
    )


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
        normalized.append({"timestamp": parsed_timestamp,
                          "note": (note or "").strip()})
    return normalized


def _contacts_to_json(
    contacts: list[schemas.SupplierContact] | list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    if not contacts:
        return normalized
    for contact in contacts:
        if isinstance(contact, schemas.SupplierContact):
            payload = contact.model_dump(exclude_none=True)
        elif isinstance(contact, Mapping):
            payload = {
                key: value
                for key, value in contact.items()
                if isinstance(key, str)
            }
        else:
            continue
        record: dict[str, object] = {}
        for key in ("name", "position", "email", "phone", "notes"):
            value = payload.get(key)
            if isinstance(value, str):
                value = value.strip()
            if value:
                record[key] = value
        if record:
            normalized.append(record)
    return normalized


def _products_to_json(products: Sequence[str] | None) -> list[str]:
    if not products:
        return []
    normalized: list[str] = []
    for product in products:
        text = (product or "").strip()
        if not text:
            continue
        if text not in normalized:
            normalized.append(text)
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


def _mask_email(value: str) -> str:
    email = (value or "").strip()
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    local = local.strip()
    domain = domain.strip() or "anon.invalid"
    if not local:
        return f"***@{domain}"
    if len(local) == 1:
        masked_local = "*"
    elif len(local) == 2:
        masked_local = f"{local[0]}*"
    else:
        masked_local = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}"
    return f"{masked_local}@{domain}"


def _mask_phone(value: str) -> str:
    digits = re.sub(r"[^0-9]", "", value or "")
    if not digits:
        return "***"
    if len(digits) <= 4:
        visible = digits[-1:] if digits else ""
        return f"{'*' * max(0, len(digits) - 1)}{visible}"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def _mask_person_name(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return text
    parts = text.split()
    masked_parts = []
    for part in parts:
        if len(part) <= 2:
            masked_parts.append(part[0] + "*")
        else:
            masked_parts.append(part[0] + "*" * (len(part) - 1))
    return " ".join(masked_parts)


def _mask_generic_text(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return text
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:2]}***{text[-2:]}"

def _apply_customer_anonymization(
    customer: models.Customer, fields: Sequence[str]
) -> list[str]:
    normalized: list[str] = []
    for raw in fields or []:
        text = str(raw or "").strip().lower()
        if text and text not in normalized:
            normalized.append(text)

    masked: list[str] = []
    for field in normalized:
        if field == "name" and customer.name:
            customer.name = _mask_person_name(customer.name)
            masked.append("name")
        elif field == "contact_name" and customer.contact_name:
            customer.contact_name = _mask_person_name(customer.contact_name)
            masked.append("contact_name")
        elif field == "email" and customer.email:
            customer.email = _mask_email(customer.email)
            masked.append("email")
        elif field == "phone" and customer.phone:
            customer.phone = _mask_phone(customer.phone)
            masked.append("phone")
        elif field == "address" and customer.address:
            customer.address = _mask_generic_text(customer.address)
            masked.append("address")
        elif field == "notes" and customer.notes:
            customer.notes = _mask_generic_text(customer.notes)
            masked.append("notes")
        elif field == "tax_id" and customer.tax_id:
            customer.tax_id = _mask_generic_text(customer.tax_id)
            masked.append("tax_id")

    if "history" in normalized and customer.history:
        history_entries = list(customer.history or [])
        customer.history = [
            {
                "timestamp": entry.get("timestamp"),
                "note": "***",
            }
            for entry in history_entries
        ]
        masked.append("history")

    return masked


_ALLOWED_CUSTOMER_STATUSES = {
    "activo", "inactivo", "moroso", "vip", "bloqueado"}
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


def _normalize_customer_segment_category(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _normalize_customer_tags(tags: Sequence[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip().lower()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


_RTN_CANONICAL_TEMPLATE = "{0}-{1}-{2}"


def _normalize_rtn(value: str | None, *, error_code: str) -> str:
    digits = re.sub(r"[^0-9]", "", value or "")
    if len(digits) != 14:
        raise ValueError(error_code)
    return _RTN_CANONICAL_TEMPLATE.format(digits[:4], digits[4:8], digits[8:])


def _generate_customer_tax_id_placeholder() -> str:
    placeholder = models.generate_customer_tax_id_placeholder()
    return _normalize_rtn(placeholder, error_code="customer_tax_id_invalid")


def _normalize_customer_tax_id(
    value: str | None, *, allow_placeholder: bool = True
) -> str:
    cleaned = (value or "").strip()
    if cleaned:
        return _normalize_rtn(cleaned, error_code="customer_tax_id_invalid")
    if allow_placeholder:
        return _generate_customer_tax_id_placeholder()
    raise ValueError("customer_tax_id_invalid")


def _is_tax_id_integrity_error(error: IntegrityError) -> bool:
    message = str(getattr(error, "orig", error)).lower()
    return "rtn" in message or "tax_id" in message or "segmento_etiquetas" in message


def _ensure_non_negative_decimal(value: Decimal, error_code: str) -> Decimal:
    normalized = _to_decimal(value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    if normalized < Decimal("0"):
        raise ValueError(error_code)
    return normalized


def _ensure_positive_decimal(value: Decimal, error_code: str) -> Decimal:
    normalized = _to_decimal(value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if normalized <= Decimal("0"):
        raise ValueError(error_code)
    return normalized


def _ensure_discount_percentage(
    value: Decimal | None, error_code: str
) -> Decimal | None:
    if value is None:
        return None
    normalized = _to_decimal(value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if normalized < Decimal("0") or normalized > Decimal("100"):
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


def _user_display_name(user: models.User | None) -> str | None:
    if user is None:
        return None
    candidates = [
        getattr(user, "full_name", None),
        getattr(user, "nombre", None),
        getattr(user, "username", None),
        getattr(user, "correo", None),
    ]
    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = candidate.strip()
            if normalized:
                return normalized
    identifier = getattr(user, "id", None)
    if identifier is None:
        identifier = getattr(user, "id_usuario", None)
    return str(identifier) if identifier is not None else None


def _supplier_ledger_payload(entry: models.SupplierLedgerEntry) -> dict[str, object]:
    return {
        "id": entry.id,
        "supplier_id": entry.supplier_id,
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
        amount=_to_decimal(amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP),
        balance_after=_to_decimal(customer.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        note=note,
        details=details or {},
        created_by_id=created_by_id,
    )
    db.add(entry)
    flush_session(db)
    return entry


def _create_supplier_ledger_entry(
    db: Session,
    *,
    supplier: models.Supplier,
    entry_type: models.SupplierLedgerEntryType,
    amount: Decimal,
    note: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    details: dict[str, object] | None = None,
    created_by_id: int | None = None,
) -> models.SupplierLedgerEntry:
    entry = models.SupplierLedgerEntry(
        supplier_id=supplier.id,
        entry_type=entry_type,
        reference_type=reference_type,
        reference_id=reference_id,
        amount=_to_decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        balance_after=_to_decimal(supplier.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        note=note,
        details=details or {},
        created_by_id=created_by_id,
    )
    db.add(entry)
    flush_session(db)
    return entry


def _store_credit_payload(credit: models.StoreCredit) -> dict[str, object]:
    return {
        "id": credit.id,
        "customer_id": credit.customer_id,
        "code": credit.code,
        "issued_amount": float(_to_decimal(credit.issued_amount)),
        "balance_amount": float(_to_decimal(credit.balance_amount)),
        "status": credit.status.value,
        "issued_at": credit.issued_at.isoformat(),
        "redeemed_at": credit.redeemed_at.isoformat() if credit.redeemed_at else None,
        "expires_at": credit.expires_at.isoformat() if credit.expires_at else None,
        "context": credit.context or {},
    }


def _store_credit_redemption_payload(
    redemption: models.StoreCreditRedemption,
) -> dict[str, object]:
    return {
        "id": redemption.id,
        "store_credit_id": redemption.store_credit_id,
        "sale_id": redemption.sale_id,
        "amount": float(_to_decimal(redemption.amount)),
        "notes": redemption.notes,
        "created_at": redemption.created_at.isoformat(),
        "created_by_id": redemption.created_by_id,
    }


def _loyalty_account_payload(account: models.LoyaltyAccount) -> dict[str, object]:
    return {
        "id": account.id,
        "customer_id": account.customer_id,
        "accrual_rate": float(_to_decimal(account.accrual_rate)),
        "redemption_rate": float(_to_decimal(account.redemption_rate)),
        "expiration_days": account.expiration_days,
        "is_active": account.is_active,
        "rule_config": account.rule_config or {},
        "balance_points": float(_to_decimal(account.balance_points)),
        "lifetime_points_earned": float(_to_decimal(account.lifetime_points_earned)),
        "lifetime_points_redeemed": float(_to_decimal(account.lifetime_points_redeemed)),
        "expired_points_total": float(_to_decimal(account.expired_points_total)),
        "last_accrual_at": account.last_accrual_at.isoformat() if account.last_accrual_at else None,
        "last_redemption_at": account.last_redemption_at.isoformat() if account.last_redemption_at else None,
        "last_expiration_at": account.last_expiration_at.isoformat() if account.last_expiration_at else None,
        "created_at": account.created_at.isoformat(),
        "updated_at": account.updated_at.isoformat(),
    }


def _loyalty_transaction_payload(
    transaction: models.LoyaltyTransaction,
) -> dict[str, object]:
    return {
        "id": transaction.id,
        "account_id": transaction.account_id,
        "sale_id": transaction.sale_id,
        "transaction_type": transaction.transaction_type.value,
        "points": float(_to_decimal(transaction.points)),
        "balance_after": float(_to_decimal(transaction.balance_after)),
        "currency_amount": float(_to_decimal(transaction.currency_amount)),
        "description": transaction.description,
        "details": transaction.details or {},
        "registered_at": transaction.registered_at.isoformat(),
        "expires_at": transaction.expires_at.isoformat() if transaction.expires_at else None,
        "registered_by_id": transaction.registered_by_id,
    }


def _generate_store_credit_code(db: Session) -> str:
    for _ in range(10):
        candidate = f"NC-{uuid4().hex[:10].upper()}"
        exists = db.scalar(
            select(models.StoreCredit.id).where(models.StoreCredit.code == candidate)
        )
        if not exists:
            return candidate
    raise RuntimeError("store_credit_code_generation_failed")


def list_store_credits(db: Session, *, customer_id: int) -> list[models.StoreCredit]:
    statement = (
        select(models.StoreCredit)
        .options(
            selectinload(models.StoreCredit.redemptions).joinedload(
                models.StoreCreditRedemption.created_by
            )
        )
        .where(models.StoreCredit.customer_id == customer_id)
        .order_by(models.StoreCredit.issued_at.desc(), models.StoreCredit.id.desc())
    )
    return list(db.scalars(statement))


def _apply_store_credit_redemption(
    db: Session,
    *,
    credit: models.StoreCredit,
    amount: Decimal,
    sale_id: int | None,
    notes: str | None,
    performed_by_id: int | None,
) -> models.StoreCreditRedemption:
    amount_value = _ensure_positive_decimal(amount, "store_credit_invalid_amount")
    current_balance = _to_decimal(credit.balance_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if amount_value > current_balance:
        raise ValueError("store_credit_insufficient_balance")

    new_balance = (current_balance - amount_value).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    credit.balance_amount = new_balance
    if new_balance == Decimal("0"):
        credit.status = models.StoreCreditStatus.REDIMIDO
        credit.redeemed_at = datetime.utcnow()
    else:
        credit.status = models.StoreCreditStatus.PARCIAL

    redemption = models.StoreCreditRedemption(
        store_credit_id=credit.id,
        sale_id=sale_id,
        amount=amount_value,
        notes=notes,
        created_by_id=performed_by_id,
    )
    db.add(redemption)

    customer = credit.customer
    message = (
        f"Aplicación de nota de crédito {credit.code} por ${_format_currency(amount_value)}"
    )
    _append_customer_history(customer, message)
    details = {
        "amount_applied": float(amount_value),
        "balance_after": float(new_balance),
        "code": credit.code,
        "sale_id": sale_id,
    }
    _create_customer_ledger_entry(
        db,
        customer=customer,
        entry_type=models.CustomerLedgerEntryType.STORE_CREDIT_REDEEMED,
        amount=Decimal("0"),
        note=notes,
        reference_type="store_credit",
        reference_id=str(credit.id),
        details=details,
        created_by_id=performed_by_id,
    )
    return redemption


def issue_store_credit(
    db: Session,
    payload: schemas.StoreCreditIssueRequest,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.StoreCredit:
    customer = get_customer(db, payload.customer_id)
    amount = _ensure_positive_decimal(payload.amount, "store_credit_invalid_amount")
    code = (payload.code or "").strip().upper()
    if code:
        existing = db.scalar(select(models.StoreCredit.id).where(models.StoreCredit.code == code))
        if existing:
            raise ValueError("store_credit_code_in_use")
    else:
        code = _generate_store_credit_code(db)

    credit = models.StoreCredit(
        code=code,
        customer_id=customer.id,
        issued_amount=amount,
        balance_amount=amount,
        status=models.StoreCreditStatus.ACTIVO,
        notes=payload.notes,
        context=payload.context or {},
        expires_at=payload.expires_at,
        issued_by_id=performed_by_id,
    )

    with transactional_session(db):
        db.add(credit)
        flush_session(db)
        db.refresh(credit)

        history_message = (
            f"Nota de crédito {credit.code} emitida por ${_format_currency(amount)}"
        )
        _append_customer_history(customer, history_message)
        db.add(customer)

        details = {
            "code": credit.code,
            "amount": float(amount),
            "expires_at": credit.expires_at.isoformat() if credit.expires_at else None,
        }
        _create_customer_ledger_entry(
            db,
            customer=customer,
            entry_type=models.CustomerLedgerEntryType.STORE_CREDIT_ISSUED,
            amount=Decimal("0"),
            note=payload.notes,
            reference_type="store_credit",
            reference_id=str(credit.id),
            details=details,
            created_by_id=performed_by_id,
        )

        _log_action(
            db,
            action="store_credit_issued",
            entity_type="store_credit",
            entity_id=str(credit.id),
            performed_by_id=performed_by_id,
            details=json.dumps({
                "customer_id": customer.id,
                "amount": float(amount),
                "code": credit.code,
                "reason": reason,
            }),
        )

        flush_session(db)
        db.refresh(customer)
        db.refresh(credit)

        enqueue_sync_outbox(
            db,
            entity_type="store_credit",
            entity_id=str(credit.id),
            operation="UPSERT",
            payload=_store_credit_payload(credit),
        )
        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer.id),
            operation="UPSERT",
            payload=_customer_payload(customer),
        )

    return credit


def redeem_store_credit(
    db: Session,
    payload: schemas.StoreCreditRedeemRequest,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> tuple[models.StoreCredit, models.StoreCreditRedemption]:
    if payload.store_credit_id is None and not payload.code:
        raise ValueError("store_credit_reference_required")

    statement = (
        select(models.StoreCredit)
        .options(
            joinedload(models.StoreCredit.customer),
            selectinload(models.StoreCredit.redemptions).joinedload(
                models.StoreCreditRedemption.created_by
            ),
        )
    )
    if payload.store_credit_id is not None:
        statement = statement.where(models.StoreCredit.id == payload.store_credit_id)
    else:
        statement = statement.where(models.StoreCredit.code == payload.code.strip().upper())

    credit = db.scalars(statement).unique().first()
    if credit is None:
        raise LookupError("store_credit_not_found")
    if credit.status == models.StoreCreditStatus.CANCELADO:
        raise ValueError("store_credit_cancelled")
    if credit.expires_at and credit.expires_at <= datetime.utcnow():
        raise ValueError("store_credit_expired")

    with transactional_session(db):
        redemption = _apply_store_credit_redemption(
            db,
            credit=credit,
            amount=payload.amount,
            sale_id=payload.sale_id,
            notes=payload.notes,
            performed_by_id=performed_by_id,
        )
        db.add(credit)
        flush_session(db)
        db.refresh(credit)
        db.refresh(redemption)

        _log_action(
            db,
            action="store_credit_redeemed",
            entity_type="store_credit",
            entity_id=str(credit.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "amount": float(_to_decimal(payload.amount)),
                    "sale_id": payload.sale_id,
                    "reason": reason,
                }
            ),
        )

        enqueue_sync_outbox(
            db,
            entity_type="store_credit",
            entity_id=str(credit.id),
            operation="UPSERT",
            payload=_store_credit_payload(credit),
        )
        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(credit.customer_id),
            operation="UPSERT",
            payload=_customer_payload(credit.customer),
        )
        enqueue_sync_outbox(
            db,
            entity_type="store_credit_redemption",
            entity_id=str(redemption.id),
            operation="UPSERT",
            payload=_store_credit_redemption_payload(redemption),
        )

    return credit, redemption


def redeem_store_credit_for_customer(
    db: Session,
    *,
    customer_id: int,
    amount: Decimal,
    sale_id: int | None,
    notes: str | None,
    performed_by_id: int | None,
    reason: str | None = None,
) -> list[models.StoreCreditRedemption]:
    total_requested = _ensure_positive_decimal(amount, "store_credit_invalid_amount")
    statement = (
        select(models.StoreCredit)
        .options(
            joinedload(models.StoreCredit.customer),
            selectinload(models.StoreCredit.redemptions).joinedload(
                models.StoreCreditRedemption.created_by
            ),
        )
        .where(
            models.StoreCredit.customer_id == customer_id,
            models.StoreCredit.status.in_(
                [models.StoreCreditStatus.ACTIVO, models.StoreCreditStatus.PARCIAL]
            ),
        )
        .order_by(models.StoreCredit.issued_at.asc(), models.StoreCredit.id.asc())
    )
    credits = list(db.scalars(statement).unique())
    if not credits:
        raise LookupError("store_credit_not_found")

    available_total = sum(
        _to_decimal(credit.balance_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for credit in credits
    )
    if available_total < total_requested:
        raise ValueError("store_credit_insufficient_balance")

    remaining = total_requested
    applied_redemptions: list[models.StoreCreditRedemption] = []
    affected_credit_ids: set[int] = set()
    customer = credits[0].customer

    with transactional_session(db):
        for credit in credits:
            if remaining <= Decimal("0"):
                break
            available = _to_decimal(credit.balance_amount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if available <= Decimal("0"):
                continue
            chunk = min(available, remaining)
            redemption = _apply_store_credit_redemption(
                db,
                credit=credit,
                amount=chunk,
                sale_id=sale_id,
                notes=notes,
                performed_by_id=performed_by_id,
            )
            db.add(credit)
            flush_session(db)
            db.refresh(credit)
            db.refresh(redemption)
            applied_redemptions.append(redemption)
            affected_credit_ids.add(credit.id)
            remaining -= chunk

        if remaining > Decimal("0"):
            raise ValueError("store_credit_insufficient_balance")

        flush_session(db)
        db.refresh(customer)

        total_applied = float(_to_decimal(total_requested))
        _log_action(
            db,
            action="store_credit_batch_redeemed",
            entity_type="customer",
            entity_id=str(customer.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "amount": total_applied,
                    "sale_id": sale_id,
                    "reason": reason,
                    "credits": sorted(affected_credit_ids),
                }
            ),
        )

        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer.id),
            operation="UPSERT",
            payload=_customer_payload(customer),
        )
        for credit in credits:
            if credit.id in affected_credit_ids:
                enqueue_sync_outbox(
                    db,
                    entity_type="store_credit",
                    entity_id=str(credit.id),
                    operation="UPSERT",
                    payload=_store_credit_payload(credit),
                )
        for redemption in applied_redemptions:
            enqueue_sync_outbox(
                db,
                entity_type="store_credit_redemption",
                entity_id=str(redemption.id),
                operation="UPSERT",
                payload=_store_credit_redemption_payload(redemption),
            )

    return applied_redemptions


def get_loyalty_account(
    db: Session,
    customer_id: int,
    *,
    with_transactions: bool = False,
) -> models.LoyaltyAccount | None:
    statement = select(models.LoyaltyAccount).where(
        models.LoyaltyAccount.customer_id == customer_id
    )
    if with_transactions:
        statement = statement.options(
            selectinload(models.LoyaltyAccount.transactions)
        )
    return db.scalars(statement).first()


def get_loyalty_account_by_id(
    db: Session,
    account_id: int,
    *,
    with_transactions: bool = False,
) -> models.LoyaltyAccount | None:
    statement = select(models.LoyaltyAccount).where(
        models.LoyaltyAccount.id == account_id
    )
    if with_transactions:
        statement = statement.options(
            selectinload(models.LoyaltyAccount.transactions)
        )
    return db.scalars(statement).first()


def ensure_loyalty_account(
    db: Session,
    customer_id: int,
    *,
    defaults: dict[str, Any] | None = None,
) -> models.LoyaltyAccount:
    account = get_loyalty_account(db, customer_id, with_transactions=False)
    if account is not None:
        return account

    defaults = defaults or {}
    accrual_rate = _quantize_rate(
        _to_decimal(defaults.get("accrual_rate", Decimal("1")))
    )
    redemption_rate = _quantize_rate(
        _to_decimal(defaults.get("redemption_rate", Decimal("1")))
    )
    if redemption_rate <= Decimal("0"):
        redemption_rate = Decimal("1.0000")
    expiration_days = int(defaults.get("expiration_days", 365) or 0)
    is_active = bool(defaults.get("is_active", True))
    rule_config = (
        defaults.get("rule_config")
        if isinstance(defaults.get("rule_config"), dict)
        else {}
    )

    with transactional_session(db):
        account = models.LoyaltyAccount(
            customer_id=customer_id,
            accrual_rate=accrual_rate,
            redemption_rate=redemption_rate,
            expiration_days=max(0, expiration_days),
            is_active=is_active,
            rule_config=rule_config,
        )
        db.add(account)
        flush_session(db)
        db.refresh(account)
        enqueue_sync_outbox(
            db,
            entity_type="loyalty_account",
            entity_id=str(account.id),
            operation="UPSERT",
            payload=_loyalty_account_payload(account),
        )
    return account


def update_loyalty_account(
    db: Session,
    customer_id: int,
    payload: schemas.LoyaltyAccountUpdate,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.LoyaltyAccount:
    account = ensure_loyalty_account(db, customer_id)

    with transactional_session(db):
        if payload.accrual_rate is not None:
            account.accrual_rate = _quantize_rate(
                _to_decimal(payload.accrual_rate)
            )
        if payload.redemption_rate is not None:
            normalized_rate = _quantize_rate(
                _to_decimal(payload.redemption_rate)
            )
            if normalized_rate <= Decimal("0"):
                raise ValueError("loyalty_redemption_rate_invalid")
            account.redemption_rate = normalized_rate
        if payload.expiration_days is not None:
            account.expiration_days = max(0, int(payload.expiration_days))
        if payload.is_active is not None:
            account.is_active = bool(payload.is_active)
        if payload.rule_config is not None:
            account.rule_config = payload.rule_config
        db.add(account)
        flush_session(db)
        db.refresh(account)

        _log_action(
            db,
            action="loyalty_account_updated",
            entity_type="customer",
            entity_id=str(customer_id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "accrual_rate": float(_to_decimal(account.accrual_rate)),
                    "redemption_rate": float(
                        _to_decimal(account.redemption_rate)
                    ),
                    "expiration_days": account.expiration_days,
                    "reason": reason,
                }
            ),
        )

        enqueue_sync_outbox(
            db,
            entity_type="loyalty_account",
            entity_id=str(account.id),
            operation="UPSERT",
            payload=_loyalty_account_payload(account),
        )

    return account


def _expire_loyalty_account_if_needed(
    db: Session,
    account: models.LoyaltyAccount,
    *,
    reference_date: datetime,
    performed_by_id: int | None = None,
) -> models.LoyaltyTransaction | None:
    expiration_days = int(account.expiration_days or 0)
    if expiration_days <= 0:
        return None

    last_activity = account.last_redemption_at or account.last_accrual_at
    if last_activity is None:
        last_activity = account.created_at
    if last_activity is None:
        last_activity = reference_date

    deadline = last_activity + timedelta(days=expiration_days)
    if reference_date <= deadline:
        return None

    current_balance = _quantize_points(_to_decimal(account.balance_points))
    if current_balance <= Decimal("0"):
        account.last_expiration_at = reference_date
        db.add(account)
        return None

    expiration_tx = models.LoyaltyTransaction(
        account_id=account.id,
        transaction_type=models.LoyaltyTransactionType.EXPIRATION,
        points=-current_balance,
        balance_after=Decimal("0"),
        currency_amount=Decimal("0"),
        description="Expiración automática de puntos",
        details={"trigger": "auto_expiration"},
        registered_at=reference_date,
        registered_by_id=performed_by_id,
    )
    account.balance_points = Decimal("0")
    account.expired_points_total = _quantize_points(
        _to_decimal(account.expired_points_total) + current_balance
    )
    account.last_expiration_at = reference_date
    db.add(expiration_tx)
    db.add(account)
    flush_session(db)
    return expiration_tx


def _record_loyalty_transaction(
    db: Session,
    *,
    account: models.LoyaltyAccount,
    sale_id: int | None,
    transaction_type: models.LoyaltyTransactionType,
    points: Decimal,
    balance_after: Decimal,
    currency_amount: Decimal,
    description: str,
    performed_by_id: int | None,
    expires_at: datetime | None = None,
    details: dict[str, Any] | None = None,
) -> models.LoyaltyTransaction:
    transaction = models.LoyaltyTransaction(
        account_id=account.id,
        sale_id=sale_id,
        transaction_type=transaction_type,
        points=_quantize_points(points),
        balance_after=_quantize_points(balance_after),
        currency_amount=_quantize_currency(currency_amount),
        description=description,
        details=details or {},
        registered_at=datetime.utcnow(),
        registered_by_id=performed_by_id,
        expires_at=expires_at,
    )
    db.add(transaction)
    flush_session(db)
    db.refresh(transaction)
    enqueue_sync_outbox(
        db,
        entity_type="loyalty_transaction",
        entity_id=str(transaction.id),
        operation="UPSERT",
        payload=_loyalty_transaction_payload(transaction),
    )
    return transaction


def apply_loyalty_for_sale(
    db: Session,
    sale: models.Sale,
    *,
    points_payment_amount: Decimal,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> schemas.POSLoyaltySaleSummary | None:
    amount_currency = _quantize_currency(_to_decimal(points_payment_amount))
    if sale.customer_id is None:
        if amount_currency > Decimal("0"):
            raise ValueError("loyalty_requires_customer")
        return None

    account = ensure_loyalty_account(db, sale.customer_id)
    now = sale.created_at or datetime.utcnow()

    expiration_tx = _expire_loyalty_account_if_needed(
        db,
        account,
        reference_date=now,
        performed_by_id=performed_by_id,
    )

    redeemed_points = Decimal("0")
    if amount_currency > Decimal("0"):
        redemption_rate = _to_decimal(account.redemption_rate)
        if redemption_rate <= Decimal("0"):
            raise ValueError("loyalty_redemption_disabled")
        required_points = _quantize_points(amount_currency / redemption_rate)
        if required_points <= Decimal("0"):
            raise ValueError("loyalty_invalid_redeem_amount")
        available = _quantize_points(_to_decimal(account.balance_points))
        if required_points > available:
            raise ValueError("loyalty_insufficient_points")
        account.balance_points = _quantize_points(available - required_points)
        account.lifetime_points_redeemed = _quantize_points(
            _to_decimal(account.lifetime_points_redeemed) + required_points
        )
        account.last_redemption_at = now
        redeemed_points = required_points
        sale.loyalty_points_redeemed = redeemed_points
        _record_loyalty_transaction(
            db,
            account=account,
            sale_id=sale.id,
            transaction_type=models.LoyaltyTransactionType.REDEEM,
            points=-redeemed_points,
            balance_after=account.balance_points,
            currency_amount=amount_currency,
            description=f"Canje aplicado a la venta #{sale.id}",
            performed_by_id=performed_by_id,
            details={"reason": reason or "redeem"},
        )

    earned_points = Decimal("0")
    if account.is_active:
        accrual_rate = _to_decimal(account.accrual_rate)
        if accrual_rate > Decimal("0"):
            earned_points = _quantize_points(
                _to_decimal(sale.total_amount) * accrual_rate
            )
    if earned_points > Decimal("0"):
        account.balance_points = _quantize_points(
            _to_decimal(account.balance_points) + earned_points
        )
        account.lifetime_points_earned = _quantize_points(
            _to_decimal(account.lifetime_points_earned) + earned_points
        )
        account.last_accrual_at = now
        sale.loyalty_points_earned = earned_points
        expires_at = None
        if account.expiration_days > 0:
            expires_at = now + timedelta(days=account.expiration_days)
        _record_loyalty_transaction(
            db,
            account=account,
            sale_id=sale.id,
            transaction_type=models.LoyaltyTransactionType.EARN,
            points=earned_points,
            balance_after=account.balance_points,
            currency_amount=_to_decimal(sale.total_amount),
            description=f"Puntos acumulados en venta #{sale.id}",
            performed_by_id=performed_by_id,
            expires_at=expires_at,
            details={"reason": reason or "earn"},
        )

    db.add(account)
    db.add(sale)
    flush_session(db)
    db.refresh(account)
    enqueue_sync_outbox(
        db,
        entity_type="loyalty_account",
        entity_id=str(account.id),
        operation="UPSERT",
        payload=_loyalty_account_payload(account),
    )

    summary = schemas.POSLoyaltySaleSummary(
        account_id=account.id,
        earned_points=earned_points,
        redeemed_points=redeemed_points,
        balance_points=_quantize_points(_to_decimal(account.balance_points)),
        redemption_amount=amount_currency,
        expiration_days=account.expiration_days if account.expiration_days > 0 else None,
        expires_at=(
            (now + timedelta(days=account.expiration_days))
            if account.expiration_days > 0
            else None
        ),
    )

    if expiration_tx is not None:
        enqueue_sync_outbox(
            db,
            entity_type="loyalty_transaction",
            entity_id=str(expiration_tx.id),
            operation="UPSERT",
            payload=_loyalty_transaction_payload(expiration_tx),
        )

    return summary


def list_loyalty_accounts(
    db: Session,
    *,
    is_active: bool | None = None,
    customer_id: int | None = None,
) -> list[models.LoyaltyAccount]:
    statement = select(models.LoyaltyAccount).options(
        joinedload(models.LoyaltyAccount.customer)
    ).order_by(models.LoyaltyAccount.created_at.desc())
    if is_active is not None:
        statement = statement.where(
            models.LoyaltyAccount.is_active.is_(is_active)
        )
    if customer_id is not None:
        statement = statement.where(
            models.LoyaltyAccount.customer_id == customer_id
        )
    return list(db.scalars(statement))


def list_loyalty_transactions(
    db: Session,
    *,
    account_id: int | None = None,
    customer_id: int | None = None,
    sale_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[models.LoyaltyTransaction]:
    statement = select(models.LoyaltyTransaction).options(
        joinedload(models.LoyaltyTransaction.account)
        .joinedload(models.LoyaltyAccount.customer)
    ).order_by(models.LoyaltyTransaction.registered_at.desc())
    if account_id is not None:
        statement = statement.where(
            models.LoyaltyTransaction.account_id == account_id
        )
    if customer_id is not None:
        statement = statement.join(models.LoyaltyAccount).where(
            models.LoyaltyAccount.customer_id == customer_id
        )
    if sale_id is not None:
        statement = statement.where(models.LoyaltyTransaction.sale_id == sale_id)
    if offset:
        statement = statement.offset(max(0, offset))
    if limit:
        statement = statement.limit(max(1, min(limit, 500)))
    return list(db.scalars(statement))


def get_loyalty_summary(db: Session) -> schemas.LoyaltyReportSummary:
    total_accounts = int(
        db.scalar(select(func.count()).select_from(models.LoyaltyAccount)) or 0
    )
    active_accounts = int(
        db.scalar(
            select(func.count()).where(models.LoyaltyAccount.is_active.is_(True))
        )
        or 0
    )
    inactive_accounts = total_accounts - active_accounts
    totals = db.execute(
        select(
            func.coalesce(func.sum(models.LoyaltyAccount.balance_points), 0),
            func.coalesce(func.sum(models.LoyaltyAccount.lifetime_points_earned), 0),
            func.coalesce(func.sum(models.LoyaltyAccount.lifetime_points_redeemed), 0),
            func.coalesce(func.sum(models.LoyaltyAccount.expired_points_total), 0),
        )
    ).one()
    balance_sum = _quantize_points(_to_decimal(totals[0]))
    earned_sum = _quantize_points(_to_decimal(totals[1]))
    redeemed_sum = _quantize_points(_to_decimal(totals[2]))
    expired_sum = _quantize_points(_to_decimal(totals[3]))

    last_activity = db.scalar(
        select(models.LoyaltyTransaction.registered_at)
        .order_by(models.LoyaltyTransaction.registered_at.desc())
        .limit(1)
    )

    return schemas.LoyaltyReportSummary(
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        inactive_accounts=inactive_accounts,
        total_balance=balance_sum,
        total_earned=earned_sum,
        total_redeemed=redeemed_sum,
        total_expired=expired_sum,
        last_activity=last_activity,
    )


def get_last_audit_entries(
    db: Session,
    *,
    entity_type: str,
    entity_ids: Iterable[int | str],
) -> dict[str, models.AuditLog]:
    normalized_ids = [str(entity_id)
                      for entity_id in entity_ids if str(entity_id)]
    if not normalized_ids:
        return {}

    statement = (
        select(models.AuditLog)
        .options(joinedload(models.AuditLog.performed_by))
        .where(models.AuditLog.entity_type == entity_type)
        .where(models.AuditLog.entity_id.in_(normalized_ids))
        .order_by(models.AuditLog.entity_id.asc(), models.AuditLog.created_at.desc())
    )

    logs = list(db.scalars(statement).unique())
    latest: dict[str, models.AuditLog] = {}
    for log in logs:
        if log.entity_id not in latest:
            latest[log.entity_id] = log
    return latest


def _attach_last_audit_trails(
    db: Session,
    *,
    entity_type: str,
    records: Iterable[object],
) -> None:
    """Enriquece los registros indicados con la última acción de auditoría."""

    record_list = list(records)
    if not record_list:
        return

    record_ids = [
        getattr(record, "id", None)
        for record in record_list
        if getattr(record, "id", None) is not None
    ]

    audit_trails: dict[str, schemas.AuditTrailInfo] = {}
    if record_ids:
        audit_logs = get_last_audit_entries(
            db,
            entity_type=entity_type,
            entity_ids=record_ids,
        )
        audit_trails = {
            key: audit_trail_utils.to_audit_trail(log)
            for key, log in audit_logs.items()
        }

    for record in record_list:
        record_id = getattr(record, "id", None)
        audit_entry = (
            audit_trails.get(str(record_id)) if record_id is not None else None
        )
        setattr(record, "ultima_accion", audit_entry)


def _sync_customer_ledger_entry(db: Session, entry: models.CustomerLedgerEntry) -> None:
    with transactional_session(db):
        db.refresh(entry)
        db.refresh(entry, attribute_names=["created_by"])
        enqueue_sync_outbox(
            db,
            entity_type="customer_ledger_entry",
            entity_id=str(entry.id),
            operation="UPSERT",
            payload=_customer_ledger_payload(entry),
        )


def _sync_supplier_ledger_entry(db: Session, entry: models.SupplierLedgerEntry) -> None:
    with transactional_session(db):
        db.refresh(entry)
        db.refresh(entry, attribute_names=["created_by"])
        enqueue_sync_outbox(
            db,
            entity_type="supplier_ledger_entry",
            entity_id=str(entry.id),
            operation="UPSERT",
            payload=_supplier_ledger_payload(entry),
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
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    entity_type: str | None = None,
    module: str | None = None,
    performed_by_id: int | None = None,
    severity: audit_utils.AuditSeverity | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
) -> list[models.AuditLog]:
    critical_keywords = audit_utils.severity_keywords()["critical"]
    warning_keywords = audit_utils.severity_keywords()["warning"]

    def _keyword_condition(keyword: str):
        pattern = f"%{keyword}%"
        return or_(
            models.AuditLog.action.ilike(pattern),
            func.coalesce(models.AuditLog.details, "").ilike(pattern),
        )

    statement = select(models.AuditLog).order_by(models.AuditLog.created_at.desc())
    if module:
        statement = statement.join(
            models.SystemLog,
            models.SystemLog.audit_log_id == models.AuditLog.id,
        ).where(models.SystemLog.modulo == module.strip().lower())
    else:
        statement = statement.outerjoin(models.SystemLog)
    if action:
        statement = statement.where(models.AuditLog.action == action)
    if entity_type:
        statement = statement.where(models.AuditLog.entity_type == entity_type)
    if performed_by_id is not None:
        statement = statement.where(
            models.AuditLog.performed_by_id == performed_by_id)
    if severity:
        critical_conditions = [_keyword_condition(keyword)
                                for keyword in critical_keywords]
        warning_conditions = [_keyword_condition(keyword)
                                for keyword in warning_keywords]
        critical_condition = or_(*critical_conditions)
        warning_condition = or_(*warning_conditions)
        if severity == "critical":
            statement = statement.where(critical_condition)
        elif severity == "warning":
            statement = statement.where(warning_condition, ~critical_condition)
        elif severity == "info":
            statement = statement.where(~critical_condition, ~warning_condition)
    if date_from is not None or date_to is not None:
        start_dt, end_dt = _normalize_date_range(date_from, date_to)
        statement = statement.where(
            models.AuditLog.created_at >= start_dt, models.AuditLog.created_at <= end_dt
        )
    statement = statement.offset(offset).limit(limit)
    return list(db.scalars(statement).unique())


def count_audit_logs(
    db: Session,
    *,
    action: str | None = None,
    entity_type: str | None = None,
    module: str | None = None,
    performed_by_id: int | None = None,
    severity: audit_utils.AuditSeverity | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
) -> int:
    critical_keywords = audit_utils.severity_keywords()["critical"]
    warning_keywords = audit_utils.severity_keywords()["warning"]

    def _keyword_condition(keyword: str):
        pattern = f"%{keyword}%"
        return or_(
            models.AuditLog.action.ilike(pattern),
            func.coalesce(models.AuditLog.details, "").ilike(pattern),
        )

    statement = select(func.count()).select_from(models.AuditLog)
    if module:
        statement = statement.join(
            models.SystemLog,
            models.SystemLog.audit_log_id == models.AuditLog.id,
        ).where(models.SystemLog.modulo == module.strip().lower())
    else:
        statement = statement.outerjoin(models.SystemLog)
    if action:
        statement = statement.where(models.AuditLog.action == action)
    if entity_type:
        statement = statement.where(models.AuditLog.entity_type == entity_type)
    if performed_by_id is not None:
        statement = statement.where(
            models.AuditLog.performed_by_id == performed_by_id)
    if severity:
        critical_conditions = [_keyword_condition(keyword)
                                for keyword in critical_keywords]
        warning_conditions = [_keyword_condition(keyword)
                                for keyword in warning_keywords]
        critical_condition = or_(*critical_conditions)
        warning_condition = or_(*warning_conditions)
        if severity == "critical":
            statement = statement.where(critical_condition)
        elif severity == "warning":
            statement = statement.where(warning_condition, ~critical_condition)
        elif severity == "info":
            statement = statement.where(~critical_condition, ~warning_condition)
    if date_from is not None or date_to is not None:
        start_dt, end_dt = _normalize_date_range(date_from, date_to)
        statement = statement.where(
            models.AuditLog.created_at >= start_dt,
            models.AuditLog.created_at <= end_dt,
        )
    return int(db.scalar(statement) or 0)


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
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    entity_type: str | None = None,
    module: str | None = None,
    performed_by_id: int | None = None,
    severity: audit_utils.AuditSeverity | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
) -> str:
    logs = list_audit_logs(
        db,
        limit=limit,
        offset=offset,
        action=action,
        entity_type=entity_type,
        module=module,
        performed_by_id=performed_by_id,
        severity=severity,
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
            acknowledgement_text = acknowledgement.acknowledged_at.strftime(
                "%Y-%m-%dT%H:%M:%S")
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
        severity = audit_utils.classify_severity(
            item.action or "", item.details)
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
    with transactional_session(db):
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

        flush_session(db)
        db.refresh(acknowledgement)

    invalidate_persistent_audit_alerts_cache()
    telemetry.record_audit_acknowledgement(normalized_type, event)
    return acknowledgement


def get_persistent_audit_alerts(
    db: Session,
    *,
    threshold_minutes: int = 15,
    min_occurrences: int = 1,
    lookback_hours: int = 48,
    limit: int = 50,
    offset: int = 0,
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
    if offset < 0:
        raise ValueError("offset must be >= 0")

    fetch_limit = limit + offset

    cache_key = _persistent_alerts_cache_key(
        threshold_minutes=threshold_minutes,
        min_occurrences=min_occurrences,
        lookback_hours=lookback_hours,
        limit=fetch_limit,
    )
    cached = _PERSISTENT_ALERTS_CACHE.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)[offset: offset + limit]

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
        limit=fetch_limit,
        reference_time=now,
    )

    keys = {(alert["entity_type"], alert["entity_id"])
            for alert in persistent_alerts}
    acknowledgements: dict[tuple[str, str],
                           models.AuditAlertAcknowledgement] = {}
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
    return enriched[offset: offset + limit]


def ensure_role_permissions(db: Session, role_name: str) -> None:
    defaults = ROLE_MODULE_PERMISSION_MATRIX.get(role_name)
    if not defaults:
        return
    with transactional_session(db):
        for module, flags in defaults.items():
            statement = (
                select(models.Permission)
                .where(models.Permission.role_name == role_name)
                .where(models.Permission.module == module)
            )
            permission = db.scalars(statement).first()
            if permission is None:
                permission = models.Permission(
                    role_name=role_name, module=module)
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
                    permission.can_delete = bool(
                        flags.get("can_delete", False))
        flush_session(db)


def ensure_role(db: Session, name: str) -> models.Role:
    statement = select(models.Role).where(models.Role.name == name)
    role = db.scalars(statement).first()
    if role is None:
        role = models.Role(name=name)
        db.add(role)
        flush_session(db)
    ensure_role_permissions(db, name)
    return role


def list_roles(
    db: Session, *, limit: int = 50, offset: int = 0
) -> list[models.Role]:
    statement = (
        select(models.Role)
        .order_by(models.Role.name.asc())
        .offset(offset)
        .limit(limit)
    )
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


def _normalize_role_names(role_names: Iterable[str]) -> list[str]:
    """Normaliza la colección de roles removiendo duplicados y espacios."""

    unique_roles: list[str] = []
    seen: set[str] = set()
    for role_name in role_names:
        if not isinstance(role_name, str):
            continue
        normalized = role_name.strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_roles.append(normalized)
    return unique_roles


def _build_role_assignments(
    db: Session, role_names: Iterable[str]
) -> list[models.UserRole]:
    """Crea las asociaciones de roles a partir de los nombres únicos provistos."""

    assignments: list[models.UserRole] = []
    for role_name in role_names:
        role = ensure_role(db, role_name)
        role_id = role.id
        if role_id is None:
            flush_session(db)
            role_id = role.id
        assignments.append(models.UserRole(role_id=role_id))
    return assignments


def create_user(
    db: Session,
    payload: schemas.UserCreate,
    *,
    password_hash: str,
    role_names: Iterable[str],
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.User:
    normalized_roles = _normalize_role_names(role_names)
    primary_role = _select_primary_role(normalized_roles)
    if primary_role not in normalized_roles:
        normalized_roles.append(primary_role)
    store_id: int | None = None
    if payload.store_id is not None:
        try:
            store = get_store(db, payload.store_id)
        except LookupError as exc:
            raise ValueError("store_not_found") from exc
        store_id = store.id
    user = models.User(
        username=payload.username,
        full_name=payload.full_name,
        telefono=payload.telefono,
        rol=primary_role,
        estado="ACTIVO",
        password_hash=password_hash,
        store_id=store_id,
    )
    with transactional_session(db):
        db.add(user)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("user_already_exists") from exc

        assignments = _build_role_assignments(db, normalized_roles)
        user.roles.extend(assignments)

        log_details: dict[str, object] = {
            "description": f"Usuario creado: {user.username}",
            "metadata": {
                "roles": sorted(normalized_roles),
            },
        }
        if store_id is not None:
            log_details["metadata"]["store_id"] = store_id
        if reason:
            log_details["metadata"]["reason"] = reason.strip()

        _log_action(
            db,
            action="user_created",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
            details=log_details,
        )

        flush_session(db)
        db.refresh(user)
    return user


def list_users(
    db: Session,
    *,
    search: str | None = None,
    role: str | None = None,
    status: Literal["all", "active", "inactive", "locked"] = "all",
    store_id: int | None = None,
    limit: int | None = 50,
    offset: int = 0,
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

    if status_normalized == "locked":
        users = list(db.scalars(statement).unique())
        locked_users = [user for user in users if _user_is_locked(user)]
        end = offset + limit if limit is not None else None
        return locked_users[offset:end]

    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def count_users(
    db: Session,
    *,
    include_inactive: bool = True,
) -> int:
    statement = select(func.count()).select_from(models.User)
    if not include_inactive:
        statement = statement.where(models.User.is_active.is_(True))
    total = db.scalar(statement)
    return int(total or 0)


def set_user_roles(
    db: Session,
    user: models.User,
    role_names: Iterable[str],
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.User:
    normalized_roles = _normalize_role_names(role_names)
    primary_role = _select_primary_role(normalized_roles)
    if primary_role not in normalized_roles:
        normalized_roles.append(primary_role)
    log_payload: dict[str, object] = {"roles": sorted(normalized_roles)}
    if reason:
        log_payload["reason"] = reason

    with transactional_session(db):
        user.roles.clear()
        flush_session(db)
        assignments = _build_role_assignments(db, normalized_roles)
        user.roles.extend(assignments)

        user.rol = primary_role

        _log_action(
            db,
            action="user_roles_updated",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
            details=json.dumps(log_payload, ensure_ascii=False),
        )

        flush_session(db)
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
    log_payload: dict[str, object] = {
        "is_active": is_active,
        "estado": "ACTIVO" if is_active else "INACTIVO",
    }
    if reason:
        log_payload["reason"] = reason

    with transactional_session(db):
        user.is_active = is_active
        user.estado = log_payload["estado"]

        _log_action(
            db,
            action="user_status_changed",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
            details=json.dumps(log_payload, ensure_ascii=False),
        )

        flush_session(db)
        db.refresh(user)
    return user


def get_role(db: Session, name: str) -> models.Role:
    statement = select(models.Role).where(
        func.upper(models.Role.name) == name.strip().upper())
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
        normalized_name = raw_name.strip() if isinstance(
            raw_name, str) and raw_name.strip() else None
        if user.full_name != normalized_name:
            user.full_name = normalized_name
            changes["full_name"] = normalized_name

    if "telefono" in updates:
        raw_phone = updates.get("telefono")
        normalized_phone = raw_phone.strip() if isinstance(
            raw_phone, str) and raw_phone.strip() else None
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

    log_payload: dict[str, object] = {"changes": changes}
    if reason:
        log_payload["reason"] = reason

    with transactional_session(db):
        flush_session(db)

        _log_action(
            db,
            action="user_updated",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
            details=json.dumps(log_payload, ensure_ascii=False),
        )

        flush_session(db)
        db.refresh(user)
    return user


def list_role_permissions(
    db: Session,
    *,
    role_name: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[schemas.RolePermissionMatrix]:
    role_names: list[str]
    if role_name:
        role = get_role(db, role_name)
        role_names = [role.name]
    else:
        role_names = [role.name for role in list_roles(
            db, limit=limit, offset=offset)]

    if not role_names:
        return []

    with transactional_session(db):
        for name in role_names:
            ensure_role_permissions(db, name)

        flush_session(db)

        statement = (
            select(models.Permission)
            .where(models.Permission.role_name.in_(role_names))
            .order_by(models.Permission.role_name.asc(), models.Permission.module.asc())
        )
        records = list(db.scalars(statement))

    grouped: dict[str, list[schemas.RoleModulePermission]] = {
        name: [] for name in role_names}
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
        permissions = sorted(grouped.get(name, []),
                             key=lambda item: item.module)
        matrices.append(schemas.RolePermissionMatrix(
            role=name, permissions=permissions))
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
    with transactional_session(db):
        ensure_role_permissions(db, role.name)
        flush_session(db)

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
                permission = models.Permission(
                    role_name=role.name, module=module_key)
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

        flush_session(db)

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

        flush_session(db)

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
        limit=None,
        offset=0,
    )

    user_ids = [user.id for user in users if getattr(
        user, "id", None) is not None]
    audit_logs = get_last_audit_entries(
        db,
        entity_type="user",
        entity_ids=user_ids,
    )
    audit_trails = {
        key: audit_trail_utils.to_audit_trail(log)
        for key, log in audit_logs.items()
    }

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
            ultima_accion=audit_trails.get(str(user.id)),
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
                models.AuditLog.entity_type.in_(
                    ["user", "usuarios", "security"]),
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
                severity=audit_utils.classify_severity(
                    log.action or "", log.details),
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
                username=_user_display_name(
                    session.user) or f"Usuario {session.user_id}",
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
    acknowledged_entities: dict[tuple[str, str],
                                schemas.AuditAcknowledgedEntity] = {}
    for highlight in summary.highlights:
        key = (highlight["entity_type"], highlight["entity_id"])
        alert_data = persistent_map.get(key)
        raw_status = str(alert_data.get("status", "pending")
                         ) if alert_data else "pending"
        status = "acknowledged" if raw_status.lower() == "acknowledged" else "pending"
        acknowledged_at = alert_data.get(
            "acknowledged_at") if alert_data else None
        acknowledged_by_id = alert_data.get(
            "acknowledged_by_id") if alert_data else None
        acknowledged_by_name = alert_data.get(
            "acknowledged_by_name") if alert_data else None
        acknowledged_note = alert_data.get(
            "acknowledged_note") if alert_data else None

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
                status=status,
                acknowledged_at=acknowledged_at,
                acknowledged_by_id=acknowledged_by_id,
                acknowledged_by_name=acknowledged_by_name,
                acknowledged_note=acknowledged_note,
            )
        )

    pending_count = len(
        [item for item in highlights if item.status != "acknowledged"])
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
    statement = select(models.UserTOTPSecret).where(
        models.UserTOTPSecret.user_id == user_id)
    return db.scalars(statement).first()


def provision_totp_secret(
    db: Session,
    user_id: int,
    secret: str,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.UserTOTPSecret:
    details = json.dumps({"reason": reason},
                         ensure_ascii=False) if reason else None
    with transactional_session(db):
        record = get_totp_secret(db, user_id)
        if record is None:
            record = models.UserTOTPSecret(
                user_id=user_id, secret=secret, is_active=False)
            db.add(record)
        else:
            record.secret = secret
            record.is_active = False
            record.activated_at = None
            record.last_verified_at = None
        flush_session(db)
        _log_action(
            db,
            action="totp_provisioned",
            entity_type="user",
            entity_id=str(user_id),
            performed_by_id=performed_by_id,
            details=details,
        )
    db.refresh(record)
    return record


def activate_totp_secret(
    db: Session,
    user_id: int,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.UserTOTPSecret:
    details = json.dumps({"reason": reason},
                         ensure_ascii=False) if reason else None
    with transactional_session(db):
        record = get_totp_secret(db, user_id)
        if record is None:
            raise LookupError("totp_not_provisioned")
        record.is_active = True
        now = datetime.utcnow()
        record.activated_at = now
        record.last_verified_at = now
        flush_session(db)
        _log_action(
            db,
            action="totp_activated",
            entity_type="user",
            entity_id=str(user_id),
            performed_by_id=performed_by_id,
            details=details,
        )
    db.refresh(record)
    return record


def deactivate_totp_secret(
    db: Session,
    user_id: int,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> None:
    details = json.dumps({"reason": reason},
                         ensure_ascii=False) if reason else None
    with transactional_session(db):
        record = get_totp_secret(db, user_id)
        if record is None:
            return
        record.is_active = False
        flush_session(db)
        _log_action(
            db,
            action="totp_deactivated",
            entity_type="user",
            entity_id=str(user_id),
            performed_by_id=performed_by_id,
            details=details,
        )


def update_totp_last_verified(db: Session, user_id: int) -> None:
    with transactional_session(db):
        record = get_totp_secret(db, user_id)
        if record is None:
            return
        record.last_verified_at = datetime.utcnow()
        flush_session(db)


def clear_login_lock(db: Session, user: models.User) -> models.User:
    if user.locked_until and user.locked_until <= datetime.utcnow():
        with transactional_session(db):
            user.locked_until = None
            user.failed_login_attempts = 0
            flush_session(db)
        db.refresh(user)
    return user


def register_failed_login(
    db: Session, user: models.User, *, reason: str | None = None
) -> models.User:
    locked_until: datetime | None = None
    with transactional_session(db):
        now = datetime.utcnow()
        user.failed_login_attempts += 1
        user.last_login_attempt_at = now
        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            locked_until = now + \
                timedelta(minutes=settings.account_lock_minutes)
            user.locked_until = locked_until
        details_payload: dict[str, object] = {
            "attempts": user.failed_login_attempts,
            "locked_until": locked_until.isoformat() if locked_until else None,
        }
        if reason:
            details_payload["reason"] = reason
        details = json.dumps(details_payload, ensure_ascii=False)
        flush_session(db)
        _log_action(
            db,
            action="auth_login_failed",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=user.id,
            details=details,
        )
    db.refresh(user)
    return user


def register_successful_login(
    db: Session, user: models.User, *, session_token: str | None = None
) -> models.User:
    with transactional_session(db):
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_attempt_at = datetime.utcnow()
        details_payload = (
            {"session_hint": session_token[-6:]} if session_token else None
        )
        details = (
            json.dumps(details_payload, ensure_ascii=False)
            if details_payload is not None
            else None
        )
        flush_session(db)
        _log_action(
            db,
            action="auth_login_success",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=user.id,
            details=details,
        )
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


def create_password_reset_token(
    db: Session, user_id: int, *, expires_minutes: int
) -> models.PasswordResetToken:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
    protected_token = token_protection.protect_token(token)
    record = models.PasswordResetToken(
        user_id=user_id,
        token=protected_token,
        expires_at=expires_at,
    )
    record.plaintext_token = token  # type: ignore[attr-defined]
    details = json.dumps(
        {"expires_at": record.expires_at.isoformat()}, ensure_ascii=False
    )
    with transactional_session(db):
        db.add(record)
        flush_session(db)
        _log_action(
            db,
            action="password_reset_requested",
            entity_type="user",
            entity_id=str(user_id),
            performed_by_id=None,
            details=details,
        )
    db.refresh(record)
    return record


def get_password_reset_token(
    db: Session, token: str
) -> models.PasswordResetToken | None:
    statement = select(models.PasswordResetToken).where(
        _token_filter(models.PasswordResetToken.token, token)
    )
    return db.scalars(statement).first()


def mark_password_reset_token_used(
    db: Session, token_record: models.PasswordResetToken
) -> models.PasswordResetToken:
    with transactional_session(db):
        token_record.used_at = datetime.utcnow()
        flush_session(db)
    db.refresh(token_record)
    return token_record


def reset_user_password(
    db: Session,
    user: models.User,
    *,
    password_hash: str,
    performed_by_id: int | None = None,
) -> models.User:
    with transactional_session(db):
        user.password_hash = password_hash
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_attempt_at = datetime.utcnow()
        flush_session(db)
        _log_action(
            db,
            action="password_reset_completed",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
        )
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
    stored_token = token_protection.protect_token(session_token)
    session = models.ActiveSession(
        user_id=user_id, session_token=stored_token, expires_at=expires_at
    )
    with transactional_session(db):
        db.add(session)
        flush_session(db)
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
        .where(_token_filter(models.ActiveSession.session_token, session_token))
    )
    return db.scalars(statement).first()


def mark_session_used(db: Session, session_token: str) -> models.ActiveSession | None:
    session = get_active_session_by_token(db, session_token)
    if session is None or session.revoked_at is not None:
        return None
    if is_session_expired(session.expires_at):
        if session.revoked_at is None:
            with transactional_session(db):
                session.revoked_at = datetime.now(timezone.utc)
                session.revoke_reason = session.revoke_reason or "expired"
                flush_session(db)
            db.refresh(session)
        return None
    with transactional_session(db):
        session.last_used_at = datetime.utcnow()
        flush_session(db)
    db.refresh(session)
    return session


def add_jwt_to_blacklist(
    db: Session,
    *,
    jti: str,
    token_type: str,
    expires_at: datetime,
    revoked_by_id: int | None = None,
    reason: str | None = None,
) -> models.JWTBlacklist:
    record = models.JWTBlacklist(
        jti=jti,
        token_type=token_type,
        expires_at=expires_at,
        revoked_by_id=revoked_by_id,
        reason=reason,
    )
    with transactional_session(db):
        db.add(record)
        flush_session(db)
    db.refresh(record)
    return record


def is_jwt_blacklisted(db: Session, jti: str) -> bool:
    statement = select(models.JWTBlacklist).where(models.JWTBlacklist.jti == jti)
    record = db.scalars(statement).first()
    if record is None:
        return False
    if record.expires_at and is_session_expired(record.expires_at):
        with transactional_session(db):
            db.delete(record)
            flush_session(db)
        return False
    return True


def list_active_sessions(
    db: Session,
    *,
    user_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.ActiveSession]:
    statement = (
        select(models.ActiveSession)
        .order_by(models.ActiveSession.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
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
    statement = select(models.ActiveSession).where(
        models.ActiveSession.id == session_id)
    session = db.scalars(statement).first()
    if session is None:
        raise LookupError("session_not_found")
    if session.revoked_at is not None:
        return session
    with transactional_session(db):
        session.revoked_at = datetime.utcnow()
        session.revoked_by_id = revoked_by_id
        session.revoke_reason = reason
        flush_session(db)
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
    with transactional_session(db):
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
            flush_session(db)
        except IntegrityError as exc:
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
        flush_session(db)
        db.refresh(store)
    return store


def update_store(
    db: Session,
    store_id: int,
    payload: schemas.StoreUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.Store:
    store = get_store(db, store_id)

    changes: list[str] = []
    if payload.name is not None:
        normalized_name = payload.name.strip()
        if normalized_name and normalized_name != store.name:
            changes.append(f"name:{store.name}->{normalized_name}")
            store.name = normalized_name

    if payload.location is not None:
        normalized_location = payload.location.strip() if payload.location else None
        if normalized_location != store.location:
            previous = store.location or ""
            new_value = normalized_location or ""
            changes.append(f"location:{previous}->{new_value}")
            store.location = normalized_location

    if payload.status is not None:
        normalized_status = _normalize_store_status(payload.status)
        if normalized_status != store.status:
            changes.append(f"status:{store.status}->{normalized_status}")
            store.status = normalized_status

    if payload.code is not None:
        normalized_code = _normalize_store_code(payload.code)
        if normalized_code != store.code and normalized_code is not None:
            changes.append(f"code:{store.code}->{normalized_code}")
            store.code = normalized_code

    if payload.timezone is not None:
        normalized_timezone = (payload.timezone or "UTC").strip() or "UTC"
        if normalized_timezone != store.timezone:
            changes.append(f"timezone:{store.timezone}->{normalized_timezone}")
            store.timezone = normalized_timezone

    if not changes:
        return store

    with transactional_session(db):
        db.add(store)
        try:
            flush_session(db)
        except IntegrityError as exc:
            message = str(getattr(exc, "orig", exc)).lower()
            if "codigo" in message or "uq_sucursales_codigo" in message:
                raise ValueError("store_code_already_exists") from exc
            raise ValueError("store_already_exists") from exc
        db.refresh(store)

        details = ", ".join(changes)
        _log_action(
            db,
            action="store_updated",
            entity_type="store",
            entity_id=str(store.id),
            performed_by_id=performed_by_id,
            details=details or None,
        )
        flush_session(db)
        db.refresh(store)
    return store


def list_stores(
    db: Session,
    *,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.Store]:
    statement = select(models.Store).order_by(models.Store.name.asc())
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement))


def count_stores(db: Session) -> int:
    statement = select(func.count()).select_from(models.Store)
    return int(db.scalar(statement) or 0)


def list_customers(
    db: Session,
    *,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    customer_type: str | None = None,
    has_debt: bool | None = None,
    segment_category: str | None = None,
    tags: Sequence[str] | None = None,
) -> list[models.Customer]:
    statement = (
        select(models.Customer)
        .options(selectinload(models.Customer.loyalty_account))
        .options(selectinload(models.Customer.segment_snapshot))
        .where(models.Customer.is_deleted.is_(False))
        .order_by(models.Customer.name.asc())
        .offset(offset)
        .limit(limit)
    )
    if status:
        normalized_status = _normalize_customer_status(status)
        statement = statement.where(
            models.Customer.status == normalized_status)
    if customer_type:
        normalized_type = _normalize_customer_type(customer_type)
        statement = statement.where(
            models.Customer.customer_type == normalized_type)
    if segment_category:
        normalized_category = _normalize_customer_segment_category(segment_category)
        if normalized_category:
            statement = statement.where(
                models.Customer.segment_category == normalized_category
            )
    normalized_tags = _normalize_customer_tags(tags)
    if normalized_tags:
        tags_column = func.lower(cast(models.Customer.tags, String))
        for tag in normalized_tags:
            statement = statement.where(tags_column.like(f'%"{tag}"%'))
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
                func.lower(func.coalesce(models.Customer.segment_category, "")).like(normalized),
                func.lower(func.coalesce(models.Customer.notes, "")
                           ).like(normalized),
                func.lower(cast(models.Customer.tags, String)).like(normalized),
                func.lower(func.coalesce(models.Customer.tax_id, "")).like(normalized),
            )
        )
    if has_debt is True:
        statement = statement.where(models.Customer.outstanding_debt > 0)
    elif has_debt is False:
        statement = statement.where(models.Customer.outstanding_debt <= 0)
    return list(db.scalars(statement))


def get_customer(db: Session, customer_id: int) -> models.Customer:
    statement = (
        select(models.Customer)
        .options(selectinload(models.Customer.loyalty_account))
        .options(selectinload(models.Customer.segment_snapshot))
        .options(selectinload(models.Customer.privacy_requests))
        .where(
            models.Customer.id == customer_id,
            models.Customer.is_deleted.is_(False),
        )
    )
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
    with transactional_session(db):
        history = _history_to_json(payload.history)
        customer_type = _normalize_customer_type(payload.customer_type)
        status = _normalize_customer_status(payload.status)
        segment_category = _normalize_customer_segment_category(
            payload.segment_category
        )
        tags = _normalize_customer_tags(payload.tags)
        tax_id = _normalize_customer_tax_id(payload.tax_id)
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
            segment_category=segment_category,
            tags=tags,
            tax_id=tax_id,
            credit_limit=credit_limit,
            notes=payload.notes,
            history=history,
            outstanding_debt=outstanding_debt,
            last_interaction_at=_last_history_timestamp(history),
        )
        db.add(customer)
        try:
            flush_session(db)
        except IntegrityError as exc:
            if _is_tax_id_integrity_error(exc):
                raise ValueError("customer_tax_id_duplicate") from exc
            raise ValueError("customer_already_exists") from exc
        db.refresh(customer)

        _log_action(
            db,
            action="customer_created",
            entity_type="customer",
            entity_id=str(customer.id),
            performed_by_id=performed_by_id,
            details=json.dumps({
                "name": customer.name,
                "tax_id": customer.tax_id,
                "segment_category": customer.segment_category,
                "tags": customer.tags,
            }),
        )
        flush_session(db)
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
    with transactional_session(db):
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
        if payload.tax_id is not None:
            normalized_tax_id = _normalize_customer_tax_id(
                payload.tax_id, allow_placeholder=False
            )
            customer.tax_id = normalized_tax_id
            updated_fields["tax_id"] = normalized_tax_id
        if payload.segment_category is not None:
            normalized_category = _normalize_customer_segment_category(
                payload.segment_category
            )
            customer.segment_category = normalized_category
            updated_fields["segment_category"] = normalized_category
        if payload.tags is not None:
            normalized_tags = _normalize_customer_tags(payload.tags)
            customer.tags = normalized_tags
            updated_fields["tags"] = normalized_tags
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
        _ensure_debt_respects_limit(
            customer.credit_limit, customer.outstanding_debt)
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
        try:
            flush_session(db)
        except IntegrityError as exc:
            if _is_tax_id_integrity_error(exc):
                raise ValueError("customer_tax_id_duplicate") from exc
            raise
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
            flush_session(db)
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
    allow_hard_delete: bool = False,
    is_superadmin: bool = False,
) -> None:
    customer = get_customer(db, customer_id)
    has_dependencies = any(
        [
            customer.sales,
            customer.repair_orders,
            customer.ledger_entries,
            customer.store_credits,
        ]
    )
    should_hard_delete = allow_hard_delete and (not has_dependencies or is_superadmin)
    with transactional_session(db):
        if should_hard_delete:
            db.delete(customer)
            flush_session(db)
            _log_action(
                db,
                action="customer_deleted",
                entity_type="customer",
                entity_id=str(customer_id),
                performed_by_id=performed_by_id,
            )
            flush_session(db)
            enqueue_sync_outbox(
                db,
                entity_type="customer",
                entity_id=str(customer_id),
                operation="DELETE",
                payload={"id": customer_id, "hard_deleted": True},
            )
            return

        customer.status = _normalize_customer_status("inactivo")
        customer.is_deleted = True
        customer.deleted_at = datetime.utcnow()
        flush_session(db)
        _log_action(
            db,
            action="customer_archived",
            entity_type="customer",
            entity_id=str(customer_id),
            performed_by_id=performed_by_id,
        )
        flush_session(db)
        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer_id),
            operation="UPDATE",
            payload={
                "id": customer_id,
                "is_deleted": True,
                "deleted_at": customer.deleted_at.isoformat() if customer.deleted_at else None,
            },
        )


def export_customers_csv(
    db: Session,
    *,
    query: str | None = None,
    status: str | None = None,
    customer_type: str | None = None,
    segment_category: str | None = None,
    tags: Sequence[str] | None = None,
) -> str:
    customers = list_customers(
        db,
        query=query,
        limit=5000,
        offset=0,
        status=status,
        customer_type=customer_type,
        segment_category=segment_category,
        tags=tags,
    )
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ID",
            "Nombre",
            "Tipo",
            "Estado",
            "Categoría",
            "Etiquetas",
            "RTN",
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
                customer.segment_category or "",
                ", ".join(customer.tags or []),
                customer.tax_id,
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
    with transactional_session(db):
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


@dataclass(slots=True)
class CustomerPaymentOutcome:
    ledger_entry: models.CustomerLedgerEntry
    customer: models.Customer
    previous_debt: Decimal
    applied_amount: Decimal
    requested_amount: Decimal


def register_customer_payment(
    db: Session,
    customer_id: int,
    payload: schemas.CustomerPaymentCreate,
    *,
    performed_by_id: int | None = None,
) -> CustomerPaymentOutcome:
    customer = get_customer(db, customer_id)
    current_debt = _to_decimal(customer.outstanding_debt).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    sale = None
    if payload.sale_id is not None:
        sale = get_sale(db, payload.sale_id)
        if sale.customer_id != customer.id:
            raise ValueError("customer_payment_sale_mismatch")

    if current_debt <= Decimal("0") and sale is None:
        raise ValueError("customer_payment_no_debt")

    amount = _to_decimal(payload.amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if amount <= Decimal("0"):
        raise ValueError("customer_payment_invalid_amount")

    applied_amount = min(current_debt, amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    customer.outstanding_debt = (current_debt - applied_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    _append_customer_history(
        customer,
        f"Pago registrado por ${_format_currency(applied_amount)}",
    )
    db.add(customer)

    # Mantener valores numéricos en detalles para facilitar cálculos en respuestas API.
    # Esto permite que los consumidores de la API realicen operaciones aritméticas directamente,
    # evitando la necesidad de convertir cadenas de texto formateadas como moneda a números.
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

    with transactional_session(db):
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
                    "applied_amount": _format_currency(applied_amount),
                    "method": payload.method,
                    "reference": payload.reference,
                    "sale_id": sale.id if sale is not None else None,
                }
            ),
        )

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

    outcome = CustomerPaymentOutcome(
        ledger_entry=ledger_entry,
        customer=customer,
        previous_debt=current_debt,
        applied_amount=applied_amount,
        requested_amount=amount,
    )
    return outcome


def list_payment_center_transactions(
    db: Session,
    *,
    limit: int = 50,
    query: str | None = None,
    method: str | None = None,
    type_filter: Literal["PAYMENT", "REFUND", "CREDIT_NOTE"] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[schemas.PaymentCenterTransaction]:
    stmt = (
        select(
            models.CustomerLedgerEntry.id,
            models.CustomerLedgerEntry.entry_type,
            models.CustomerLedgerEntry.amount,
            models.CustomerLedgerEntry.created_at,
            models.CustomerLedgerEntry.note,
            models.Customer.id.label("customer_id"),
            models.Customer.name.label("customer_name"),
            models.CustomerLedgerEntry.reference_id,
            models.CustomerLedgerEntry.details,
        )
        .join(
            models.Customer,
            models.Customer.id == models.CustomerLedgerEntry.customer_id,
        )
        .where(
            models.CustomerLedgerEntry.entry_type.in_(
                [
                    models.CustomerLedgerEntryType.PAYMENT,
                    models.CustomerLedgerEntryType.ADJUSTMENT,
                ]
            )
        )
        .order_by(models.CustomerLedgerEntry.created_at.desc())
        .limit(limit)
    )

    if date_from is not None:
        stmt = stmt.where(models.CustomerLedgerEntry.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(models.CustomerLedgerEntry.created_at <= date_to)

    if query:
        search = f"%{query.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(models.Customer.name).like(search),
                func.lower(models.CustomerLedgerEntry.reference_id).like(
                    search),
            )
        )

    rows = db.execute(stmt).all()
    transactions: list[schemas.PaymentCenterTransaction] = []
    for row in rows:
        entry_type: models.CustomerLedgerEntryType = row.entry_type
        details_payload: dict[str, Any]
        if isinstance(row.details, dict):
            details_payload = row.details
        else:
            details_payload = {}
            if isinstance(row.details, str):
                try:
                    details_payload = json.loads(row.details)
                except json.JSONDecodeError:
                    details_payload = {}

        event = str(details_payload.get("event", "")).strip().lower()
        method_name = str(details_payload.get("method", "")).strip()
        if entry_type == models.CustomerLedgerEntryType.PAYMENT:
            tx_type = "PAYMENT"
        elif entry_type == models.CustomerLedgerEntryType.ADJUSTMENT:
            if event in {"sale_return", "manual_refund"}:
                tx_type = "REFUND"
            elif event == "credit_note":
                tx_type = "CREDIT_NOTE"
            else:
                continue
        else:
            continue

        if type_filter and tx_type != type_filter:
            continue
        if method and method_name.lower() != method.lower():
            continue

        amount_value = float(abs(row.amount or Decimal("0")))
        sale_reference = details_payload.get("sale_id") or row.reference_id
        order_id: int | None = None
        order_number: str | None = None
        if sale_reference:
            order_number = str(sale_reference)
            try:
                order_id = int(str(sale_reference))
            except (TypeError, ValueError):
                order_id = None

        transactions.append(
            schemas.PaymentCenterTransaction(
                id=row.id,
                type=tx_type,
                amount=amount_value,
                created_at=row.created_at,
                order_id=order_id,
                order_number=order_number,
                customer_id=row.customer_id,
                customer_name=row.customer_name,
                method=method_name or None,
                note=row.note,
            )
        )
    return transactions


def get_payment_center_summary(
    db: Session,
    *,
    reference: datetime | None = None,
) -> schemas.PaymentCenterSummary:
    reference = reference or datetime.utcnow()
    tzinfo = reference.tzinfo
    today_start = datetime(reference.year, reference.month,
                           reference.day, tzinfo=tzinfo)
    tomorrow_start = today_start + timedelta(days=1)
    month_start = datetime(reference.year, reference.month, 1, tzinfo=tzinfo)
    if reference.month == 12:
        next_month_start = datetime(reference.year + 1, 1, 1, tzinfo=tzinfo)
    else:
        next_month_start = datetime(
            reference.year, reference.month + 1, 1, tzinfo=tzinfo)

    payments_today_stmt = select(
        func.coalesce(-func.sum(models.CustomerLedgerEntry.amount),
                      Decimal("0"))
    ).where(
        models.CustomerLedgerEntry.entry_type
        == models.CustomerLedgerEntryType.PAYMENT,
        models.CustomerLedgerEntry.created_at >= today_start,
        models.CustomerLedgerEntry.created_at < tomorrow_start,
    )

    payments_month_stmt = select(
        func.coalesce(-func.sum(models.CustomerLedgerEntry.amount),
                      Decimal("0"))
    ).where(
        models.CustomerLedgerEntry.entry_type
        == models.CustomerLedgerEntryType.PAYMENT,
        models.CustomerLedgerEntry.created_at >= month_start,
        models.CustomerLedgerEntry.created_at < next_month_start,
    )

    pending_balance_stmt = select(
        func.coalesce(func.sum(models.Customer.outstanding_debt), Decimal("0"))
    ).where(models.Customer.outstanding_debt > 0)

    collections_today = db.scalar(payments_today_stmt) or Decimal("0")
    collections_month = db.scalar(payments_month_stmt) or Decimal("0")
    refunds_month_total = Decimal("0")
    refunds_stmt = (
        select(
            models.CustomerLedgerEntry.amount,
            models.CustomerLedgerEntry.details,
        )
        .where(
            models.CustomerLedgerEntry.entry_type
            == models.CustomerLedgerEntryType.ADJUSTMENT,
            models.CustomerLedgerEntry.created_at >= month_start,
            models.CustomerLedgerEntry.created_at < next_month_start,
        )
    )
    for amount_value, details in db.execute(refunds_stmt):
        details_payload: dict[str, Any]
        if isinstance(details, dict):
            details_payload = details
        else:
            details_payload = {}
            if isinstance(details, str):
                try:
                    details_payload = json.loads(details)
                except json.JSONDecodeError:
                    details_payload = {}
        event_name = str(details_payload.get("event", "")).strip()
        if event_name in {"sale_return", "manual_refund"}:
            refunds_month_total += -_to_decimal(amount_value)
    refunds_month_total = refunds_month_total.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    pending_balance = db.scalar(pending_balance_stmt) or Decimal("0")

    return schemas.PaymentCenterSummary(
        collections_today=float(collections_today),
        collections_month=float(collections_month),
        refunds_month=float(refunds_month_total),
        pending_balance=float(pending_balance),
    )


def register_payment_center_refund(
    db: Session,
    payload: schemas.PaymentCenterRefundCreate,
    *,
    performed_by_id: int | None = None,
) -> models.CustomerLedgerEntry:
    customer = get_customer(db, payload.customer_id)
    amount = _to_decimal(payload.amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if amount <= Decimal("0"):
        raise ValueError("payment_center_refund_invalid_amount")

    normalized_note = (payload.note or f"Reembolso {payload.reason}").strip()
    if not normalized_note:
        normalized_note = f"Reembolso {payload.reason}"

    with transactional_session(db):
        current_debt = _to_decimal(customer.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        new_debt = (current_debt - amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if new_debt < Decimal("0"):
            new_debt = Decimal("0")
        customer.outstanding_debt = new_debt
        _append_customer_history(
            customer,
            f"Reembolso registrado por ${_format_currency(amount)}",
        )
        db.add(customer)

        details: dict[str, object] = {
            "event": "manual_refund",
            "method": payload.method,
            "reason": payload.reason,
            "amount": _format_currency(amount),
        }
        if payload.sale_id is not None:
            details["sale_id"] = payload.sale_id

        ledger_entry = _create_customer_ledger_entry(
            db,
            customer=customer,
            entry_type=models.CustomerLedgerEntryType.ADJUSTMENT,
            amount=-amount,
            note=normalized_note,
            reference_type="sale" if payload.sale_id is not None else "refund",
            reference_id=str(
                payload.sale_id) if payload.sale_id is not None else None,
            details=details,
            created_by_id=performed_by_id,
        )

        _log_action(
            db,
            action="customer_refund_registered",
            entity_type="customer",
            entity_id=str(customer.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "amount": _format_currency(amount),
                    "method": payload.method,
                    "reason": payload.reason,
                    "sale_id": payload.sale_id,
                }
            ),
        )

        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer.id),
            operation="UPSERT",
            payload=_customer_payload(customer),
        )
        _sync_customer_ledger_entry(db, ledger_entry)
    return ledger_entry


def register_payment_center_credit_note(
    db: Session,
    payload: schemas.PaymentCenterCreditNoteCreate,
    *,
    performed_by_id: int | None = None,
) -> models.CustomerLedgerEntry:
    customer = get_customer(db, payload.customer_id)
    amount = _to_decimal(payload.total).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if amount <= Decimal("0"):
        raise ValueError("payment_center_credit_note_invalid_amount")

    note = (payload.note or "Nota de crédito aplicada").strip()
    if not note:
        note = "Nota de crédito aplicada"

    details: dict[str, object] = {
        "event": "credit_note",
        "lines": [
            {
                "description": line.description,
                "quantity": line.quantity,
                "amount": _format_currency(line.amount),
            }
            for line in payload.lines
        ],
    }
    if payload.sale_id is not None:
        details["sale_id"] = payload.sale_id

    with transactional_session(db):
        current_debt = _to_decimal(customer.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        new_debt = (current_debt - amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if new_debt < Decimal("0"):
            new_debt = Decimal("0")
        customer.outstanding_debt = new_debt
        _append_customer_history(
            customer,
            f"Nota de crédito registrada por ${_format_currency(amount)}",
        )
        db.add(customer)

        ledger_entry = _create_customer_ledger_entry(
            db,
            customer=customer,
            entry_type=models.CustomerLedgerEntryType.ADJUSTMENT,
            amount=-amount,
            note=note,
            reference_type="sale" if payload.sale_id is not None else "credit_note",
            reference_id=str(
                payload.sale_id) if payload.sale_id is not None else None,
            details=details,
            created_by_id=performed_by_id,
        )

        _log_action(
            db,
            action="customer_credit_note_registered",
            entity_type="customer",
            entity_id=str(customer.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "amount": _format_currency(amount),
                    "sale_id": payload.sale_id,
                    "lines": details["lines"],
                }
            ),
        )

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
    store_credits = list(
        db.scalars(
            select(models.StoreCredit)
            .options(
                selectinload(models.StoreCredit.redemptions).joinedload(
                    models.StoreCreditRedemption.created_by
                )
            )
            .where(models.StoreCredit.customer_id == customer.id)
            .order_by(models.StoreCredit.issued_at.desc(), models.StoreCredit.id.desc())
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
        config_stmt = select(models.POSConfig).where(
            models.POSConfig.store_id.in_(store_ids))
        configs = {
            config.store_id: config for config in db.scalars(config_stmt)}

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
    total_store_credit_issued = sum(
        (_to_decimal(credit.issued_amount) for credit in store_credits),
        Decimal("0"),
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_store_credit_available = sum(
        (
            _to_decimal(credit.balance_amount)
            for credit in store_credits
            if credit.status
            in {models.StoreCreditStatus.ACTIVO, models.StoreCreditStatus.PARCIAL}
        ),
        Decimal("0"),
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_store_credit_redeemed = (
        total_store_credit_issued - total_store_credit_available
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    snapshot = schemas.CustomerFinancialSnapshot(
        credit_limit=float(credit_limit),
        outstanding_debt=float(outstanding),
        available_credit=float(available_credit),
        total_sales_credit=total_sales_credit,
        total_payments=total_payments,
        store_credit_issued=float(total_store_credit_issued),
        store_credit_available=float(total_store_credit_available),
        store_credit_redeemed=float(total_store_credit_redeemed),
    )

    customer_schema = schemas.CustomerResponse.model_validate(customer)
    store_credit_schema = [
        schemas.StoreCreditResponse.model_validate(credit)
        for credit in store_credits
    ]
    privacy_requests = [
        schemas.CustomerPrivacyRequestResponse.model_validate(entry)
        for entry in sorted(
            customer.privacy_requests,
            key=lambda record: record.created_at,
            reverse=True,
        )[:20]
    ]

    return schemas.CustomerSummaryResponse(
        customer=customer_schema,
        totals=snapshot,
        sales=sales_summary,
        invoices=invoices,
        payments=payments[:20],
        ledger=ledger_entries[:50],
        store_credits=store_credit_schema,
        privacy_requests=privacy_requests,
    )


def create_customer_privacy_request(
    db: Session,
    customer_id: int,
    payload: schemas.CustomerPrivacyRequestCreate,
    *,
    performed_by_id: int | None = None,
) -> tuple[models.Customer, models.CustomerPrivacyRequest]:
    customer = get_customer(db, customer_id)
    request_type = models.PrivacyRequestType(payload.request_type)
    now = datetime.utcnow()
    consent_snapshot = dict(customer.privacy_consents or {})
    masked_fields: list[str] = []

    with transactional_session(db):
        if request_type == models.PrivacyRequestType.CONSENT:
            updates = payload.consent or {}
            if not updates:
                raise ValueError("privacy_consent_required")
            consent_snapshot.update(updates)
            customer.privacy_consents = consent_snapshot
            summary = ", ".join(
                f"{key}={'sí' if value else 'no'}"
                for key, value in updates.items()
            )
            history_note = (
                f"Consentimientos actualizados ({summary})"
                if summary
                else "Consentimientos actualizados."
            )
            _append_customer_history(customer, history_note)
        else:
            masked_fields = _apply_customer_anonymization(
                customer, payload.mask_fields
            )
            consent_snapshot = dict(customer.privacy_consents or {})
            summary = ", ".join(masked_fields) if masked_fields else "sin cambios"
            _append_customer_history(
                customer, f"Anonimización parcial aplicada ({summary})."
            )

        metadata = dict(customer.privacy_metadata or {})
        metadata["last_request"] = {
            "type": request_type.value,
            "timestamp": now.isoformat(),
            "details": payload.details,
            "masked_fields": masked_fields,
        }
        customer.privacy_metadata = metadata
        customer.privacy_last_request_at = now

        request = models.CustomerPrivacyRequest(
            customer_id=customer.id,
            request_type=request_type,
            status=models.PrivacyRequestStatus.PROCESADA,
            details=payload.details,
            consent_snapshot=consent_snapshot,
            masked_fields=masked_fields,
            processed_by_id=performed_by_id,
            processed_at=now,
        )

        db.add(customer)
        db.add(request)
        flush_session(db)
        db.refresh(customer)
        db.refresh(request)

        enqueue_sync_outbox(
            db,
            entity_type="customer",
            entity_id=str(customer.id),
            operation="UPSERT",
            payload=_customer_payload(customer),
        )
        enqueue_sync_outbox(
            db,
            entity_type="customer_privacy_request",
            entity_id=str(request.id),
            operation="UPSERT",
            payload=_customer_privacy_request_payload(request),
        )

        _log_action(
            db,
            action="customer_privacy_request",
            entity_type="customer",
            entity_id=str(customer.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "request_type": request_type.value,
                    "details": payload.details,
                    "masked_fields": masked_fields,
                }
            ),
        )

    return customer, request


def _resolve_sale_references(
    db: Session, sale_ids: set[int]
) -> tuple[dict[int, models.Sale], dict[int, models.POSConfig]]:
    if not sale_ids:
        return {}, {}
    sale_stmt = (
        select(models.Sale)
        .options(joinedload(models.Sale.store))
        .where(models.Sale.id.in_(sale_ids))
    )
    sale_map = {sale.id: sale for sale in db.scalars(sale_stmt)}
    store_ids = {sale.store_id for sale in sale_map.values()}
    if not store_ids:
        return sale_map, {}
    config_stmt = select(models.POSConfig).where(
        models.POSConfig.store_id.in_(store_ids)
    )
    config_map = {config.store_id: config for config in db.scalars(config_stmt)}
    return sale_map, config_map


def _format_sale_reference(
    sale_id: int,
    sale_map: Mapping[int, models.Sale],
    config_map: Mapping[int, models.POSConfig],
) -> str:
    sale = sale_map.get(sale_id)
    if sale is None:
        return f"Venta #{sale_id}"
    prefix = None
    if sale.store_id in config_map:
        prefix = config_map[sale.store_id].invoice_prefix
    if prefix:
        return f"{prefix}-{sale.id:06d}"
    return f"Venta #{sale.id}"


def _ledger_entry_label(entry: models.CustomerLedgerEntry) -> str:
    mapping = {
        models.CustomerLedgerEntryType.SALE: "Cargo por venta",
        models.CustomerLedgerEntryType.PAYMENT: "Pago registrado",
        models.CustomerLedgerEntryType.ADJUSTMENT: "Ajuste",
        models.CustomerLedgerEntryType.NOTE: "Nota",
        models.CustomerLedgerEntryType.STORE_CREDIT_ISSUED: "Nota de crédito emitida",
        models.CustomerLedgerEntryType.STORE_CREDIT_REDEEMED: "Nota de crédito aplicada",
    }
    base = mapping.get(entry.entry_type, entry.entry_type.value.replace("_", " ").title())
    if entry.note:
        return f"{base} — {entry.note}" if entry.note.strip() else base
    return base


def get_customer_accounts_receivable(
    db: Session, customer_id: int
) -> schemas.CustomerAccountsReceivableResponse:
    customer = get_customer(db, customer_id)

    ledger_entries = list(
        db.scalars(
            select(models.CustomerLedgerEntry)
            .where(models.CustomerLedgerEntry.customer_id == customer.id)
            .order_by(
                models.CustomerLedgerEntry.created_at.asc(),
                models.CustomerLedgerEntry.id.asc(),
            )
        )
    )

    charges: list[dict[str, object]] = []
    last_payment_at: datetime | None = None
    for entry in ledger_entries:
        amount = _to_decimal(entry.amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if amount > Decimal("0"):
            charges.append({
                "entry": entry,
                "original": amount,
                "remaining": amount,
            })
        elif amount < Decimal("0"):
            credit_amount = -amount
            for charge in charges:
                remaining = charge["remaining"]  # type: ignore[index]
                if remaining <= Decimal("0"):
                    continue
                allocation = min(remaining, credit_amount)
                charge["remaining"] = remaining - allocation  # type: ignore[index]
                credit_amount -= allocation
                if credit_amount <= Decimal("0"):
                    break
        if entry.entry_type == models.CustomerLedgerEntryType.PAYMENT:
            if last_payment_at is None or entry.created_at > last_payment_at:
                last_payment_at = entry.created_at

    outstanding_total = sum(
        _to_decimal(charge["remaining"])  # type: ignore[index]
        for charge in charges
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if outstanding_total < Decimal("0"):
        outstanding_total = Decimal("0.00")

    credit_limit = _to_decimal(customer.credit_limit).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    available_credit = (credit_limit - outstanding_total).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if available_credit < Decimal("0"):
        available_credit = Decimal("0.00")

    sale_ids: set[int] = set()
    for charge in charges:
        entry: models.CustomerLedgerEntry = charge["entry"]  # type: ignore[index]
        if (
            entry.reference_type == "sale"
            and entry.reference_id
            and entry.reference_id.isdigit()
        ):
            sale_ids.add(int(entry.reference_id))

    sale_map, config_map = _resolve_sale_references(db, sale_ids)

    bucket_defs: list[tuple[str, int, int | None]] = [
        ("0-30 días", 0, 30),
        ("31-60 días", 31, 60),
        ("61-90 días", 61, 90),
        ("90+ días", 91, None),
    ]
    bucket_totals: list[dict[str, object]] = [
        {"label": label, "from": start, "to": end, "amount": Decimal("0.00"), "count": 0}
        for label, start, end in bucket_defs
    ]

    today = datetime.utcnow().date()
    weighted_days = Decimal("0.00")
    open_entries: list[schemas.AccountsReceivableEntry] = []
    for charge in charges:
        entry: models.CustomerLedgerEntry = charge["entry"]  # type: ignore[index]
        remaining: Decimal = charge["remaining"]  # type: ignore[index]
        original: Decimal = charge["original"]  # type: ignore[index]
        if remaining <= Decimal("0"):
            continue
        days_outstanding = max(
            (today - entry.created_at.date()).days,
            0,
        )
        bucket_index = 0
        for idx, (_, start, end) in enumerate(bucket_defs):
            if end is None:
                bucket_index = idx
                break
            if days_outstanding <= end:
                if days_outstanding >= start:
                    bucket_index = idx
                    break
            elif idx == len(bucket_defs) - 1:
                bucket_index = idx
        bucket = bucket_totals[bucket_index]
        bucket["amount"] = _to_decimal(bucket["amount"]) + remaining  # type: ignore[index]
        bucket["count"] = int(bucket["count"]) + 1  # type: ignore[index]

        weighted_days += remaining * Decimal(days_outstanding)

        reference_label: str | None = None
        if entry.reference_type == "sale" and entry.reference_id and entry.reference_id.isdigit():
            sale_id = int(entry.reference_id)
            reference_label = _format_sale_reference(sale_id, sale_map, config_map)
        elif entry.reference_id:
            reference_label = f"{entry.reference_type} #{entry.reference_id}" if entry.reference_type else entry.reference_id

        details_payload = entry.details if isinstance(entry.details, dict) else None
        status = "overdue" if days_outstanding > 30 else "current"
        open_entries.append(
            schemas.AccountsReceivableEntry(
                ledger_entry_id=entry.id,
                reference_type=entry.reference_type,
                reference_id=entry.reference_id,
                reference=reference_label,
                issued_at=entry.created_at,
                original_amount=float(original),
                balance_due=float(remaining.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                days_outstanding=days_outstanding,
                status=status,  # type: ignore[arg-type]
                note=entry.note,
                details=details_payload or None,
            )
        )

    aging = []
    for bucket, (label, start, end) in zip(bucket_totals, bucket_defs):
        amount_decimal = _to_decimal(bucket["amount"])  # type: ignore[index]
        percentage = (
            float(
                (amount_decimal / outstanding_total * Decimal("100"))
                .quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            )
            if outstanding_total > Decimal("0")
            else 0.0
        )
        aging.append(
            schemas.AccountsReceivableBucket(
                label=label,
                days_from=start,
                days_to=end,
                amount=float(amount_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                percentage=percentage,
                count=int(bucket["count"]),  # type: ignore[index]
            )
        )

    average_days = 0.0
    if outstanding_total > Decimal("0"):
        average_days = float(
            (weighted_days / outstanding_total)
            .quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        )

    schedule_entries: list[schemas.CreditScheduleEntry] = []
    next_due_date: datetime | None = None
    if outstanding_total > Decimal("0"):
        base_date = None
        for charge in reversed(charges):
            if _to_decimal(charge["remaining"]) > Decimal("0"):  # type: ignore[index]
                entry: models.CustomerLedgerEntry = charge["entry"]  # type: ignore[index]
                base_date = entry.created_at
                break
        schedule = credit.build_credit_schedule(
            base_date=base_date,
            remaining_balance=outstanding_total,
        )
        if schedule:
            next_due_date = schedule[0]["due_date"]
        schedule_entries = [
            schemas.CreditScheduleEntry.model_validate(item) for item in schedule
        ]

    recent_entries = list(
        db.scalars(
            select(models.CustomerLedgerEntry)
            .where(models.CustomerLedgerEntry.customer_id == customer.id)
            .order_by(models.CustomerLedgerEntry.created_at.desc())
            .limit(20)
        )
    )
    recent_activity = [
        schemas.CustomerLedgerEntryResponse.model_validate(
            {
                "id": entry.id,
                "entry_type": entry.entry_type,
                "reference_type": entry.reference_type,
                "reference_id": entry.reference_id,
                "amount": entry.amount,
                "balance_after": entry.balance_after,
                "note": entry.note,
                "details": entry.details,
                "created_at": entry.created_at,
                "created_by": _user_display_name(entry.created_by),
            }
        )
        for entry in recent_entries
    ]

    summary = schemas.AccountsReceivableSummary(
        total_outstanding=float(outstanding_total),
        available_credit=float(available_credit),
        credit_limit=float(credit_limit),
        last_payment_at=last_payment_at,
        next_due_date=next_due_date,
        average_days_outstanding=average_days,
        contact_email=customer.email,
        contact_phone=customer.phone,
    )

    customer_schema = schemas.CustomerResponse.model_validate(customer)
    generated_at = datetime.utcnow()
    return schemas.CustomerAccountsReceivableResponse(
        customer=customer_schema,
        summary=summary,
        aging=aging,
        open_entries=sorted(
            open_entries,
            key=lambda item: (item.issued_at, item.ledger_entry_id),
        ),
        credit_schedule=schedule_entries,
        recent_activity=recent_activity,
        generated_at=generated_at,
    )


def build_customer_statement_report(
    db: Session, customer_id: int
) -> schemas.CustomerStatementReport:
    receivable = get_customer_accounts_receivable(db, customer_id)

    ledger_entries = list(
        db.scalars(
            select(models.CustomerLedgerEntry)
            .where(models.CustomerLedgerEntry.customer_id == customer_id)
            .order_by(
                models.CustomerLedgerEntry.created_at.asc(),
                models.CustomerLedgerEntry.id.asc(),
            )
        )
    )

    sale_ids: set[int] = set()
    for entry in ledger_entries:
        if entry.reference_type == "sale" and entry.reference_id and entry.reference_id.isdigit():
            sale_ids.add(int(entry.reference_id))
    sale_map, config_map = _resolve_sale_references(db, sale_ids)

    lines: list[schemas.CustomerStatementLine] = []
    for entry in ledger_entries:
        reference: str | None = None
        if entry.reference_type == "sale" and entry.reference_id and entry.reference_id.isdigit():
            reference = _format_sale_reference(int(entry.reference_id), sale_map, config_map)
        elif entry.reference_id:
            reference = (
                f"{entry.reference_type} #{entry.reference_id}"
                if entry.reference_type
                else entry.reference_id
            )
        amount_value = _to_decimal(entry.amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        balance_after = _to_decimal(entry.balance_after).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        lines.append(
            schemas.CustomerStatementLine(
                created_at=entry.created_at,
                description=_ledger_entry_label(entry),
                reference=reference,
                entry_type=entry.entry_type,
                amount=float(amount_value),
                balance_after=float(balance_after),
            )
        )

    return schemas.CustomerStatementReport(
        customer=receivable.customer,
        summary=receivable.summary,
        lines=lines,
        generated_at=datetime.utcnow(),
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
        statement = statement.where(
            func.date(models.Sale.created_at) >= date_from)
    if date_to is not None:
        statement = statement.where(
            func.date(models.Sale.created_at) <= date_to)
    return statement.group_by(models.Sale.customer_id).subquery()


def build_customer_portfolio(
    db: Session,
    *,
    category: Literal["delinquent", "frequent"],
    limit: int = 50,
    offset: int = 0,
    date_from: date | None = None,
    date_to: date | None = None,
) -> schemas.CustomerPortfolioReport:
    sales_stats = _customer_sales_stats_subquery(
        date_from=date_from, date_to=date_to)
    base_statement = select(
        models.Customer,
        sales_stats.c.sales_count,
        sales_stats.c.sales_total,
        sales_stats.c.last_sale_at,
    )

    if category == "frequent":
        statement = (
            base_statement.join(
                sales_stats, sales_stats.c.customer_id == models.Customer.id)
            .order_by(desc(sales_stats.c.sales_total), models.Customer.name.asc())
            .offset(offset)
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
            .offset(offset)
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
            current_month = date(current_month.year,
                                 current_month.month - 1, 1)
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
        total_outstanding_debt=float(
            delinquent_row.total_outstanding_debt or 0),
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
    limit: int = 50,
    offset: int = 0,
) -> list[models.Supplier]:
    statement = (
        select(models.Supplier)
        .where(models.Supplier.is_deleted.is_(False))
        .order_by(models.Supplier.name.asc())
        .offset(offset)
        .limit(limit)
    )
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.Supplier.name).like(normalized),
                func.lower(models.Supplier.contact_name).like(normalized),
                func.lower(models.Supplier.email).like(normalized),
                func.lower(models.Supplier.phone).like(normalized),
                func.lower(models.Supplier.rtn).like(normalized),
                func.lower(models.Supplier.payment_terms).like(normalized),
                func.lower(models.Supplier.notes).like(normalized),
            )
        )
    return list(db.scalars(statement))


def get_supplier(db: Session, supplier_id: int) -> models.Supplier:
    statement = select(models.Supplier).where(
        models.Supplier.id == supplier_id,
        models.Supplier.is_deleted.is_(False),
    )
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
    normalized_rtn = None
    if payload.rtn:
        normalized_rtn = _normalize_rtn(payload.rtn, error_code="supplier_rtn_invalid")
    supplier = models.Supplier(
        name=payload.name,
        rtn=normalized_rtn,
        payment_terms=payload.payment_terms,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        contact_info=_contacts_to_json(payload.contact_info),
        address=payload.address,
        notes=payload.notes,
        history=history,
        outstanding_debt=_to_decimal(payload.outstanding_debt),
        products_supplied=_products_to_json(payload.products_supplied),
    )
    try:
        with transactional_session(db):
            db.add(supplier)
            flush_session(db)

            _log_action(
                db,
                action="supplier_created",
                entity_type="supplier",
                entity_id=str(supplier.id),
                performed_by_id=performed_by_id,
                details=json.dumps({"name": supplier.name}),
            )

            db.refresh(supplier)
    except IntegrityError as exc:
        raise ValueError("supplier_already_exists") from exc
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
    if payload.rtn is not None:
        supplier.rtn = (
            _normalize_rtn(payload.rtn, error_code="supplier_rtn_invalid")
            if payload.rtn
            else None
        )
        updated_fields["rtn"] = supplier.rtn
    if payload.payment_terms is not None:
        supplier.payment_terms = payload.payment_terms
        updated_fields["payment_terms"] = payload.payment_terms
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
    if payload.contact_info is not None:
        contacts = _contacts_to_json(payload.contact_info)
        supplier.contact_info = contacts
        updated_fields["contact_info"] = contacts
    if payload.products_supplied is not None:
        products = _products_to_json(payload.products_supplied)
        supplier.products_supplied = products
        updated_fields["products_supplied"] = products
    with transactional_session(db):
        db.add(supplier)
        flush_session(db)

        if updated_fields:
            _log_action(
                db,
                action="supplier_updated",
                entity_type="supplier",
                entity_id=str(supplier.id),
                performed_by_id=performed_by_id,
                details=json.dumps(updated_fields),
            )

        db.refresh(supplier)
    return supplier


def delete_supplier(
    db: Session,
    supplier_id: int,
    *,
    performed_by_id: int | None = None,
    allow_hard_delete: bool = False,
    is_superadmin: bool = False,
) -> None:
    supplier = get_supplier(db, supplier_id)
    has_dependencies = bool(supplier.batches or supplier.ledger_entries)
    should_hard_delete = allow_hard_delete and (not has_dependencies or is_superadmin)
    with transactional_session(db):
        if should_hard_delete:
            db.delete(supplier)

            _log_action(
                db,
                action="supplier_deleted",
                entity_type="supplier",
                entity_id=str(supplier_id),
                performed_by_id=performed_by_id,
            )
            return

        supplier.is_deleted = True
        supplier.deleted_at = datetime.utcnow()
        _log_action(
            db,
            action="supplier_archived",
            entity_type="supplier",
            entity_id=str(supplier_id),
            performed_by_id=performed_by_id,
        )


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
    limit: int | None = 50,
    offset: int = 0,
) -> list[schemas.PurchaseVendorResponse]:
    statement = (
        select(
            models.Proveedor,
            func.coalesce(func.sum(models.Compra.total),
                          0).label("total_compras"),
            func.coalesce(func.sum(models.Compra.impuesto),
                          0).label("total_impuesto"),
            func.count(models.Compra.id_compra).label("compras_registradas"),
            func.max(models.Compra.fecha).label("ultima_compra"),
        )
        .outerjoin(models.Compra, models.Compra.proveedor_id == models.Proveedor.id_proveedor)
        .group_by(models.Proveedor.id_proveedor)
        .order_by(models.Proveedor.nombre.asc())
    )
    if vendor_id is not None:
        statement = statement.where(models.Proveedor.id_proveedor == vendor_id)
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(func.lower(
            models.Proveedor.nombre).like(normalized))
    if estado:
        statement = statement.where(func.lower(
            models.Proveedor.estado) == estado.lower())
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)

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


def count_purchase_vendors(
    db: Session,
    *,
    vendor_id: int | None = None,
    query: str | None = None,
    estado: str | None = None,
) -> int:
    statement = select(func.count()).select_from(models.Proveedor)
    if vendor_id is not None:
        statement = statement.where(models.Proveedor.id_proveedor == vendor_id)
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(func.lower(
            models.Proveedor.nombre).like(normalized))
    if estado:
        statement = statement.where(func.lower(
            models.Proveedor.estado) == estado.lower())
    return int(db.scalar(statement) or 0)


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
    with transactional_session(db):
        db.add(vendor)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("purchase_vendor_duplicate") from exc

        _log_action(
            db,
            action="purchase_vendor_created",
            entity_type="purchase_vendor",
            entity_id=str(vendor.id_proveedor),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {"nombre": vendor.nombre, "estado": vendor.estado}),
        )
        flush_session(db)
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
    with transactional_session(db):
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

        if updated_fields:
            _log_action(
                db,
                action="purchase_vendor_updated",
                entity_type="purchase_vendor",
                entity_id=str(vendor.id_proveedor),
                performed_by_id=performed_by_id,
                details=json.dumps(updated_fields),
            )
        flush_session(db)
        db.refresh(vendor)
    return vendor


def compute_purchase_suggestions(
    db: Session,
    *,
    store_ids: Sequence[int] | None = None,
    lookback_days: int = 30,
    minimum_stock: int | None = None,
    planning_horizon_days: int = 14,
) -> schemas.PurchaseSuggestionsResponse:
    """Calcula sugerencias de compra agrupadas por sucursal."""

    normalized_lookback = max(int(lookback_days or 30), 7)
    normalized_horizon = max(int(planning_horizon_days or 14), 7)
    settings_alerts = inventory_alert_settings
    threshold = settings_alerts.clamp_threshold(minimum_stock)

    since = datetime.utcnow() - timedelta(days=normalized_lookback)

    device_stmt = (
        select(
            models.Device.id,
            models.Device.store_id,
            models.Store.name.label("store_name"),
            models.Device.sku,
            models.Device.name,
            models.Device.quantity,
            models.Device.proveedor,
            models.Device.costo_unitario,
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
        .order_by(models.Store.name.asc(), models.Device.name.asc())
    )
    if store_ids:
        device_stmt = device_stmt.where(models.Device.store_id.in_(store_ids))

    device_rows = list(db.execute(device_stmt))
    if not device_rows:
        return schemas.PurchaseSuggestionsResponse(
            generated_at=datetime.utcnow(),
            lookback_days=normalized_lookback,
            planning_horizon_days=normalized_horizon,
            minimum_stock=threshold,
            total_items=0,
            stores=[],
        )

    device_ids = [int(row.id) for row in device_rows]

    sales_stmt = (
        select(
            models.SaleItem.device_id,
            func.sum(models.SaleItem.quantity).label("sold_units"),
            func.min(models.Sale.created_at).label("first_sale"),
            func.max(models.Sale.created_at).label("last_sale"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .where(models.SaleItem.device_id.in_(device_ids))
        .where(func.upper(models.Sale.status) != "CANCELADA")
        .group_by(models.SaleItem.device_id)
    )
    if store_ids:
        sales_stmt = sales_stmt.where(models.Sale.store_id.in_(store_ids))
    sales_stmt = sales_stmt.where(models.Sale.created_at >= since)

    sales_map: dict[int, dict[str, object]] = {}
    for row in db.execute(sales_stmt):
        sold_units = int(row.sold_units or 0)
        first_sale = row.first_sale
        last_sale = row.last_sale
        span_days = normalized_lookback
        if first_sale and last_sale:
            first_dt = max(first_sale, since)
            span_days = max(
                1,
                min(
                    normalized_lookback,
                    (last_sale.date() - first_dt.date()).days + 1,
                ),
            )
        sales_map[int(row.device_id)] = {
            "sold_units": sold_units,
            "span_days": span_days,
        }

    supplier_candidates = {
        row.proveedor.strip().lower()
        for row in device_rows
        if getattr(row, "proveedor", None) and row.proveedor.strip()
    }
    vendor_map: dict[str, tuple[int, str]] = {}
    if supplier_candidates:
        vendor_stmt = (
            select(
                models.Proveedor.id_proveedor,
                models.Proveedor.nombre,
                func.lower(models.Proveedor.nombre).label("normalized"),
            )
            .where(func.lower(models.Proveedor.nombre).in_(tuple(supplier_candidates)))
            .order_by(models.Proveedor.nombre.asc())
        )
        for vendor in db.execute(vendor_stmt):
            vendor_map[vendor.normalized] = (
                int(vendor.id_proveedor),
                vendor.nombre,
            )

    stores_payload: dict[int, list[schemas.PurchaseSuggestionItem]] = defaultdict(list)
    store_value_totals: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    total_items = 0

    for row in device_rows:
        device_id = int(row.id)
        quantity = int(row.quantity or 0)
        unit_cost = _to_decimal(getattr(row, "costo_unitario", None) or Decimal("0"))
        supplier_name = (row.proveedor or "").strip() or None

        sales_info = sales_map.get(device_id)
        sold_units = int(sales_info["sold_units"]) if sales_info else 0
        span_days = int(sales_info["span_days"]) if sales_info else normalized_lookback
        average_daily = float(sold_units) / span_days if span_days > 0 else 0.0
        projected_coverage = (
            max(int(math.ceil(quantity / average_daily)), 0)
            if average_daily > 0
            else None
        )

        buffer_units = int(math.ceil(average_daily * normalized_horizon)) if average_daily > 0 else 0
        target_stock = max(threshold, buffer_units)
        if target_stock <= 0:
            continue
        if quantity >= target_stock:
            continue

        suggested_quantity = target_stock - quantity
        if suggested_quantity <= 0:
            continue

        reason = "below_minimum" if quantity <= threshold else "projected_consumption"

        supplier_id: int | None = None
        supplier_display = supplier_name
        if supplier_name:
            normalized_supplier = supplier_name.lower()
            vendor_entry = vendor_map.get(normalized_supplier)
            if vendor_entry:
                supplier_id, official_name = vendor_entry
                supplier_display = official_name

        item = schemas.PurchaseSuggestionItem(
            store_id=int(row.store_id),
            store_name=row.store_name,
            supplier_id=supplier_id,
            supplier_name=supplier_display,
            device_id=device_id,
            sku=row.sku,
            name=row.name,
            current_quantity=quantity,
            minimum_stock=threshold,
            suggested_quantity=suggested_quantity,
            average_daily_sales=round(average_daily, 2),
            projected_coverage_days=projected_coverage,
            last_30_days_sales=sold_units,
            unit_cost=unit_cost,
            reason=reason,
        )

        stores_payload[int(row.store_id)].append(item)
        store_value_totals[int(row.store_id)] += (
            unit_cost * Decimal(suggested_quantity)
        )
        total_items += 1

    stores: list[schemas.PurchaseSuggestionStore] = []
    for store_id, items in stores_payload.items():
        items.sort(key=lambda entry: (entry.suggested_quantity, entry.name), reverse=True)
        total_recommended = sum(item.suggested_quantity for item in items)
        total_value = float(store_value_totals[store_id])
        store_name = items[0].store_name if items else ""
        stores.append(
            schemas.PurchaseSuggestionStore(
                store_id=store_id,
                store_name=store_name,
                total_suggested=total_recommended,
                total_value=total_value,
                items=items,
            )
        )

    stores.sort(key=lambda store: (-store.total_value, store.store_name))

    return schemas.PurchaseSuggestionsResponse(
        generated_at=datetime.utcnow(),
        lookback_days=normalized_lookback,
        planning_horizon_days=normalized_horizon,
        minimum_stock=threshold,
        total_items=total_items,
        stores=stores,
    )


def set_purchase_vendor_status(
    db: Session,
    vendor_id: int,
    estado: str,
    *,
    performed_by_id: int | None = None,
) -> models.Proveedor:
    vendor = get_purchase_vendor(db, vendor_id)
    with transactional_session(db):
        vendor.estado = estado
        db.add(vendor)

        _log_action(
            db,
            action="purchase_vendor_status_updated",
            entity_type="purchase_vendor",
            entity_id=str(vendor.id_proveedor),
            performed_by_id=performed_by_id,
            details=json.dumps({"estado": estado}),
        )
        flush_session(db)
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
    db: Session, supplier_id: int, *, limit: int = 50, offset: int = 0
) -> list[models.SupplierBatch]:
    supplier = get_supplier(db, supplier_id)
    statement = (
        select(models.SupplierBatch)
        .where(models.SupplierBatch.supplier_id == supplier.id)
        .order_by(models.SupplierBatch.purchase_date.desc(), models.SupplierBatch.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).unique())


def get_supplier_batch_overview(
    db: Session,
    *,
    store_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    batch_filter = or_(
        models.SupplierBatch.store_id == store_id,
        models.SupplierBatch.store_id.is_(None),
    )

    latest_rank = func.row_number().over(
        partition_by=models.SupplierBatch.supplier_id,
        order_by=(
            models.SupplierBatch.purchase_date.desc(),
            models.SupplierBatch.created_at.desc(),
        ),
    )

    ranked_batches = (
        select(
            models.SupplierBatch.supplier_id.label("supplier_id"),
            models.SupplierBatch.batch_code.label("latest_batch_code"),
            models.SupplierBatch.unit_cost.label("latest_unit_cost"),
            latest_rank.label("batch_rank"),
        )
        .where(batch_filter)
    ).subquery()

    latest_batches = (
        select(
            ranked_batches.c.supplier_id,
            ranked_batches.c.latest_batch_code,
            ranked_batches.c.latest_unit_cost,
        )
        .where(ranked_batches.c.batch_rank == 1)
    ).subquery()

    aggregated = (
        select(
            models.SupplierBatch.supplier_id.label("supplier_id"),
            models.Supplier.name.label("supplier_name"),
            func.count().label("batch_count"),
            func.sum(models.SupplierBatch.quantity).label("total_quantity"),
            func.sum(
                models.SupplierBatch.quantity * models.SupplierBatch.unit_cost
            ).label("total_value"),
            func.max(models.SupplierBatch.purchase_date).label(
                "latest_purchase_date"
            ),
        )
        .join(models.Supplier, models.Supplier.id == models.SupplierBatch.supplier_id)
        .where(batch_filter)
        .group_by(models.SupplierBatch.supplier_id, models.Supplier.name)
    ).subquery()

    statement = (
        select(
            aggregated.c.supplier_id,
            aggregated.c.supplier_name,
            aggregated.c.batch_count,
            aggregated.c.total_quantity,
            aggregated.c.total_value,
            aggregated.c.latest_purchase_date,
            latest_batches.c.latest_batch_code,
            latest_batches.c.latest_unit_cost,
        )
        .join(
            latest_batches,
            latest_batches.c.supplier_id == aggregated.c.supplier_id,
            isouter=True,
        )
        .order_by(
            aggregated.c.latest_purchase_date.desc(),
            aggregated.c.total_value.desc(),
        )
    )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)

    rows = db.execute(statement).all()

    result: list[dict[str, object]] = []
    for row in rows:
        total_value = Decimal(row.total_value or 0).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        latest_unit_cost = row.latest_unit_cost
        result.append(
            {
                "supplier_id": row.supplier_id,
                "supplier_name": row.supplier_name,
                "batch_count": int(row.batch_count or 0),
                "total_quantity": int(row.total_quantity or 0),
                "total_value": float(total_value),
                "latest_purchase_date": row.latest_purchase_date,
                "latest_batch_code": row.latest_batch_code,
                "latest_unit_cost": float(latest_unit_cost)
                if latest_unit_cost is not None
                else None,
            }
        )

    return result


def count_supplier_batch_overview(db: Session, *, store_id: int) -> int:
    statement = (
        select(func.count(func.distinct(models.SupplierBatch.supplier_id)))
        .where(
            or_(
                models.SupplierBatch.store_id == store_id,
                models.SupplierBatch.store_id.is_(None),
            )
        )
    )
    total = db.scalar(statement)
    return int(total or 0)


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

    with transactional_session(db):
        batch = models.SupplierBatch(
            supplier_id=supplier.id,
            store_id=store.id if store else None,
            device_id=device.id if device else None,
            model_name=payload.model_name or (device.name if device else ""),
            batch_code=payload.batch_code,
            unit_cost=_to_decimal(payload.unit_cost).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP),
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

        flush_session(db)
        db.refresh(batch)

        if device is not None:
            _recalculate_store_inventory_value(db, device.store_id)

        _log_action(
            db,
            action="supplier_batch_created",
            entity_type="supplier_batch",
            entity_id=str(batch.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"supplier_id": supplier.id,
                               "batch_code": batch.batch_code}),
        )
        flush_session(db)
        db.refresh(batch)
    return batch


def update_supplier_batch(
    db: Session,
    batch_id: int,
    payload: schemas.SupplierBatchUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.SupplierBatch:
    statement = select(models.SupplierBatch).where(
        models.SupplierBatch.id == batch_id)
    batch = db.scalars(statement).first()
    if batch is None:
        raise LookupError("supplier_batch_not_found")

    updated_fields: dict[str, object] = {}

    with transactional_session(db):
        if payload.model_name is not None:
            batch.model_name = payload.model_name
            updated_fields["model_name"] = payload.model_name
        if payload.batch_code is not None:
            batch.batch_code = payload.batch_code
            updated_fields["batch_code"] = payload.batch_code
        if payload.unit_cost is not None:
            batch.unit_cost = _to_decimal(payload.unit_cost).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP)
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
        flush_session(db)
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
            flush_session(db)
            db.refresh(batch)
    return batch


def delete_supplier_batch(
    db: Session,
    batch_id: int,
    *,
    performed_by_id: int | None = None,
) -> None:
    statement = select(models.SupplierBatch).where(
        models.SupplierBatch.id == batch_id)
    batch = db.scalars(statement).first()
    if batch is None:
        raise LookupError("supplier_batch_not_found")
    store_id = batch.store_id
    with transactional_session(db):
        db.delete(batch)
        flush_session(db)
        if store_id:
            _recalculate_store_inventory_value(db, store_id)
        _log_action(
            db,
            action="supplier_batch_deleted",
            entity_type="supplier_batch",
            entity_id=str(batch_id),
            performed_by_id=performed_by_id,
        )
        flush_session(db)


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
        "RTN",
        "Términos de pago",
        "Contacto",
        "Cargo contacto",
        "Correo",
        "Teléfono",
        "Dirección",
        "Deuda",
        "Productos suministrados",
    ])
    for supplier in suppliers:
        contact_entry: Mapping[str, object] | None = None
        if supplier.contact_info:
            first_entry = supplier.contact_info[0]
            if isinstance(first_entry, Mapping):
                contact_entry = first_entry
        writer.writerow(
            [
                supplier.id,
                supplier.name,
                supplier.rtn or "",
                supplier.payment_terms or "",
                (contact_entry.get("name") if contact_entry else supplier.contact_name or ""),
                (contact_entry.get("position") if contact_entry else ""),
                supplier.email or "",
                supplier.phone or "",
                supplier.address or "",
                float(supplier.outstanding_debt),
                ", ".join(_products_to_json(supplier.products_supplied)),
            ]
        )
    return buffer.getvalue()


def get_suppliers_accounts_payable(
    db: Session,
) -> schemas.SupplierAccountsPayableResponse:
    suppliers = list(
        db.scalars(select(models.Supplier).order_by(models.Supplier.name.asc()))
    )

    bucket_defs: list[tuple[str, int, int | None]] = [
        ("0-30 días", 0, 30),
        ("31-60 días", 31, 60),
        ("61-90 días", 61, 90),
        ("90+ días", 91, None),
    ]
    bucket_totals: list[dict[str, object]] = [
        {"label": label, "from": start, "to": end, "amount": Decimal("0.00"), "count": 0}
        for label, start, end in bucket_defs
    ]

    total_balance = Decimal("0.00")
    total_overdue = Decimal("0.00")
    items: list[schemas.SupplierAccountsPayableSupplier] = []
    today = datetime.utcnow().date()

    for supplier in suppliers:
        balance = _to_decimal(supplier.outstanding_debt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        history = (
            supplier.history
            if isinstance(supplier.history, list)
            else []
        )
        last_history = _last_history_timestamp(history)
        last_activity = last_history or supplier.updated_at or supplier.created_at

        days_outstanding = 0
        if last_activity is not None:
            days_outstanding = max(
                (today - last_activity.date()).days,
                0,
            )

        bucket_index = 0
        for idx, (_, start, end) in enumerate(bucket_defs):
            if end is None or days_outstanding <= end:
                if end is None or days_outstanding >= start:
                    bucket_index = idx
                    break

        bucket = bucket_totals[bucket_index]
        bucket["amount"] = _to_decimal(bucket["amount"]) + balance  # type: ignore[index]
        if balance > Decimal("0"):
            bucket["count"] = int(bucket["count"]) + 1  # type: ignore[index]

        total_balance += balance
        if days_outstanding > 30:
            total_overdue += balance

        contact_name = supplier.contact_name
        contact_email = supplier.email
        contact_phone = supplier.phone
        sanitized_contacts = _contacts_to_json(
            supplier.contact_info
            if isinstance(supplier.contact_info, list)
            else []
        )
        if sanitized_contacts:
            primary = sanitized_contacts[0]
            if isinstance(primary, Mapping):
                contact_name = (primary.get("name") or contact_name) if contact_name else primary.get("name")
                contact_email = (
                    primary.get("email") or contact_email
                ) if contact_email else primary.get("email")
                contact_phone = (
                    primary.get("phone") or contact_phone
                ) if contact_phone else primary.get("phone")

        contact_schemas: list[schemas.SupplierContact] = []
        for entry in sanitized_contacts:
            try:
                contact_schemas.append(schemas.SupplierContact.model_validate(entry))
            except ValidationError:
                continue

        products = _products_to_json(
            supplier.products_supplied
            if isinstance(supplier.products_supplied, Sequence)
            else []
        )

        items.append(
            schemas.SupplierAccountsPayableSupplier(
                supplier_id=supplier.id,
                supplier_name=supplier.name,
                rtn=supplier.rtn,
                payment_terms=supplier.payment_terms,
                outstanding_debt=float(balance),
                bucket_label=bucket_defs[bucket_index][0],
                bucket_from=bucket_defs[bucket_index][1],
                bucket_to=bucket_defs[bucket_index][2],
                days_outstanding=days_outstanding,
                last_activity=last_activity,
                contact_name=contact_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                products_supplied=products,
                contact_info=contact_schemas,
            )
        )

    aging_buckets: list[schemas.SupplierAccountsPayableBucket] = []
    for bucket_data, (label, start, end) in zip(bucket_totals, bucket_defs):
        amount_decimal = _to_decimal(bucket_data["amount"])  # type: ignore[index]
        percentage = 0.0
        if total_balance > Decimal("0"):
            percentage = float(
                (amount_decimal / total_balance * Decimal("100"))
                .quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            )
        aging_buckets.append(
            schemas.SupplierAccountsPayableBucket(
                label=label,
                days_from=start,
                days_to=end,
                amount=float(
                    amount_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                ),
                percentage=percentage,
                count=int(bucket_data["count"]),  # type: ignore[index]
            )
        )

    summary = schemas.SupplierAccountsPayableSummary(
        total_balance=float(total_balance.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        total_overdue=float(total_overdue.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        supplier_count=len(suppliers),
        generated_at=datetime.utcnow(),
        buckets=aging_buckets,
    )

    return schemas.SupplierAccountsPayableResponse(
        summary=summary,
        suppliers=sorted(
            items,
            key=lambda item: (item.bucket_from, -item.outstanding_debt, item.supplier_name.lower()),
        ),
    )


def get_store(db: Session, store_id: int) -> models.Store:
    statement = select(models.Store).where(models.Store.id == store_id)
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("store_not_found") from exc


def get_store_by_name(db: Session, name: str) -> models.Store | None:
    normalized = (name or "").strip()
    if not normalized:
        return None
    statement = select(models.Store).where(
        func.lower(models.Store.name) == normalized.lower()
    )
    return db.scalars(statement).first()


def ensure_store_by_name(
    db: Session, name: str, *, performed_by_id: int | None = None
) -> tuple[models.Store, bool]:
    existing = get_store_by_name(db, name)
    if existing is not None:
        return existing, False
    payload = schemas.StoreCreate(
        name=name.strip(),
        location=None,
        phone=None,
        manager=None,
        status="activa",
        timezone="UTC",
        code=None,
    )
    store = create_store(db, payload, performed_by_id=performed_by_id)
    return store, True


def create_device(
    db: Session,
    store_id: int,
    payload: schemas.DeviceCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Device:
    get_store(db, store_id)
    default_warehouse = _ensure_default_warehouse(db, store_id)
    payload_data = payload.model_dump()
    provided_fields = payload.model_fields_set
    imei = payload_data.get("imei")
    serial = payload_data.get("serial")
    _ensure_unique_identifiers(db, imei=imei, serial=serial)
    _validate_device_numeric_fields(payload_data)
    minimum_stock = int(payload_data.get("minimum_stock", 0) or 0)
    reorder_point = int(payload_data.get("reorder_point", 0) or 0)
    if reorder_point < minimum_stock:
        reorder_point = minimum_stock
        payload_data["reorder_point"] = reorder_point
    payload_data["minimum_stock"] = minimum_stock
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
        payload_data["fecha_ingreso"] = payload_data.get(
            "fecha_compra") or date.today()
    warehouse_id = payload_data.get("warehouse_id") or default_warehouse.id
    if warehouse_id is not None:
        warehouse = get_warehouse(db, warehouse_id, store_id=store_id)
        payload_data["warehouse_id"] = warehouse.id
    with transactional_session(db):
        device = models.Device(store_id=store_id, **payload_data)
        if unit_price is None:
            _recalculate_sale_price(device)
        else:
            device.unit_price = unit_price
            device.precio_venta = unit_price
        db.add(device)
        try:
            flush_session(db)
        except IntegrityError as exc:
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
        flush_session(db)
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
    statement = (
        select(models.Device)
        .options(
            joinedload(models.Device.identifier),
            selectinload(models.Device.variants),
        )
        .where(
            models.Device.id == device_id,
            models.Device.store_id == store_id,
        )
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("device_not_found") from exc


def get_device_global(db: Session, device_id: int) -> models.Device:
    statement = (
        select(models.Device)
        .options(
            joinedload(models.Device.identifier),
            selectinload(models.Device.variants),
        )
        .where(models.Device.id == device_id)
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("device_not_found") from exc


def list_product_variants(
    db: Session,
    *,
    store_id: int | None = None,
    device_id: int | None = None,
    include_inactive: bool = False,
) -> list[models.ProductVariant]:
    statement = (
        select(models.ProductVariant)
        .options(joinedload(models.ProductVariant.device))
        .order_by(models.ProductVariant.variant_sku.asc())
    )
    if device_id is not None:
        statement = statement.where(models.ProductVariant.device_id == device_id)
    if store_id is not None:
        statement = statement.join(models.ProductVariant.device).where(
            models.Device.store_id == store_id
        )
    if not include_inactive:
        statement = statement.where(models.ProductVariant.is_active.is_(True))
    return list(db.scalars(statement).unique())


def get_product_variant(db: Session, variant_id: int) -> models.ProductVariant:
    statement = (
        select(models.ProductVariant)
        .options(joinedload(models.ProductVariant.device))
        .where(models.ProductVariant.id == variant_id)
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("product_variant_not_found") from exc


def _unset_default_variant(db: Session, device_id: int, keep_id: int | None = None) -> None:
    query = db.query(models.ProductVariant).filter(
        models.ProductVariant.device_id == device_id
    )
    if keep_id is not None:
        query = query.filter(models.ProductVariant.id != keep_id)
    query.update({"is_default": False}, synchronize_session=False)


def create_product_variant(
    db: Session,
    device_id: int,
    payload: schemas.ProductVariantCreate,
    *,
    performed_by_id: int | None = None,
) -> models.ProductVariant:
    device = get_device_global(db, device_id)
    payload_data = payload.model_dump()
    if payload_data.get("unit_price_override") is not None:
        payload_data["unit_price_override"] = _to_decimal(
            payload_data["unit_price_override"]
        )
    with transactional_session(db):
        variant = models.ProductVariant(device_id=device.id, **payload_data)
        db.add(variant)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("product_variant_conflict") from exc
        if variant.is_default:
            _unset_default_variant(db, device.id, keep_id=variant.id)
        variant.device = device
        db.refresh(variant)

        _log_action(
            db,
            action="product_variant_created",
            entity_type="product_variant",
            entity_id=str(variant.id),
            performed_by_id=performed_by_id,
            details=json.dumps({
                "device_id": device.id,
                "variant_sku": variant.variant_sku,
            }),
        )
        flush_session(db)
        db.refresh(variant)
    return variant


def update_product_variant(
    db: Session,
    variant_id: int,
    payload: schemas.ProductVariantUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.ProductVariant:
    variant = get_product_variant(db, variant_id)
    updates = payload.model_dump(exclude_unset=True)
    sanitized: dict[str, Any] = {}
    for field, value in updates.items():
        if field == "unit_price_override" and value is not None:
            sanitized[field] = _to_decimal(value)
        else:
            sanitized[field] = value
    if not sanitized:
        return variant

    with transactional_session(db):
        for field, value in sanitized.items():
            setattr(variant, field, value)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("product_variant_conflict") from exc
        if sanitized.get("is_default"):
            _unset_default_variant(db, variant.device_id, keep_id=variant.id)
        db.refresh(variant)

        _log_action(
            db,
            action="product_variant_updated",
            entity_type="product_variant",
            entity_id=str(variant.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"updated_fields": sorted(sanitized.keys())}),
        )
        flush_session(db)
        db.refresh(variant)
    return variant


def archive_product_variant(
    db: Session,
    variant_id: int,
    *,
    performed_by_id: int | None = None,
) -> models.ProductVariant:
    variant = get_product_variant(db, variant_id)
    if not variant.is_active:
        return variant
    with transactional_session(db):
        variant.is_active = False
        flush_session(db)
        db.refresh(variant)

        _log_action(
            db,
            action="product_variant_archived",
            entity_type="product_variant",
            entity_id=str(variant.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"device_id": variant.device_id}),
        )
        flush_session(db)
        db.refresh(variant)
    return variant


def list_product_bundles(
    db: Session,
    *,
    store_id: int | None = None,
    include_inactive: bool = False,
) -> list[models.ProductBundle]:
    statement = (
        select(models.ProductBundle)
        .options(
            joinedload(models.ProductBundle.store),
            selectinload(models.ProductBundle.items).joinedload(
                models.ProductBundleItem.device
            ),
            selectinload(models.ProductBundle.items).joinedload(
                models.ProductBundleItem.variant
            ),
        )
        .order_by(models.ProductBundle.bundle_sku.asc())
    )
    if store_id is not None:
        statement = statement.where(models.ProductBundle.store_id == store_id)
    if not include_inactive:
        statement = statement.where(models.ProductBundle.is_active.is_(True))
    return list(db.scalars(statement).unique())


def get_product_bundle(db: Session, bundle_id: int) -> models.ProductBundle:
    statement = (
        select(models.ProductBundle)
        .options(
            joinedload(models.ProductBundle.store),
            selectinload(models.ProductBundle.items).joinedload(
                models.ProductBundleItem.device
            ),
            selectinload(models.ProductBundle.items).joinedload(
                models.ProductBundleItem.variant
            ),
        )
        .where(models.ProductBundle.id == bundle_id)
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("product_bundle_not_found") from exc


def _build_bundle_item(
    db: Session,
    item: schemas.ProductBundleItemCreate,
    *,
    expected_store_id: int | None,
) -> models.ProductBundleItem:
    device = get_device_global(db, item.device_id)
    if expected_store_id is not None and device.store_id != expected_store_id:
        raise ValueError("bundle_device_store_mismatch")
    variant_id = item.variant_id
    if variant_id is not None:
        variant = get_product_variant(db, variant_id)
        if variant.device_id != device.id:
            raise ValueError("bundle_variant_device_mismatch")
    return models.ProductBundleItem(
        device=device,
        variant=variant if variant_id is not None else None,
        variant_id=variant_id,
        quantity=item.quantity,
    )


def _replace_bundle_items(
    db: Session,
    bundle: models.ProductBundle,
    items: Sequence[schemas.ProductBundleItemCreate],
    *,
    expected_store_id: int | None,
) -> None:
    bundle.items[:] = []
    for item in items:
        bundle.items.append(
            _build_bundle_item(db, item, expected_store_id=expected_store_id)
        )


def create_product_bundle(
    db: Session,
    payload: schemas.ProductBundleCreate,
    *,
    performed_by_id: int | None = None,
) -> models.ProductBundle:
    if not payload.items:
        raise ValueError("bundle_items_required")
    if payload.store_id is not None:
        get_store(db, payload.store_id)
    data = payload.model_dump(exclude={"items"})
    data["base_price"] = _to_decimal(data.get("base_price"))
    with transactional_session(db):
        bundle = models.ProductBundle(**data)
        db.add(bundle)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("product_bundle_conflict") from exc
        _replace_bundle_items(
            db,
            bundle,
            payload.items,
            expected_store_id=bundle.store_id,
        )
        flush_session(db)
        db.refresh(bundle)

        _log_action(
            db,
            action="product_bundle_created",
            entity_type="product_bundle",
            entity_id=str(bundle.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"bundle_sku": bundle.bundle_sku}),
        )
        flush_session(db)
        db.refresh(bundle)
    return bundle


def update_product_bundle(
    db: Session,
    bundle_id: int,
    payload: schemas.ProductBundleUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.ProductBundle:
    bundle = get_product_bundle(db, bundle_id)
    updates = payload.model_dump(exclude_unset=True, exclude={"items"})
    items = payload.items
    if "base_price" in updates and updates["base_price"] is not None:
        updates["base_price"] = _to_decimal(updates["base_price"])
    if not updates and items is None:
        return bundle

    with transactional_session(db):
        for field, value in updates.items():
            setattr(bundle, field, value)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("product_bundle_conflict") from exc
        target_store_id = bundle.store_id
        if items is not None:
            if not items:
                raise ValueError("bundle_items_required")
            _replace_bundle_items(
                db,
                bundle,
                items,
                expected_store_id=target_store_id,
            )
        flush_session(db)
        db.refresh(bundle)

        changed_fields = sorted(list(updates.keys()) + (["items"] if items is not None else []))
        _log_action(
            db,
            action="product_bundle_updated",
            entity_type="product_bundle",
            entity_id=str(bundle.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"updated_fields": changed_fields}),
        )
        flush_session(db)
        db.refresh(bundle)
    return bundle


def archive_product_bundle(
    db: Session,
    bundle_id: int,
    *,
    performed_by_id: int | None = None,
) -> models.ProductBundle:
    bundle = get_product_bundle(db, bundle_id)
    if not bundle.is_active:
        return bundle
    with transactional_session(db):
        bundle.is_active = False
        flush_session(db)
        db.refresh(bundle)

        _log_action(
            db,
            action="product_bundle_archived",
            entity_type="product_bundle",
            entity_id=str(bundle.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"store_id": bundle.store_id}),
        )
        flush_session(db)
        db.refresh(bundle)
    return bundle


def list_price_lists(
    db: Session,
    *,
    store_id: int | None = None,
    customer_id: int | None = None,
    is_active: bool | None = None,
    include_items: bool = False,
    include_inactive: bool = True,
    include_global: bool = True,
) -> list[models.PriceList]:
    statement = (
        select(models.PriceList)
        .where(models.PriceList.is_deleted.is_(False))
        .order_by(models.PriceList.priority.asc(), models.PriceList.id.asc())
    )
    if include_items:
        statement = statement.options(joinedload(models.PriceList.items))
    if is_active is not None:
        statement = statement.where(models.PriceList.is_active.is_(is_active))
    elif not include_inactive:
        statement = statement.where(models.PriceList.is_active.is_(True))
    if store_id is not None:
        if include_global:
            statement = statement.where(
                or_(
                    models.PriceList.store_id == store_id,
                    models.PriceList.store_id.is_(None),
                )
            )
        else:
            statement = statement.where(models.PriceList.store_id == store_id)
    elif not include_global:
        statement = statement.where(models.PriceList.store_id.isnot(None))
    if customer_id is not None:
        if include_global:
            statement = statement.where(
                or_(
                    models.PriceList.customer_id == customer_id,
                    models.PriceList.customer_id.is_(None),
                )
            )
        else:
            statement = statement.where(models.PriceList.customer_id == customer_id)
    elif not include_global:
        statement = statement.where(models.PriceList.customer_id.isnot(None))
    results = db.scalars(statement)
    if include_items:
        results = results.unique()
    return list(results)


def get_price_list(
    db: Session,
    price_list_id: int,
    *,
    include_items: bool = False,
) -> models.PriceList:
    statement = select(models.PriceList).where(
        models.PriceList.id == price_list_id,
        models.PriceList.is_deleted.is_(False),
    )
    if include_items:
        statement = statement.options(joinedload(models.PriceList.items))
    result = db.scalars(statement)
    if include_items:
        result = result.unique()
    try:
        return result.one()
    except NoResultFound as exc:
        raise LookupError("price_list_not_found") from exc


def create_price_list(
    db: Session,
    payload: schemas.PriceListCreate,
    *,
    performed_by_id: int | None = None,
) -> models.PriceList:
    data = payload.model_dump()
    store_id = data.get("store_id")
    customer_id = data.get("customer_id")
    if store_id is not None:
        get_store(db, store_id)
    if customer_id is not None:
        get_customer(db, customer_id)
    with transactional_session(db):
        price_list = models.PriceList(**data)
        db.add(price_list)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("price_list_conflict") from exc
        db.refresh(price_list)
        _log_action(
            db,
            action="price_list_created",
            entity_type="price_list",
            entity_id=str(price_list.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"name": price_list.name}),
        )
        flush_session(db)
        db.refresh(price_list)
    return price_list


def update_price_list(
    db: Session,
    price_list_id: int,
    payload: schemas.PriceListUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.PriceList:
    price_list = get_price_list(db, price_list_id)
    updates = payload.model_dump(exclude_unset=True)
    sanitized_updates: dict[str, Any] = {}
    for field, value in updates.items():
        if field in {"name", "currency"} and value is None:
            continue
        sanitized_updates[field] = value
    if not sanitized_updates:
        return price_list
    if (
        "store_id" in sanitized_updates
        and sanitized_updates["store_id"] is not None
        and sanitized_updates["store_id"] != price_list.store_id
    ):
        get_store(db, sanitized_updates["store_id"])
    if (
        "customer_id" in sanitized_updates
        and sanitized_updates["customer_id"] is not None
        and sanitized_updates["customer_id"] != price_list.customer_id
    ):
        get_customer(db, sanitized_updates["customer_id"])
    with transactional_session(db):
        for field, value in sanitized_updates.items():
            setattr(price_list, field, value)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("price_list_conflict") from exc
        db.refresh(price_list)
        _log_action(
            db,
            action="price_list_updated",
            entity_type="price_list",
            entity_id=str(price_list.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"updated_fields": sorted(sanitized_updates.keys())}),
        )
        flush_session(db)
        db.refresh(price_list)
    return price_list


def delete_price_list(
    db: Session,
    price_list_id: int,
    *,
    performed_by_id: int | None = None,
    allow_hard_delete: bool = False,
    is_superadmin: bool = False,
) -> None:
    price_list = get_price_list(db, price_list_id)
    name = price_list.name
    has_dependencies = bool(price_list.items)
    should_hard_delete = allow_hard_delete and (not has_dependencies or is_superadmin)
    with transactional_session(db):
        if should_hard_delete:
            db.delete(price_list)
            flush_session(db)
            _log_action(
                db,
                action="price_list_deleted",
                entity_type="price_list",
                entity_id=str(price_list_id),
                performed_by_id=performed_by_id,
                details=json.dumps({"name": name}),
            )
            flush_session(db)
            return

        price_list.is_active = False
        price_list.is_deleted = True
        price_list.deleted_at = datetime.utcnow()
        flush_session(db)
        _log_action(
            db,
            action="price_list_archived",
            entity_type="price_list",
            entity_id=str(price_list_id),
            performed_by_id=performed_by_id,
            details=json.dumps({"name": name}),
        )
        flush_session(db)


def get_price_list_item(db: Session, item_id: int) -> models.PriceListItem:
    statement = select(models.PriceListItem).where(
        models.PriceListItem.id == item_id,
        models.PriceListItem.is_deleted.is_(False),
    )
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("price_list_item_not_found") from exc


def create_price_list_item(
    db: Session,
    price_list_id: int,
    payload: schemas.PriceListItemCreate,
    *,
    performed_by_id: int | None = None,
) -> models.PriceListItem:
    price_list = get_price_list(db, price_list_id)
    device = get_device_global(db, payload.device_id)
    if price_list.store_id is not None and device.store_id != price_list.store_id:
        raise ValueError("price_list_item_invalid_store")
    price = _ensure_positive_decimal(payload.price, "price_list_item_price_invalid")
    discount = _ensure_discount_percentage(
        payload.discount_percentage, "price_list_item_discount_invalid"
    )
    with transactional_session(db):
        item = models.PriceListItem(
            price_list_id=price_list.id,
            device_id=device.id,
            price=price,
            discount_percentage=discount,
            currency=payload.currency,
            notes=payload.notes,
        )
        db.add(item)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("price_list_item_conflict") from exc
        db.refresh(item)
        _log_action(
            db,
            action="price_list_item_created",
            entity_type="price_list_item",
            entity_id=str(item.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "price_list_id": price_list.id,
                    "device_id": device.id,
                }
            ),
        )
        flush_session(db)
        db.refresh(item)
    return item


def update_price_list_item(
    db: Session,
    item_id: int,
    payload: schemas.PriceListItemUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.PriceListItem:
    item = get_price_list_item(db, item_id)
    updates = payload.model_dump(exclude_unset=True)
    if "price" in updates and updates["price"] is not None:
        updates["price"] = _ensure_positive_decimal(
            updates["price"], "price_list_item_price_invalid"
        )
    if "discount_percentage" in updates:
        updates["discount_percentage"] = _ensure_discount_percentage(
            updates["discount_percentage"], "price_list_item_discount_invalid"
        )
    if not updates:
        return item
    with transactional_session(db):
        for field, value in updates.items():
            setattr(item, field, value)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("price_list_item_conflict") from exc
        db.refresh(item)
        _log_action(
            db,
            action="price_list_item_updated",
            entity_type="price_list_item",
            entity_id=str(item.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "price_list_id": item.price_list_id,
                    "device_id": item.device_id,
                    "updated_fields": sorted(updates.keys()),
                }
            ),
        )
        flush_session(db)
        db.refresh(item)
    return item


def delete_price_list_item(
    db: Session,
    item_id: int,
    *,
    performed_by_id: int | None = None,
    allow_hard_delete: bool = False,
    is_superadmin: bool = False,
) -> None:
    item = get_price_list_item(db, item_id)
    should_hard_delete = allow_hard_delete or is_superadmin
    with transactional_session(db):
        if should_hard_delete:
            db.delete(item)
            flush_session(db)
            _log_action(
                db,
                action="price_list_item_deleted",
                entity_type="price_list_item",
                entity_id=str(item_id),
                performed_by_id=performed_by_id,
                details=json.dumps(
                    {
                        "price_list_id": item.price_list_id,
                        "device_id": item.device_id,
                    }
                ),
            )
            flush_session(db)
            return

        item.is_deleted = True
        item.deleted_at = datetime.utcnow()
        flush_session(db)
        _log_action(
            db,
            action="price_list_item_archived",
            entity_type="price_list_item",
            entity_id=str(item_id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "price_list_id": item.price_list_id,
                    "device_id": item.device_id,
                }
            ),
        )
        flush_session(db)


def resolve_price_for_device(
    db: Session,
    *,
    device_id: int,
    store_id: int | None = None,
    customer_id: int | None = None,
    reference_date: date | None = None,
) -> tuple[models.PriceList, models.PriceListItem] | None:
    get_device_global(db, device_id)
    effective_date = reference_date or date.today()

    validity_condition = and_(
        or_(models.PriceList.valid_from.is_(None), models.PriceList.valid_from <= effective_date),
        or_(models.PriceList.valid_until.is_(None), models.PriceList.valid_until >= effective_date),
    )

    statement = (
        select(models.PriceListItem, models.PriceList)
        .join(models.PriceList, models.PriceListItem.price_list_id == models.PriceList.id)
        .where(models.PriceListItem.device_id == device_id)
        .where(models.PriceListItem.is_deleted.is_(False))
        .where(models.PriceList.is_active.is_(True))
        .where(models.PriceList.is_deleted.is_(False))
        .where(validity_condition)
    )

    results = db.execute(statement).all()

    def _priority(price_list: models.PriceList) -> int:
        if (
            store_id is not None
            and customer_id is not None
            and price_list.store_id == store_id
            and price_list.customer_id == customer_id
        ):
            return 1
        if (
            customer_id is not None
            and price_list.customer_id == customer_id
            and price_list.store_id is None
        ):
            return 2
        if (
            store_id is not None
            and price_list.store_id == store_id
            and price_list.customer_id is None
        ):
            return 3
        if price_list.store_id is None and price_list.customer_id is None:
            return 4
        return 99

    best_match: tuple[models.PriceList, models.PriceListItem] | None = None
    best_priority = 99
    for item, price_list in results:
        priority = _priority(price_list)
        if priority >= 99:
            continue
        if (
            best_match is None
            or priority < best_priority
            or (
                priority == best_priority
                and price_list.updated_at > best_match[0].updated_at
            )
        ):
            best_match = (price_list, item)
            best_priority = priority

    return best_match


# // [PACK34-lookup]
def resolve_device_for_pos(
    db: Session,
    *,
    store_id: int,
    device_id: int | None = None,
    imei: str | None = None,
) -> models.Device:
    if device_id:
        return get_device(db, store_id, device_id)
    if imei:
        normalized = imei.strip()
        if not normalized:
            raise LookupError("device_not_found")
        statement = select(models.Device).where(
            models.Device.store_id == store_id,
            func.lower(models.Device.imei) == normalized.lower(),
        )
        device = db.scalars(statement).first()
        if device is not None:
            return device
        identifier_stmt = (
            select(models.Device)
            .join(models.DeviceIdentifier)
            .where(models.Device.store_id == store_id)
            .where(
                or_(
                    func.lower(
                        models.DeviceIdentifier.imei_1) == normalized.lower(),
                    func.lower(
                        models.DeviceIdentifier.imei_2) == normalized.lower(),
                )
            )
        )
        device = db.scalars(identifier_stmt).first()
        if device is not None:
            return device
    raise LookupError("device_not_found")


def resolve_device_for_inventory(
    db: Session,
    *,
    store_id: int,
    device_id: int | None = None,
    imei: str | None = None,
    serial: str | None = None,
) -> models.Device:
    """Localiza un dispositivo para recepciones o conteos cíclicos.

    Prioriza `device_id` explícito, luego IMEI (incluyendo identificadores
    secundarios) y finalmente serial, siempre acotado a la sucursal indicada.
    """

    if device_id:
        return get_device(db, store_id, device_id)

    normalized_imei = imei.strip() if imei else None
    if normalized_imei:
        try:
            return resolve_device_for_pos(
                db,
                store_id=store_id,
                device_id=None,
                imei=normalized_imei,
            )
        except LookupError:
            pass

    if serial:
        normalized_serial = serial.strip()
    else:
        normalized_serial = None

    if normalized_serial:
        statement = select(models.Device).where(
            models.Device.store_id == store_id,
            func.lower(models.Device.serial) == normalized_serial.lower(),
        )
        device = db.scalars(statement).first()
        if device is not None:
            return device

        identifier_stmt = (
            select(models.Device)
            .join(models.DeviceIdentifier)
            .where(models.Device.store_id == store_id)
            .where(
                func.lower(models.DeviceIdentifier.numero_serie)
                == normalized_serial.lower()
            )
        )
        device = db.scalars(identifier_stmt).first()
        if device is not None:
            return device

    raise LookupError("device_not_found")


def find_device_for_import(
    db: Session,
    *,
    store_id: int,
    imei: str | None = None,
    serial: str | None = None,
    modelo: str | None = None,
    color: str | None = None,
) -> models.Device | None:
    if imei:
        statement = select(models.Device).where(
            func.lower(models.Device.imei) == imei.lower()
        )
        device = db.scalars(statement).first()
        if device is not None:
            return device
    if serial:
        statement = select(models.Device).where(
            func.lower(models.Device.serial) == serial.lower()
        )
        device = db.scalars(statement).first()
        if device is not None:
            return device
    if modelo and color:
        statement = (
            select(models.Device)
            .where(models.Device.store_id == store_id)
            .where(func.lower(models.Device.modelo) == modelo.lower())
            .where(func.lower(models.Device.color) == color.lower())
        )
        return db.scalars(statement).first()
    return None


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
    _validate_device_numeric_fields(updated_fields)
    new_minimum_stock = updated_fields.get("minimum_stock")
    new_reorder_point = updated_fields.get("reorder_point")
    current_minimum = int(getattr(device, "minimum_stock", 0) or 0)
    current_reorder = int(getattr(device, "reorder_point", 0) or 0)
    if "warehouse_id" in updated_fields:
        target_warehouse = updated_fields.get("warehouse_id")
        if target_warehouse is not None:
            warehouse = get_warehouse(db, int(target_warehouse), store_id=store_id)
            updated_fields["warehouse_id"] = warehouse.id
        else:
            updated_fields["warehouse_id"] = None
    if new_reorder_point is not None:
        target_min = new_minimum_stock if new_minimum_stock is not None else current_minimum
        if int(new_reorder_point) < int(target_min):
            raise ValueError("reorder_point_below_minimum")
    if new_minimum_stock is not None:
        target_reorder = new_reorder_point if new_reorder_point is not None else current_reorder
        if int(target_reorder) < int(new_minimum_stock):
            updated_fields["reorder_point"] = int(new_minimum_stock)
    if new_minimum_stock is not None:
        updated_fields["minimum_stock"] = int(new_minimum_stock)
    if new_reorder_point is not None:
        updated_fields["reorder_point"] = int(updated_fields["reorder_point"])

    sensitive_before = {
        "costo_unitario": device.costo_unitario,
        "estado_comercial": device.estado_comercial,
        "proveedor": device.proveedor,
    }

    with transactional_session(db):
        for key, value in updated_fields.items():
            setattr(device, key, value)
        if manual_price is not None:
            device.unit_price = manual_price
            device.precio_venta = manual_price
        elif {"costo_unitario", "margen_porcentaje"}.intersection(updated_fields):
            _recalculate_sale_price(device)
        flush_session(db)
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
                key: {"before": str(
                    sensitive_before[key]), "after": str(value)}
                for key, value in sensitive_after.items()
                if sensitive_before.get(key) != value
            }
            _log_action(
                db,
                action="device_updated",
                entity_type="device",
                entity_id=str(device.id),
                performed_by_id=performed_by_id,
                details=json.dumps(
                    {"fields": fields_changed, "sensitive": sensitive_changes}),
            )
            flush_session(db)
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

    with transactional_session(db):
        identifier.imei_1 = imei_1
        identifier.imei_2 = imei_2
        identifier.numero_serie = numero_serie
        identifier.estado_tecnico = payload_data.get("estado_tecnico")
        identifier.observaciones = payload_data.get("observaciones")

        db.add(identifier)
        flush_session(db)
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
        flush_session(db)
        db.refresh(identifier)
    return identifier


def get_device_identifier(
    db: Session, store_id: int, device_id: int
) -> models.DeviceIdentifier:
    device = get_device(db, store_id, device_id)
    if device.identifier is None:
        raise LookupError("device_identifier_not_found")
    return device.identifier


# =====================
# WMS Bins (ligero)
# =====================
def create_wms_bin(
    db: Session,
    store_id: int,
    payload: schemas.WMSBinCreate,
    *,
    performed_by_id: int | None = None,
) -> models.WMSBin:
    get_store(db, store_id)
    data = payload.model_dump()
    # Normaliza código a mayúsculas sin espacios extremos
    code = (data.get("codigo") or data.get("code") or "").strip()
    if not code:
        raise ValueError("wms_bin_code_required")
    normalized_code = code.upper()
    statement = select(models.WMSBin).where(
        models.WMSBin.store_id == store_id,
        func.upper(models.WMSBin.code) == normalized_code,
    )
    if db.scalars(statement).first() is not None:
        raise ValueError("wms_bin_duplicate")
    bin_obj = models.WMSBin(
        store_id=store_id,
        code=normalized_code,
        aisle=data.get("pasillo") or data.get("aisle"),
        rack=data.get("rack"),
        level=data.get("nivel") or data.get("level"),
        description=data.get("descripcion") or data.get("description"),
    )
    with transactional_session(db):
        db.add(bin_obj)
        flush_session(db)
        db.refresh(bin_obj)
        _log_action(
            db,
            action="wms_bin_created",
            entity_type="wms_bin",
            entity_id=str(bin_obj.id),
            performed_by_id=performed_by_id,
            details=f"SUCURSAL={store_id}, CODIGO={normalized_code}",
        )
    return bin_obj


def list_wms_bins(
    db: Session,
    store_id: int,
    *,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.WMSBin]:
    get_store(db, store_id)
    statement = (
        select(models.WMSBin)
        .where(models.WMSBin.store_id == store_id)
        .order_by(models.WMSBin.code.asc())
    )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement))


def update_wms_bin(
    db: Session,
    store_id: int,
    bin_id: int,
    payload: schemas.WMSBinUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.WMSBin:
    get_store(db, store_id)
    bin_obj = db.get(models.WMSBin, bin_id)
    if bin_obj is None or bin_obj.store_id != store_id:
        raise LookupError("wms_bin_not_found")
    data = payload.model_dump(exclude_none=True)
    changed_fields: list[str] = []
    with transactional_session(db):
        if "codigo" in data or "code" in data:
            new_code = (data.get("codigo") or data.get(
                "code") or "").strip().upper()
            if not new_code:
                raise ValueError("wms_bin_code_required")
            exists = db.scalars(
                select(models.WMSBin)
                .where(models.WMSBin.store_id == store_id)
                .where(func.upper(models.WMSBin.code) == new_code)
                .where(models.WMSBin.id != bin_id)
            ).first()
            if exists is not None:
                raise ValueError("wms_bin_duplicate")
            bin_obj.code = new_code
            changed_fields.append("codigo")
        if "pasillo" in data or "aisle" in data:
            bin_obj.aisle = data.get("pasillo") or data.get("aisle")
            changed_fields.append("pasillo")
        if "rack" in data:
            bin_obj.rack = data.get("rack")
            changed_fields.append("rack")
        if "nivel" in data or "level" in data:
            bin_obj.level = data.get("nivel") or data.get("level")
            changed_fields.append("nivel")
        if "descripcion" in data or "description" in data:
            bin_obj.description = data.get(
                "descripcion") or data.get("description")
            changed_fields.append("descripcion")
        db.add(bin_obj)
        flush_session(db)
        db.refresh(bin_obj)
        if changed_fields:
            _log_action(
                db,
                action="wms_bin_updated",
                entity_type="wms_bin",
                entity_id=str(bin_obj.id),
                performed_by_id=performed_by_id,
                details=json.dumps(
                    {"fields": changed_fields}, ensure_ascii=False),
            )
    return bin_obj


def _unset_default_warehouse(db: Session, store_id: int, keep_id: int | None = None) -> None:
    query = db.query(models.Warehouse).filter(models.Warehouse.store_id == store_id)
    if keep_id is not None:
        query = query.filter(models.Warehouse.id != keep_id)
    query.update({"is_default": False}, synchronize_session=False)


def _ensure_default_warehouse(db: Session, store_id: int) -> models.Warehouse:
    existing_default = db.scalars(
        select(models.Warehouse)
        .where(models.Warehouse.store_id == store_id)
        .where(models.Warehouse.is_default.is_(True))
    ).first()
    if existing_default:
        return existing_default
    fallback = db.scalars(
        select(models.Warehouse)
        .where(models.Warehouse.store_id == store_id)
        .where(func.lower(models.Warehouse.name) == "default")
    ).first()
    if fallback:
        with transactional_session(db):
            _unset_default_warehouse(db, store_id, keep_id=fallback.id)
            fallback.is_default = True
            db.add(fallback)
        return fallback
    code = f"DEF-{store_id}"
    warehouse = models.Warehouse(
        store_id=store_id,
        name="Default",
        code=code,
        is_default=True,
    )
    with transactional_session(db):
        db.add(warehouse)
        flush_session(db)
    return warehouse


def list_warehouses(
    db: Session, store_id: int, *, include_inactive_default: bool = True
) -> list[models.Warehouse]:
    get_store(db, store_id)
    statement = (
        select(models.Warehouse)
        .where(models.Warehouse.store_id == store_id)
        .order_by(models.Warehouse.is_default.desc(), models.Warehouse.name.asc())
    )
    warehouses = list(db.scalars(statement))
    if warehouses:
        return warehouses
    default = _ensure_default_warehouse(db, store_id)
    return [default]


def get_warehouse(
    db: Session, warehouse_id: int, *, store_id: int | None = None
) -> models.Warehouse:
    warehouse = db.get(models.Warehouse, warehouse_id)
    if warehouse is None:
        raise LookupError("warehouse_not_found")
    if store_id is not None and warehouse.store_id != store_id:
        raise LookupError("warehouse_not_found")
    return warehouse


def create_warehouse(
    db: Session,
    store_id: int,
    payload: schemas.WarehouseCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Warehouse:
    store = get_store(db, store_id)
    data = payload.model_dump()
    name = data.get("name", "").strip()
    code = (data.get("code", "").strip() or name).upper()
    desired_default = bool(data.get("is_default"))
    if not name:
        raise ValueError("warehouse_name_required")
    if not code:
        raise ValueError("warehouse_code_required")
    existing = db.scalars(
        select(models.Warehouse)
        .where(models.Warehouse.store_id == store_id)
        .where(func.upper(models.Warehouse.code) == code.upper())
    ).first()
    if existing:
        raise ValueError("warehouse_code_duplicate")
    duplicate_name = db.scalars(
        select(models.Warehouse)
        .where(models.Warehouse.store_id == store_id)
        .where(func.lower(models.Warehouse.name) == name.lower())
    ).first()
    if duplicate_name:
        raise ValueError("warehouse_name_duplicate")

    with transactional_session(db):
        if desired_default:
            _unset_default_warehouse(db, store_id)
        warehouse = models.Warehouse(
            store_id=store.id,
            name=name,
            code=code,
            is_default=desired_default,
        )
        db.add(warehouse)
        flush_session(db)
        db.refresh(warehouse)
        _log_action(
            db,
            action="warehouse_created",
            entity_type="warehouse",
            entity_id=str(warehouse.id),
            performed_by_id=performed_by_id,
            details=f"SUCURSAL={store_id}, CODIGO={code}",
        )
    return warehouse


def assign_device_to_bin(
    db: Session,
    store_id: int,
    *,
    device_id: int,
    bin_id: int,
    performed_by_id: int | None,
    reason: str | None = None,
) -> models.DeviceBinAssignment:
    device = get_device(db, store_id, device_id)
    bin_obj = db.get(models.WMSBin, bin_id)
    if bin_obj is None or bin_obj.store_id != store_id:
        raise LookupError("wms_bin_not_found")
    with transactional_session(db):
        # Desactivar asignación previa activa si existe
        prev_stmt = (
            select(models.DeviceBinAssignment)
            .where(models.DeviceBinAssignment.device_id == device.id)
            .where(models.DeviceBinAssignment.active.is_(True))
        )
        prev = db.scalars(prev_stmt).first()
        moved = False
        if prev is not None:
            if prev.bin_id == bin_obj.id:
                # Ya asignado al mismo bin, no duplicar
                return prev
            prev.active = False
            prev.unassigned_at = datetime.utcnow()
            db.add(prev)
            moved = True

        assignment = models.DeviceBinAssignment(
            device_id=device.id,
            bin_id=bin_obj.id,
            active=True,
            assigned_at=datetime.utcnow(),
        )
        db.add(assignment)
        flush_session(db)
        db.refresh(assignment)

        action = "device_bin_moved" if moved else "device_bin_assigned"
        details = f"DEVICE={device.id}, BIN={bin_obj.code}, STORE={store_id}"
        if reason:
            details = f"{details}, MOTIVO={reason.strip()}"
        _log_action(
            db,
            action=action,
            entity_type="device",
            entity_id=str(device.id),
            performed_by_id=performed_by_id,
            details=details,
        )
    return assignment


def get_device_current_bin(db: Session, store_id: int, device_id: int) -> models.WMSBin | None:
    device = get_device(db, store_id, device_id)
    stmt = (
        select(models.WMSBin)
        .join(models.DeviceBinAssignment, models.DeviceBinAssignment.bin_id == models.WMSBin.id)
        .where(models.DeviceBinAssignment.device_id == device.id)
        .where(models.DeviceBinAssignment.active.is_(True))
    )
    return db.scalars(stmt).first()


def list_devices_in_bin(
    db: Session,
    store_id: int,
    bin_id: int,
    *,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.Device]:
    bin_obj = db.get(models.WMSBin, bin_id)
    if bin_obj is None or bin_obj.store_id != store_id:
        raise LookupError("wms_bin_not_found")
    stmt = (
        select(models.Device)
        .join(models.DeviceBinAssignment, models.DeviceBinAssignment.device_id == models.Device.id)
        .where(models.DeviceBinAssignment.bin_id == bin_id)
        .where(models.DeviceBinAssignment.active.is_(True))
        .order_by(models.Device.sku.asc())
    )
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


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
    warehouse_id: int | None = None,
    fecha_ingreso_desde: date | None = None,
    fecha_ingreso_hasta: date | None = None,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.Device]:
    get_store(db, store_id)
    statement = (
        select(models.Device)
        .options(
            joinedload(models.Device.identifier),
            selectinload(models.Device.variants),
            joinedload(models.Device.warehouse),
        )
        .where(models.Device.store_id == store_id)
    )
    if warehouse_id is not None:
        statement = statement.where(models.Device.warehouse_id == warehouse_id)
    if estado is not None:
        statement = statement.where(models.Device.estado_comercial == estado)
    if categoria:
        statement = statement.where(
            models.Device.categoria.ilike(f"%{categoria}%"))
    if condicion:
        statement = statement.where(
            models.Device.condicion.ilike(f"%{condicion}%"))
    if estado_inventario:
        statement = statement.where(
            models.Device.estado.ilike(f"%{estado_inventario}%"))
    if ubicacion:
        statement = statement.where(
            models.Device.ubicacion.ilike(f"%{ubicacion}%"))
    if proveedor:
        statement = statement.where(
            models.Device.proveedor.ilike(f"%{proveedor}%"))
    if fecha_ingreso_desde or fecha_ingreso_hasta:
        start, end = _normalize_date_range(
            fecha_ingreso_desde, fecha_ingreso_hasta)
        statement = statement.where(
            models.Device.fecha_ingreso >= start.date(
            ), models.Device.fecha_ingreso <= end.date()
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
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement))


def count_store_devices(
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
    warehouse_id: int | None = None,
    fecha_ingreso_desde: date | None = None,
    fecha_ingreso_hasta: date | None = None,
) -> int:
    get_store(db, store_id)
    statement = select(func.count()).select_from(models.Device)
    statement = statement.where(models.Device.store_id == store_id)
    if warehouse_id is not None:
        statement = statement.where(models.Device.warehouse_id == warehouse_id)
    if estado is not None:
        statement = statement.where(models.Device.estado_comercial == estado)
    if categoria:
        statement = statement.where(
            models.Device.categoria.ilike(f"%{categoria}%"))
    if condicion:
        statement = statement.where(
            models.Device.condicion.ilike(f"%{condicion}%"))
    if estado_inventario:
        statement = statement.where(
            models.Device.estado.ilike(f"%{estado_inventario}%"))
    if ubicacion:
        statement = statement.where(
            models.Device.ubicacion.ilike(f"%{ubicacion}%"))
    if proveedor:
        statement = statement.where(
            models.Device.proveedor.ilike(f"%{proveedor}%"))
    if fecha_ingreso_desde or fecha_ingreso_hasta:
        start, end = _normalize_date_range(
            fecha_ingreso_desde, fecha_ingreso_hasta)
        statement = statement.where(
            models.Device.fecha_ingreso >= start.date(
            ), models.Device.fecha_ingreso <= end.date()
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
    return int(db.scalar(statement) or 0)


def _apply_device_search_filters(
    statement: Select[tuple[models.Device]], filters: schemas.DeviceSearchFilters
) -> Select[tuple[models.Device]]:
    if filters.imei:
        statement = statement.where(models.Device.imei == filters.imei)
    if filters.serial:
        statement = statement.where(models.Device.serial == filters.serial)
    if filters.capacidad_gb is not None:
        statement = statement.where(
            models.Device.capacidad_gb == filters.capacidad_gb)
    if filters.color:
        statement = statement.where(
            models.Device.color.ilike(f"%{filters.color}%"))
    if filters.marca:
        statement = statement.where(
            models.Device.marca.ilike(f"%{filters.marca}%"))
    if filters.modelo:
        statement = statement.where(
            models.Device.modelo.ilike(f"%{filters.modelo}%"))
    if filters.categoria:
        statement = statement.where(
            models.Device.categoria.ilike(f"%{filters.categoria}%"))
    if filters.condicion:
        statement = statement.where(
            models.Device.condicion.ilike(f"%{filters.condicion}%"))
    if filters.estado_comercial is not None:
        statement = statement.where(
            models.Device.estado_comercial == filters.estado_comercial)
    if filters.estado:
        statement = statement.where(
            models.Device.estado.ilike(f"%{filters.estado}%"))
    if filters.ubicacion:
        statement = statement.where(
            models.Device.ubicacion.ilike(f"%{filters.ubicacion}%"))
    if filters.proveedor:
        statement = statement.where(
            models.Device.proveedor.ilike(f"%{filters.proveedor}%"))
    if filters.fecha_ingreso_desde or filters.fecha_ingreso_hasta:
        start, end = _normalize_date_range(
            filters.fecha_ingreso_desde, filters.fecha_ingreso_hasta
        )
        statement = statement.where(
            models.Device.fecha_ingreso >= start.date(),
            models.Device.fecha_ingreso <= end.date(),
        )
    return statement


def search_devices(
    db: Session,
    filters: schemas.DeviceSearchFilters,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[models.Device]:
    statement: Select[tuple[models.Device]] = (
        select(models.Device)
        .options(
            joinedload(models.Device.store),
            joinedload(models.Device.identifier),
        )
        .join(models.Store)
    )
    statement = _apply_device_search_filters(statement, filters)
    statement = statement.order_by(
        models.Device.store_id.asc(), models.Device.sku.asc())
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def count_devices_matching_filters(
    db: Session, filters: schemas.DeviceSearchFilters
) -> int:
    statement: Select[tuple[int]] = select(func.count()).select_from(models.Device).join(
        models.Store
    )
    statement = _apply_device_search_filters(statement, filters)
    return int(db.scalar(statement) or 0)


def list_incomplete_devices(
    db: Session,
    *,
    store_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[models.Device]:
    statement = (
        select(models.Device)
        .options(joinedload(models.Device.store))
        .where(models.Device.completo.is_(False))
        .order_by(models.Device.id.desc())
    )
    if store_id is not None:
        statement = statement.where(models.Device.store_id == store_id)
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def count_incomplete_devices(
    db: Session, *, store_id: int | None = None
) -> int:
    statement: Select[tuple[int]] = select(func.count()).select_from(models.Device).where(
        models.Device.completo.is_(False)
    )
    if store_id is not None:
        statement = statement.where(models.Device.store_id == store_id)
    return int(db.scalar(statement) or 0)


def _ensure_adjustment_authorized(db: Session, performed_by_id: int | None) -> None:
    if performed_by_id is None:
        # Permite ejecuciones automatizadas (importaciones, sincronizaciones) manteniendo
        # compatibilidad con flujos existentes donde no hay un usuario autenticado.
        return
    user = get_user(db, performed_by_id)
    role_names = {
        membership.role.name for membership in user.roles if membership.role}
    if not {ADMIN, GERENTE}.intersection(role_names):
        raise PermissionError("movement_adjust_requires_authorized_user")


def _normalize_movement_comment(comment: str | None) -> str:
    if comment is None:
        normalized = "Movimiento inventario"
    else:
        normalized = comment.strip() or "Movimiento inventario"
    if len(normalized) < 5:
        normalized = f"{normalized} Kardex".strip()
    if len(normalized) < 5:
        normalized = "Movimiento inventario"
    return normalized[:255]


def _record_inventory_movement_reference(
    db: Session,
    *,
    movement: models.InventoryMovement,
    reference_type: str | None,
    reference_id: str | None,
    performed_by_id: int | None,
) -> None:
    """Registra la relación del movimiento con su operación original."""

    if not reference_type or not reference_id or movement.id is None:
        return

    normalized_type = reference_type.strip().lower()
    normalized_id = str(reference_id).strip()
    if not normalized_type or not normalized_id:
        return

    if len(normalized_type) > 40:
        normalized_type = normalized_type[:40]
    if len(normalized_id) > 120:
        normalized_id = normalized_id[:120]

    details = json.dumps(
        {"reference_type": normalized_type, "reference_id": normalized_id}
    )
    _log_action(
        db,
        action="inventory_movement_reference",
        entity_type="inventory_movement",
        entity_id=str(movement.id),
        performed_by_id=performed_by_id,
        details=details,
    )
    setattr(movement, "reference_type", normalized_type)
    setattr(movement, "reference_id", normalized_id)


def _register_inventory_movement(
    db: Session,
    *,
    store_id: int,
    device_id: int,
    movement_type: models.MovementType,
    quantity: int,
    comment: str | None,
    performed_by_id: int | None,
    source_store_id: int | None = None,
    destination_store_id: int | None = None,
    source_warehouse_id: int | None = None,
    warehouse_id: int | None = None,
    unit_cost: Decimal | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> models.InventoryMovement:
    normalized_comment = _normalize_movement_comment(comment)
    movement_payload = schemas.MovementCreate(
        producto_id=device_id,
        tipo_movimiento=movement_type,
        cantidad=quantity,
        comentario=normalized_comment,
        sucursal_origen_id=source_store_id,
        sucursal_destino_id=destination_store_id,
        almacen_origen_id=source_warehouse_id,
        almacen_destino_id=warehouse_id,
        unit_cost=unit_cost,
    )
    return create_inventory_movement(
        db,
        store_id,
        movement_payload,
        performed_by_id=performed_by_id,
        reference_type=reference_type,
        reference_id=reference_id,
    )


def _lock_device_inventory_row(
    db: Session, *, store_id: int, device_id: int
) -> None:
    """Aplica un bloqueo de fila sobre el dispositivo antes de modificar stock."""

    db.execute(
        select(models.Device.id)
        .where(
            models.Device.id == device_id,
            models.Device.store_id == store_id,
        )
        .with_for_update()
    )


def create_inventory_movement(
    db: Session,
    store_id: int,
    payload: schemas.MovementCreate,
    *,
    performed_by_id: int | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> models.InventoryMovement:
    store = get_store(db, store_id)
    if (
        payload.sucursal_destino_id is not None
        and payload.sucursal_destino_id != store_id
    ):
        raise ValueError("invalid_destination_store")

    source_store_id = payload.sucursal_origen_id

    device = get_device(db, store_id, payload.producto_id)

    destination_warehouse_id = payload.almacen_destino_id or device.warehouse_id
    source_warehouse_id = payload.almacen_origen_id or device.warehouse_id
    if destination_warehouse_id is not None:
        get_warehouse(db, destination_warehouse_id, store_id=store_id)
    if source_warehouse_id is not None:
        get_warehouse(db, source_warehouse_id, store_id=source_store_id or store_id)

    if source_store_id is not None:
        get_store(db, source_store_id)

    if (
        reference_type is None
        and payload.tipo_movimiento == models.MovementType.ADJUST
        and device.id is not None
    ):
        reference_type = "manual_adjustment"
        reference_id = str(device.id)

    needs_decrement_lock = payload.tipo_movimiento == models.MovementType.OUT or (
        payload.tipo_movimiento == models.MovementType.ADJUST
        and device.quantity > payload.cantidad
    )

    with transactional_session(db):
        if needs_decrement_lock:
            _lock_device_inventory_row(
                db, store_id=store_id, device_id=device.id
            )
            db.refresh(device)

        previous_quantity = device.quantity
        previous_cost = _to_decimal(device.costo_unitario)
        previous_sale_price = device.unit_price

        if (
            payload.tipo_movimiento == models.MovementType.OUT
            and device.quantity < payload.cantidad
        ):
            raise ValueError("insufficient_stock")

        movement_unit_cost: Decimal | None = None
        stock_move_type: models.StockMoveType | None = None
        stock_move_quantity: Decimal | None = None
        stock_move_branch_id: int | None = None
        ledger_quantity: Decimal | None = None
        ledger_branch_id: int | None = None
        ledger_unit_cost: Decimal | None = None

        if payload.tipo_movimiento == models.MovementType.IN:
            if payload.unit_cost is not None:
                incoming_cost = _to_decimal(payload.unit_cost)
            elif previous_cost > Decimal("0"):
                incoming_cost = previous_cost
            elif device.unit_price is not None and device.unit_price > Decimal("0"):
                incoming_cost = _to_decimal(device.unit_price)
            else:
                incoming_cost = previous_cost
            device.quantity += payload.cantidad
            average_cost = _calculate_weighted_average_cost(
                previous_quantity,
                previous_cost,
                payload.cantidad,
                incoming_cost,
            )
            device.costo_unitario = _quantize_currency(average_cost)
            movement_unit_cost = _quantize_currency(incoming_cost)
            _recalculate_sale_price(device)
            if (
                payload.unit_cost is None
                and previous_sale_price is not None
                and previous_sale_price > Decimal("0")
            ):
                device.unit_price = _to_decimal(previous_sale_price)
                device.precio_venta = device.unit_price
            stock_move_type = models.StockMoveType.IN  # // [PACK30-31-BACKEND]
            stock_move_quantity = _to_decimal(payload.cantidad)
            stock_move_branch_id = store_id
        elif payload.tipo_movimiento == models.MovementType.OUT:
            branch_for_cost = source_store_id or store_id
            computed_cost = inventory_accounting.compute_unit_cost(
                db,
                product_id=device.id,
                branch_id=branch_for_cost,
                quantity_out=payload.cantidad,
            )
            movement_unit_cost = _quantize_currency(computed_cost)
            device.quantity -= payload.cantidad
            if source_store_id is None:
                source_store_id = store_id
            if device.quantity <= 0:
                device.costo_unitario = Decimal("0.00")
            stock_move_type = models.StockMoveType.OUT
            stock_move_quantity = _to_decimal(payload.cantidad)
            stock_move_branch_id = branch_for_cost
            ledger_quantity = _to_decimal(payload.cantidad)
            ledger_branch_id = branch_for_cost
            ledger_unit_cost = movement_unit_cost
        elif payload.tipo_movimiento == models.MovementType.ADJUST:
            _ensure_adjustment_authorized(db, performed_by_id)
            if source_store_id is None:
                source_store_id = store_id
            adjustment_difference = payload.cantidad - previous_quantity
            adjustment_decimal = _to_decimal(adjustment_difference)
            branch_for_cost = store_id
            if (device.imei or device.serial) and (
                device.estado and device.estado.lower() == "vendido"
            ):
                raise ValueError("adjustment_device_already_sold")
            if adjustment_difference < 0 and abs(adjustment_difference) > previous_quantity:
                raise ValueError("adjustment_insufficient_stock")
            if adjustment_difference < 0:
                removal_qty = abs(adjustment_difference)
                computed_cost = inventory_accounting.compute_unit_cost(
                    db,
                    product_id=device.id,
                    branch_id=branch_for_cost,
                    quantity_out=removal_qty,
                )
                movement_unit_cost = _quantize_currency(computed_cost)
                ledger_quantity = _to_decimal(removal_qty)
                ledger_branch_id = branch_for_cost
                ledger_unit_cost = movement_unit_cost
            elif adjustment_difference > 0:
                if payload.unit_cost is not None:
                    incoming_cost = _to_decimal(payload.unit_cost)
                elif previous_cost > Decimal("0"):
                    incoming_cost = previous_cost
                elif (
                    device.unit_price is not None
                    and device.unit_price > Decimal("0")
                ):
                    incoming_cost = _to_decimal(device.unit_price)
                else:
                    incoming_cost = previous_cost

                average_cost = _calculate_weighted_average_cost(
                    previous_quantity,
                    previous_cost,
                    adjustment_difference,
                    incoming_cost,
                )
                device.costo_unitario = _quantize_currency(average_cost)
                movement_unit_cost = _quantize_currency(incoming_cost)
                _recalculate_sale_price(device)
            elif payload.unit_cost is not None and payload.cantidad > 0:
                updated_cost = _to_decimal(payload.unit_cost)
                device.costo_unitario = _quantize_currency(updated_cost)
                movement_unit_cost = _quantize_currency(updated_cost)
                _recalculate_sale_price(device)
            else:
                movement_unit_cost = (
                    _quantize_currency(previous_cost)
                    if previous_cost > Decimal("0")
                    else Decimal("0.00")
                )
            device.quantity = payload.cantidad
            if device.quantity <= 0:
                device.costo_unitario = Decimal("0.00")
            stock_move_type = models.StockMoveType.ADJUST
            stock_move_quantity = adjustment_decimal
            stock_move_branch_id = branch_for_cost
        else:
            raise ValueError("movement_type_not_supported")

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
            warehouse_id=destination_warehouse_id,
            source_warehouse_id=source_warehouse_id,
            device=device,
            movement_type=payload.tipo_movimiento,
            quantity=payload.cantidad,
            comment=payload.comentario,
            unit_cost=movement_unit_cost,
            performed_by_id=performed_by_id,
        )
        db.add(movement)
        flush_session(db)
        db.refresh(device)
        db.refresh(movement)
        reference_segments: list[str] = []
        if reference_type:
            reference_segments.append(reference_type)
        if reference_id:
            reference_segments.append(reference_id)
        accounting_reference = ":".join(
            reference_segments) if reference_segments else None
        stock_move_record: models.StockMove | None = None
        zero_decimal = Decimal("0")
        if (
            stock_move_type is not None
            and stock_move_quantity is not None
            and (
                stock_move_type != models.StockMoveType.ADJUST
                or stock_move_quantity != zero_decimal
            )
        ):
            stock_move_record = inventory_accounting.record_move(
                db,
                product_id=device.id,
                branch_id=stock_move_branch_id,
                quantity=stock_move_quantity,
                move_type=stock_move_type,
                reference=accounting_reference,
                occurred_at=movement.created_at,
            )
        if (
            stock_move_record is not None
            and ledger_quantity is not None
            and ledger_unit_cost is not None
            and ledger_quantity > zero_decimal
        ):
            cost_entry = models.CostLedgerEntry(
                product_id=device.id,
                move_id=stock_move_record.id,
                branch_id=ledger_branch_id or stock_move_branch_id,
                quantity=_to_decimal(ledger_quantity).quantize(
                    Decimal("0.0001")),
                unit_cost=_to_decimal(
                    ledger_unit_cost).quantize(Decimal("0.01")),
                method=models.CostingMethod(settings.cost_method),
            )
            db.add(cost_entry)
        # Aseguramos que las relaciones necesarias estén disponibles para la respuesta serializada.
        if movement.store is not None:
            _ = movement.store.name
        if movement.source_store is not None:
            _ = movement.source_store.name
        if movement.performed_by is not None:
            _ = movement.performed_by.username
        if movement.warehouse is not None:
            _ = movement.warehouse.name
        if movement.source_warehouse is not None:
            _ = movement.source_warehouse.name
        setattr(
            movement,
            "almacen_destino",
            movement.warehouse.name if movement.warehouse else None,
        )
        setattr(
            movement,
            "almacen_origen",
            movement.source_warehouse.name if movement.source_warehouse else None,
        )

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

        flush_session(db)
        db.refresh(movement)
        _record_inventory_movement_reference(
            db,
            movement=movement,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by_id=performed_by_id,
        )
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
    if movement.id is not None:
        last_logs = get_last_audit_entries(
            db,
            entity_type="inventory_movement",
            entity_ids=[movement.id],
        )
        latest_log = last_logs.get(str(movement.id))
        if latest_log is not None:
            setattr(
                movement,
                "ultima_accion",
                audit_trail_utils.to_audit_trail(latest_log),
            )
    inventory_availability.invalidate_inventory_availability_cache()
    return movement


def transfer_between_warehouses(
    db: Session,
    payload: schemas.WarehouseTransferCreate,
    *,
    performed_by_id: int | None = None,
) -> tuple[models.InventoryMovement, models.InventoryMovement]:
    if payload.source_warehouse_id == payload.destination_warehouse_id:
        raise ValueError("warehouse_transfer_same_destination")
    source_warehouse = get_warehouse(
        db, payload.source_warehouse_id, store_id=payload.store_id
    )
    destination_warehouse = get_warehouse(
        db, payload.destination_warehouse_id, store_id=payload.store_id
    )
    device = get_device(db, payload.store_id, payload.device_id)
    if device.warehouse_id not in {None, source_warehouse.id}:
        raise ValueError("warehouse_transfer_mismatch")
    if payload.quantity <= 0:
        raise ValueError("warehouse_transfer_invalid_quantity")
    if device.quantity != payload.quantity:
        raise ValueError("warehouse_transfer_full_quantity_required")

    with transactional_session(db):
        movement_out = _register_inventory_movement(
            db,
            store_id=payload.store_id,
            device_id=device.id,
            movement_type=models.MovementType.OUT,
            quantity=payload.quantity,
            comment=payload.reason,
            performed_by_id=performed_by_id,
            source_store_id=payload.store_id,
            destination_store_id=payload.store_id,
            source_warehouse_id=source_warehouse.id,
            warehouse_id=destination_warehouse.id,
            reference_type="warehouse_transfer",
            reference_id=str(destination_warehouse.id),
        )
        device.warehouse_id = destination_warehouse.id
        movement_in = _register_inventory_movement(
            db,
            store_id=payload.store_id,
            device_id=device.id,
            movement_type=models.MovementType.IN,
            quantity=payload.quantity,
            comment=payload.reason,
            performed_by_id=performed_by_id,
            source_store_id=payload.store_id,
            destination_store_id=payload.store_id,
            source_warehouse_id=source_warehouse.id,
            warehouse_id=destination_warehouse.id,
            reference_type="warehouse_transfer",
            reference_id=str(source_warehouse.id),
        )
    return movement_out, movement_in


def list_inventory_summary(
    db: Session, *, limit: int | None = None, offset: int = 0
) -> list[models.Store]:
    statement = select(models.Store).options(joinedload(models.Store.devices)).order_by(
        models.Store.name.asc()
    )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def list_devices_below_minimum_thresholds(
    db: Session, *, store_id: int | None = None
) -> list[dict[str, object]]:
    """Devuelve los dispositivos que están bajo el stock mínimo o punto de reorden."""

    query = (
        select(
            models.Device.id.label("device_id"),
            models.Device.store_id,
            models.Store.name.label("store_name"),
            models.Device.sku,
            models.Device.name,
            models.Device.quantity,
            models.Device.unit_price,
            models.Device.minimum_stock,
            models.Device.reorder_point,
        )
        .join(models.Store, models.Device.store_id == models.Store.id)
        .where(
            or_(
                models.Device.quantity <= models.Device.minimum_stock,
                models.Device.quantity <= models.Device.reorder_point,
            )
        )
    )

    if store_id:
        query = query.where(models.Device.store_id == store_id)

    rows = db.execute(query.order_by(models.Device.quantity, models.Device.sku)).mappings()
    return [dict(row) for row in rows]


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
                        "minimum_stock": getattr(device, "minimum_stock", 0) or 0,
                        "reorder_point": getattr(device, "reorder_point", 0) or 0,
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
            joinedload(models.Sale.customer),
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
    product_ranking: dict[int, dict[str, object]] = {}
    customer_ranking: dict[tuple[int | None, str], dict[str, object]] = {}
    credit_total = Decimal("0")
    cash_total = Decimal("0")

    today = datetime.utcnow().date()
    window_days = [today - timedelta(days=delta) for delta in range(6, -1, -1)]
    window_set = set(window_days)

    for sale in sales:
        total_sales_amount += sale.total_amount
        sale_cost = Decimal("0")
        for item in sale.items:
            device_cost = _to_decimal(
                getattr(item.device, "costo_unitario", None) or item.unit_price)
            sale_cost += (device_cost * item.quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP)
        profit = (sale.total_amount -
                  sale_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_profit += profit

        payment_method = getattr(sale, "payment_method", None)
        if payment_method == models.PaymentMethod.CREDITO:
            credit_total += sale.total_amount
        else:
            cash_total += sale.total_amount

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

        for item in sale.items:
            product_entry = product_ranking.setdefault(
                item.device_id,
                {
                    "label": (
                        getattr(item.device, "name", None)
                        or getattr(item.device, "sku", None)
                        or "Producto"
                    ),
                    "revenue": Decimal("0"),
                    "quantity": 0,
                },
            )
            product_entry["revenue"] += item.total_line
            product_entry["quantity"] += item.quantity

        customer_label = (
            sale.customer_name
            or (sale.customer.full_name if getattr(sale, "customer", None) and sale.customer.full_name else None)
            or (sale.customer.username if getattr(sale, "customer", None) and getattr(sale.customer, "username", None) else None)
            or "Venta de mostrador"
        )
        customer_entry = customer_ranking.setdefault(
            (sale.customer_id, customer_label),
            {
                "label": customer_label,
                "revenue": Decimal("0"),
                "orders": 0,
            },
        )
        customer_entry["revenue"] += sale.total_amount
        customer_entry["orders"] += 1

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

    receivable_row = db.execute(
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
    total_outstanding = Decimal(receivable_row.total_outstanding_debt or 0).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    top_delinquent = build_customer_portfolio(
        db,
        category="delinquent",
        limit=3,
    )
    top_debtors = [
        {
            "customer_id": item.customer_id,
            "name": item.name,
            "outstanding_debt": item.outstanding_debt,
            "available_credit": item.available_credit,
        }
        for item in top_delinquent.items[:3]
        if item.outstanding_debt > 0
    ]
    accounts_receivable = {
        "total_outstanding_debt": float(total_outstanding),
        "customers_with_debt": int(receivable_row.customers_with_debt or 0),
        "moroso_flagged": int(receivable_row.moroso_flagged or 0),
        "top_debtors": top_debtors,
    }

    average_ticket = (
        (total_sales_amount / sales_count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if sales_count > 0
        else Decimal("0")
    )
    ranked_products = sorted(
        (
            {
                "label": entry["label"],
                "value": float(entry["revenue"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "quantity": int(entry["quantity"]),
            }
            for entry in product_ranking.values()
        ),
        key=lambda item: (item["value"], item["quantity"]),
        reverse=True,
    )[:5]
    ranked_customers = sorted(
        (
            {
                "label": entry["label"],
                "value": float(entry["revenue"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "quantity": int(entry["orders"]),
            }
            for entry in customer_ranking.values()
        ),
        key=lambda item: (item["value"], item["quantity"]),
        reverse=True,
    )[:5]

    total_payments = (credit_total + cash_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _payment_share(amount: Decimal) -> float:
        if total_payments == 0:
            return 0.0
        percentage = (amount / total_payments * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(percentage)

    payment_mix = [
        {
            "label": "Crédito",
            "value": float(credit_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "percentage": _payment_share(credit_total),
        },
        {
            "label": "Contado",
            "value": float(cash_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "percentage": _payment_share(cash_total),
        },
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
        acknowledgement = ack_map.get(
            (entry["entity_type"], entry["entity_id"]))
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

    acknowledged_entities.sort(
        key=lambda item: item["acknowledged_at"], reverse=True)

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
        "sales_insights": {
            "average_ticket": float(average_ticket),
            "top_products": ranked_products,
            "top_customers": ranked_customers,
            "payment_mix": payment_mix,
        },
        "accounts_receivable": accounts_receivable,
        "sales_trend": sales_trend,
        "stock_breakdown": stock_breakdown,
        "repair_mix": repair_mix,
        "profit_breakdown": profit_breakdown,
        "audit_alerts": audit_alerts,
    }


def get_inventory_integrity_report(
    db: Session, *, store_ids: Iterable[int] | None = None
) -> schemas.InventoryIntegrityReport:
    """Devuelve el reporte de integridad entre existencias y movimientos."""

    return inventory_audit.build_inventory_integrity_report(db, store_ids=store_ids)


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
        movement_stmt = movement_stmt.where(
            models.InventoryMovement.store_id.in_(store_filter))
    movement_stmt = movement_stmt.where(
        models.InventoryMovement.created_at >= start_dt)
    movement_stmt = movement_stmt.where(
        models.InventoryMovement.created_at <= end_dt)
    if movement_type is not None:
        movement_stmt = movement_stmt.where(
            models.InventoryMovement.movement_type == movement_type)

    movements = list(db.scalars(movement_stmt).unique())

    _hydrate_movement_references(db, movements)

    movement_ids = [
        movement.id for movement in movements if movement.id is not None]
    audit_logs = get_last_audit_entries(
        db,
        entity_type="inventory_movement",
        entity_ids=movement_ids,
    )
    audit_trails = {
        key: audit_trail_utils.to_audit_trail(log)
        for key, log in audit_logs.items()
    }

    totals_by_type: dict[models.MovementType, dict[str, Decimal | int]] = {}
    period_map: dict[tuple[date, models.MovementType],
                     dict[str, Decimal | int]] = {}
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
        period_data["quantity"] = int(
            period_data["quantity"]) + movement.quantity
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
                referencia_tipo=getattr(movement, "reference_type", None),
                referencia_id=getattr(movement, "reference_id", None),
                fecha=movement.created_at,
                ultima_accion=audit_trails.get(str(movement.id)),
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
            total_cantidad=int(totals_by_type.get(
                movement_enum, {}).get("quantity", 0)),
            total_valor=_to_decimal(totals_by_type.get(
                movement_enum, {}).get("value", 0)),
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
    limit: int = 50,
    offset: int = 0,
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
        .offset(offset)
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
            _to_decimal(entry.valor_total_producto) -
            _to_decimal(entry.valor_costo_producto)
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


def get_inactive_products_report(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    categories: Iterable[str] | None = None,
    min_days_without_movement: int = 30,
    limit: int = 50,
    offset: int = 0,
) -> schemas.InactiveProductReport:
    min_days = max(int(min_days_without_movement), 0)
    valuations = calculate_inventory_valuation(
        db, store_ids=store_ids, categories=categories
    )

    filtered = [
        entry
        for entry in valuations
        if entry.quantity > 0
        and (
            entry.dias_sin_movimiento is None
            or int(entry.dias_sin_movimiento) >= min_days
        )
    ]

    normalized_offset = max(offset, 0)
    normalized_limit = max(limit, 0)
    paginated = (
        filtered[normalized_offset : normalized_offset + normalized_limit]
        if normalized_limit
        else filtered[normalized_offset:]
    )

    items = [
        schemas.InactiveProductEntry(
            store_id=entry.store_id,
            store_name=entry.store_name,
            device_id=entry.device_id,
            sku=entry.sku,
            device_name=entry.device_name,
            categoria=entry.categoria,
            quantity=entry.quantity,
            valor_total_producto=_to_decimal(entry.valor_total_producto),
            ultima_venta=entry.ultima_venta,
            ultima_compra=entry.ultima_compra,
            ultimo_movimiento=entry.ultimo_movimiento,
            dias_sin_movimiento=entry.dias_sin_movimiento,
            ventas_30_dias=entry.ventas_30_dias,
            ventas_90_dias=entry.ventas_90_dias,
            rotacion_30_dias=_to_decimal(entry.rotacion_30_dias),
            rotacion_90_dias=_to_decimal(entry.rotacion_90_dias),
            rotacion_total=_to_decimal(entry.rotacion_total),
        )
        for entry in paginated
    ]

    total_units = sum((entry.quantity for entry in filtered), 0)
    total_value = sum(
        (_to_decimal(entry.valor_total_producto) for entry in filtered),
        Decimal("0"),
    )
    days_values = [
        int(entry.dias_sin_movimiento)
        for entry in filtered
        if entry.dias_sin_movimiento is not None
    ]
    average_days: float | None = None
    if days_values:
        average_days = round(sum(days_values) / len(days_values), 2)
    max_days: int | None = max(days_values) if days_values else None

    totals = schemas.InactiveProductReportTotals(
        total_products=len(filtered),
        total_units=total_units,
        total_value=total_value,
        average_days_without_movement=average_days,
        max_days_without_movement=max_days,
    )

    normalized_stores = sorted({int(store_id) for store_id in store_ids or []})
    normalized_categories = [category for category in categories or [] if category]

    filters = schemas.InactiveProductReportFilters(
        store_ids=normalized_stores,
        categories=normalized_categories,
        min_days_without_movement=min_days,
    )

    return schemas.InactiveProductReport(
        generated_at=datetime.utcnow(),
        filters=filters,
        totals=totals,
        items=items,
    )


def calculate_rotation_analytics(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()

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
        device_stmt = device_stmt.where(
            models.Device.store_id.in_(store_filter))
    if category:
        device_stmt = device_stmt.where(category_expr == category)
    if supplier:
        device_stmt = device_stmt.where(models.Device.proveedor == supplier)
    if offset:
        device_stmt = device_stmt.offset(offset)
    if limit is not None:
        device_stmt = device_stmt.limit(limit)

    device_rows = list(db.execute(device_stmt))
    if not device_rows:
        return []

    device_ids = [row.id for row in device_rows]

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
    if device_ids:
        sale_stats = sale_stats.where(
            models.SaleItem.device_id.in_(device_ids))
    if start_dt:
        sale_stats = sale_stats.where(models.Sale.created_at >= start_dt)
    if end_dt:
        sale_stats = sale_stats.where(models.Sale.created_at <= end_dt)
    if category:
        sale_stats = sale_stats.where(category_expr == category)
    if supplier:
        sale_stats = sale_stats.where(models.Device.proveedor == supplier)

    purchase_stats = (
        select(
            models.PurchaseOrderItem.device_id,
            func.sum(models.PurchaseOrderItem.quantity_received).label(
                "received_units"),
            models.PurchaseOrder.store_id,
        )
        .join(models.PurchaseOrder, models.PurchaseOrder.id == models.PurchaseOrderItem.purchase_order_id)
        .join(models.Device, models.Device.id == models.PurchaseOrderItem.device_id)
        .group_by(models.PurchaseOrderItem.device_id, models.PurchaseOrder.store_id)
    )
    if store_filter:
        purchase_stats = purchase_stats.where(
            models.PurchaseOrder.store_id.in_(store_filter))
    if device_ids:
        purchase_stats = purchase_stats.where(
            models.PurchaseOrderItem.device_id.in_(device_ids)
        )
    if start_dt:
        purchase_stats = purchase_stats.where(
            models.PurchaseOrder.created_at >= start_dt)
    if end_dt:
        purchase_stats = purchase_stats.where(
            models.PurchaseOrder.created_at <= end_dt)
    if category:
        purchase_stats = purchase_stats.where(category_expr == category)
    if supplier:
        purchase_stats = purchase_stats.where(models.Device.proveedor == supplier)

    sold_map = {
        row.device_id: int(row.sold_units or 0) for row in db.execute(sale_stats)
    }
    received_map = {
        row.device_id: int(row.received_units or 0)
        for row in db.execute(purchase_stats)
    }

    results: list[dict[str, object]] = []
    for row in device_rows:
        sold_units = sold_map.get(row.id, 0)
        received_units = received_map.get(row.id, 0)
        denominator = received_units if received_units > 0 else max(
            sold_units, 1)
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
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
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
        .order_by(
            models.Device.fecha_compra.is_(None),
            models.Device.fecha_compra.asc(),
        )
    )
    if store_filter:
        device_stmt = device_stmt.where(
            models.Device.store_id.in_(store_filter))
    if date_from:
        device_stmt = device_stmt.where(
            models.Device.fecha_compra >= date_from)
    if date_to:
        device_stmt = device_stmt.where(models.Device.fecha_compra <= date_to)
    if category:
        device_stmt = device_stmt.where(category_expr == category)
    if supplier:
        device_stmt = device_stmt.where(models.Device.proveedor == supplier)

    if offset:
        device_stmt = device_stmt.offset(offset)
    if limit is not None:
        device_stmt = device_stmt.limit(limit)

    device_rows = list(db.execute(device_stmt))
    if not device_rows:
        return []

    metrics: list[dict[str, object]] = []
    for row in device_rows:
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
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()

    device_stmt = (
        select(
            models.Device.id,
            models.Device.sku,
            models.Device.name,
            models.Device.quantity,
            models.Device.minimum_stock,
            models.Device.reorder_point,
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
        .order_by(models.Store.name.asc(), models.Device.name.asc())
    )
    if store_filter:
        device_stmt = device_stmt.where(
            models.Device.store_id.in_(store_filter))
    if category:
        device_stmt = device_stmt.where(category_expr == category)
    if supplier:
        device_stmt = device_stmt.where(models.Device.proveedor == supplier)
    if offset:
        device_stmt = device_stmt.offset(offset)
    if limit is not None:
        device_stmt = device_stmt.limit(limit)

    device_rows = list(db.execute(device_stmt))
    if not device_rows:
        return []

    device_ids = [row.id for row in device_rows]

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
        sales_summary_stmt = sales_summary_stmt.where(
            models.Sale.store_id.in_(store_filter))
    if device_ids:
        sales_summary_stmt = sales_summary_stmt.where(
            models.SaleItem.device_id.in_(device_ids)
        )
    if start_dt:
        sales_summary_stmt = sales_summary_stmt.where(
            models.Sale.created_at >= start_dt)
    if end_dt:
        sales_summary_stmt = sales_summary_stmt.where(
            models.Sale.created_at <= end_dt)
    if category:
        sales_summary_stmt = sales_summary_stmt.where(
            category_expr == category)
    if supplier:
        sales_summary_stmt = sales_summary_stmt.where(
            models.Device.proveedor == supplier)

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
        daily_sales_stmt = daily_sales_stmt.where(
            models.Sale.store_id.in_(store_filter))
    if device_ids:
        daily_sales_stmt = daily_sales_stmt.where(
            models.SaleItem.device_id.in_(device_ids)
        )
    if start_dt:
        daily_sales_stmt = daily_sales_stmt.where(
            models.Sale.created_at >= start_dt)
    if end_dt:
        daily_sales_stmt = daily_sales_stmt.where(
            models.Sale.created_at <= end_dt)
    if category:
        daily_sales_stmt = daily_sales_stmt.where(category_expr == category)
    if supplier:
        daily_sales_stmt = daily_sales_stmt.where(
            models.Device.proveedor == supplier)

    sales_map: dict[int, dict[str, object]] = {}
    for row in db.execute(sales_summary_stmt):
        sales_map[row.device_id] = {
            "sold_units": int(row.sold_units or 0),
            "first_sale": row.first_sale,
            "last_sale": row.last_sale,
            "store_id": int(row.store_id),
        }

    daily_sales_map: defaultdict[int,
                                 list[tuple[datetime, float]]] = defaultdict(list)
    for row in db.execute(daily_sales_stmt):
        day: datetime | None = row.day
        if day is None:
            continue
        daily_sales_map[row.device_id].append(
            (day, float(row.sold_units or 0)))

    metrics: list[dict[str, object]] = []
    for row in device_rows:
        stats = sales_map.get(row.id)
        quantity = int(row.quantity or 0)
        daily_points_raw = sorted(
            daily_sales_map.get(row.id, []), key=lambda item: item[0]
        )
        points = [(float(index), value)
                  for index, (_, value) in enumerate(daily_points_raw)]
        slope, intercept, r_squared = _linear_regression(points)
        historical_avg = (
            sum(value for _, value in daily_points_raw) / len(daily_points_raw)
            if daily_points_raw
            else 0.0
        )
        predicted_next = max(0.0, slope * len(points) +
                             intercept) if points else 0.0
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
                "minimum_stock": int(getattr(row, "minimum_stock", 0) or 0),
                "reorder_point": int(getattr(row, "reorder_point", 0) or 0),
                "trend": trend_label,
                "trend_score": round(float(slope), 4),
                "confidence": round(float(r_squared), 3),
                "alert_level": alert_level,
                "sold_units": sold_units,
            }
        )

    metrics.sort(key=lambda item: (
        item["projected_days"] is None, item["projected_days"] or 0))
    return metrics


def calculate_store_comparatives(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()

    inventory_stmt = (
        select(
            models.Store.id,
            models.Store.name,
            func.coalesce(func.count(models.Device.id),
                          0).label("device_count"),
            func.coalesce(func.sum(models.Device.quantity),
                          0).label("total_units"),
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
        inventory_stmt = inventory_stmt.where(
            models.Store.id.in_(store_filter))
    if category:
        inventory_stmt = inventory_stmt.where(category_expr == category)
    if supplier:
        inventory_stmt = inventory_stmt.where(models.Device.proveedor == supplier)
    if offset:
        inventory_stmt = inventory_stmt.offset(offset)
    if limit is not None:
        inventory_stmt = inventory_stmt.limit(limit)

    inventory_rows = list(db.execute(inventory_stmt))
    if not inventory_rows:
        return []

    store_ids_window = [int(row.id) for row in inventory_rows]

    rotation = calculate_rotation_analytics(
        db,
        store_ids=store_ids_window,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=None,
        offset=0,
    )
    aging = calculate_aging_analytics(
        db,
        store_ids=store_ids_window,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=None,
        offset=0,
    )

    rotation_totals: dict[int, tuple[float, int]] = {}
    aging_totals: dict[int, tuple[float, int]] = {}

    for item in rotation:
        store_id = int(item["store_id"])
        total, count = rotation_totals.get(store_id, (0.0, 0))
        rotation_totals[store_id] = (
            total + float(item["rotation_rate"]), count + 1)

    for item in aging:
        store_id_value = item.get("store_id")
        if store_id_value is None:
            continue
        store_id = int(store_id_value)
        total, count = aging_totals.get(store_id, (0.0, 0))
        aging_totals[store_id] = (
            total + float(item["days_in_stock"]), count + 1)

    rotation_avg = {
        store_id: (total / count if count else 0.0)
        for store_id, (total, count) in rotation_totals.items()
    }
    aging_avg = {
        store_id: (total / count if count else 0.0)
        for store_id, (total, count) in aging_totals.items()
    }

    window_start = start_dt or (datetime.utcnow() - timedelta(days=30))
    sales_stmt = (
        select(
            models.Sale.store_id,
            func.coalesce(func.count(models.Sale.id), 0).label("orders"),
            func.coalesce(func.sum(models.Sale.total_amount),
                          0).label("revenue"),
        )
        .join(models.SaleItem, models.SaleItem.sale_id == models.Sale.id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .where(models.Sale.created_at >= window_start)
        .group_by(models.Sale.store_id)
    )
    if store_ids_window:
        sales_stmt = sales_stmt.where(
            models.Sale.store_id.in_(store_ids_window))
    if end_dt:
        sales_stmt = sales_stmt.where(models.Sale.created_at <= end_dt)
    if category:
        sales_stmt = sales_stmt.where(category_expr == category)
    if supplier:
        sales_stmt = sales_stmt.where(models.Device.proveedor == supplier)

    sales_map: dict[int, dict[str, Decimal]] = {}
    for row in db.execute(sales_stmt):
        sales_map[int(row.store_id)] = {
            "orders": Decimal(row.orders or 0),
            "revenue": Decimal(row.revenue or 0),
        }

    comparatives: list[dict[str, object]] = []
    for row in inventory_rows:
        store_id = int(row.id)
        sales = sales_map.get(
            store_id, {"orders": Decimal(0), "revenue": Decimal(0)})
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
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()
    revenue_expr = func.coalesce(func.sum(models.SaleItem.total_line), 0)
    cost_expr = func.coalesce(
        func.sum(models.SaleItem.quantity * models.Device.costo_unitario),
        0,
    )
    profit_expr = revenue_expr - cost_expr
    stmt = (
        select(
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
            revenue_expr.label("revenue"),
            cost_expr.label("cost"),
            profit_expr.label("profit"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(models.Store.id, models.Store.name)
        .order_by(profit_expr.desc())
    )
    if store_filter:
        stmt = stmt.where(models.Store.id.in_(store_filter))
    if start_dt:
        stmt = stmt.where(models.Sale.created_at >= start_dt)
    if end_dt:
        stmt = stmt.where(models.Sale.created_at <= end_dt)
    if category:
        stmt = stmt.where(category_expr == category)
    if supplier:
        stmt = stmt.where(models.Device.proveedor == supplier)
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    metrics: list[dict[str, object]] = []
    for row in db.execute(stmt):
        revenue = Decimal(row.revenue or 0)
        cost = Decimal(row.cost or 0)
        profit = Decimal(row.profit or 0)
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

    return metrics


def calculate_sales_by_store(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()
    stmt = (
        select(
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
            func.coalesce(func.sum(models.SaleItem.total_line), 0).label("revenue"),
            func.count(func.distinct(models.Sale.id)).label("orders"),
            func.coalesce(func.sum(models.SaleItem.quantity), 0).label("units"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(models.Store.id, models.Store.name)
        .order_by(func.coalesce(func.sum(models.SaleItem.total_line), 0).desc())
    )
    if store_filter:
        stmt = stmt.where(models.Store.id.in_(store_filter))
    if start_dt:
        stmt = stmt.where(models.Sale.created_at >= start_dt)
    if end_dt:
        stmt = stmt.where(models.Sale.created_at <= end_dt)
    if category:
        stmt = stmt.where(category_expr == category)
    if supplier:
        stmt = stmt.where(models.Device.proveedor == supplier)
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    results: list[dict[str, object]] = []
    for row in db.execute(stmt):
        results.append(
            {
                "store_id": int(row.store_id),
                "store_name": row.store_name,
                "revenue": float(row.revenue or 0),
                "orders": int(row.orders or 0),
                "units": int(row.units or 0),
            }
        )
    return results


def calculate_sales_by_category(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()
    stmt = (
        select(
            category_expr.label("category"),
            func.coalesce(func.sum(models.SaleItem.total_line), 0).label("revenue"),
            func.count(func.distinct(models.Sale.id)).label("orders"),
            func.coalesce(func.sum(models.SaleItem.quantity), 0).label("units"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(category_expr)
        .order_by(func.coalesce(func.sum(models.SaleItem.total_line), 0).desc())
    )
    if store_filter:
        stmt = stmt.where(models.Sale.store_id.in_(store_filter))
    if start_dt:
        stmt = stmt.where(models.Sale.created_at >= start_dt)
    if end_dt:
        stmt = stmt.where(models.Sale.created_at <= end_dt)
    if category:
        stmt = stmt.where(category_expr == category)
    if supplier:
        stmt = stmt.where(models.Device.proveedor == supplier)
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    results: list[dict[str, object]] = []
    for row in db.execute(stmt):
        results.append(
            {
                "category": row.category or "Sin categoría",
                "revenue": float(row.revenue or 0),
                "orders": int(row.orders or 0),
                "units": int(row.units or 0),
            }
        )
    return results


def calculate_sales_timeseries(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()
    stmt = (
        select(
            func.date(models.Sale.created_at).label("sale_date"),
            func.coalesce(func.sum(models.SaleItem.total_line), 0).label("revenue"),
            func.count(func.distinct(models.Sale.id)).label("orders"),
            func.coalesce(func.sum(models.SaleItem.quantity), 0).label("units"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(func.date(models.Sale.created_at))
        .order_by(func.date(models.Sale.created_at).asc())
    )
    if store_filter:
        stmt = stmt.where(models.Sale.store_id.in_(store_filter))
    if start_dt:
        stmt = stmt.where(models.Sale.created_at >= start_dt)
    if end_dt:
        stmt = stmt.where(models.Sale.created_at <= end_dt)
    if category:
        stmt = stmt.where(category_expr == category)
    if supplier:
        stmt = stmt.where(models.Device.proveedor == supplier)
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    series: list[dict[str, object]] = []
    for row in db.execute(stmt):
        series.append(
            {
                "date": row.sale_date,
                "revenue": float(row.revenue or 0),
                "orders": int(row.orders or 0),
                "units": int(row.units or 0),
            }
        )
    return series


def calculate_sales_projection(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    horizon_days: int = 30,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()
    lookback_days = max(horizon_days, 30)
    since = start_dt or (datetime.utcnow() - timedelta(days=lookback_days))

    store_stmt = select(models.Store.id, models.Store.name).order_by(
        models.Store.name.asc())
    if store_filter:
        store_stmt = store_stmt.where(models.Store.id.in_(store_filter))
    if offset:
        store_stmt = store_stmt.offset(offset)
    if limit is not None:
        store_stmt = store_stmt.limit(limit)

    store_rows = list(db.execute(store_stmt))
    if not store_rows:
        return []

    store_ids_window = [int(row.id) for row in store_rows]

    day_bucket = func.date(models.Sale.created_at)
    daily_stmt = (
        select(
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
            day_bucket.label("sale_day"),
            func.coalesce(func.sum(models.SaleItem.quantity),
                          0).label("units"),
            func.coalesce(func.sum(models.SaleItem.total_line),
                          0).label("revenue"),
            func.coalesce(func.count(func.distinct(
                models.Sale.id)), 0).label("orders"),
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
    daily_stmt = daily_stmt.where(models.Store.id.in_(store_ids_window))
    if end_dt:
        daily_stmt = daily_stmt.where(models.Sale.created_at <= end_dt)
    if category:
        daily_stmt = daily_stmt.where(category_expr == category)
    if supplier:
        daily_stmt = daily_stmt.where(models.Device.proveedor == supplier)

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
        slope_units, intercept_units, r2_units = _linear_regression(
            unit_points)
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


def list_analytics_categories(
    db: Session, *, limit: int | None = None, offset: int = 0
) -> list[str]:
    category_expr = _device_category_expr()
    stmt = (
        select(func.distinct(category_expr).label("category"))
        .where(category_expr.is_not(None))
        .order_by(category_expr.asc())
    )
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return [row.category for row in db.execute(stmt) if row.category]


def generate_analytics_alerts(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    alerts: list[dict[str, object]] = []
    window = None if limit is None else max(limit + offset, 0)
    forecast = calculate_stockout_forecast(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=window,
        offset=0,
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
        supplier=supplier,
        horizon_days=14,
        limit=window,
        offset=0,
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

    anomalies = detect_return_anomalies(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        min_returns=3,
        sigma_threshold=1.5,
        limit=window,
        offset=offset,
    )

    for anomaly in anomalies:
        if not anomaly.get("is_anomalous"):
            continue
        alerts.append(
            {
                "type": "returns",
                "level": "warning",
                "message": (
                    f"{anomaly['user_name'] or 'Usuario'} registra devoluciones inusuales"
                    f" ({anomaly['return_count']} en la ventana)"
                ),
                "store_id": None,
                "store_name": "Global",
                "device_id": None,
                "sku": None,
            }
        )

    alerts.sort(key=lambda alert: (
        alert["level"] != "critical", alert["level"] != "warning"))
    if limit is None:
        return alerts[offset:]
    return alerts[offset: offset + limit]


def calculate_store_sales_forecast(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    horizon_days: int = 14,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    projections = calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        horizon_days=horizon_days,
        limit=limit,
        offset=offset,
    )
    forecasts: list[dict[str, object]] = []
    for item in projections:
        forecasts.append(
            {
                "store_id": int(item["store_id"]),
                "store_name": item["store_name"],
                "average_daily_units": float(item.get("average_daily_units", 0)),
                "projected_units": float(item.get("projected_units", 0)),
                "projected_revenue": float(item.get("projected_revenue", 0)),
                "trend": item.get("trend", "estable"),
                "confidence": float(item.get("confidence", 0)),
            }
        )
    return forecasts


def calculate_reorder_suggestions(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    horizon_days: int = 7,
    safety_days: int = 2,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    horizon = max(horizon_days, 1) + max(safety_days, 0)
    forecast = calculate_stockout_forecast(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    suggestions: list[dict[str, object]] = []
    for item in forecast:
        quantity = int(item.get("quantity", 0) or 0)
        reorder_point = int(item.get("reorder_point", 0) or 0)
        minimum_stock = int(item.get("minimum_stock", 0) or 0)
        avg_daily = float(item.get("average_daily_sales", 0.0) or 0.0)
        projected_days = item.get("projected_days")

        buffer_target = max(reorder_point, minimum_stock)
        demand_target = math.ceil(avg_daily * horizon)
        target_level = max(buffer_target, demand_target)
        recommended_order = max(target_level - quantity, 0)

        if recommended_order <= 0:
            continue

        reason_parts: list[str] = []
        if projected_days is not None:
            reason_parts.append(f"Agotamiento estimado en {projected_days} días")
        if demand_target > buffer_target:
            reason_parts.append(
                f"Cubre demanda proyectada ({horizon} días)"
            )
        if not reason_parts:
            reason_parts.append("Stock bajo frente al buffer configurado")

        suggestions.append(
            {
                "store_id": int(item["store_id"]),
                "store_name": item["store_name"],
                "device_id": int(item["device_id"]),
                "sku": item["sku"],
                "name": item["name"],
                "quantity": quantity,
                "reorder_point": reorder_point,
                "minimum_stock": minimum_stock,
                "recommended_order": recommended_order,
                "projected_days": projected_days,
                "average_daily_sales": round(avg_daily, 2) if avg_daily else None,
                "reason": "; ".join(reason_parts),
            }
        )

    suggestions.sort(key=lambda item: item["recommended_order"], reverse=True)
    return suggestions


def detect_return_anomalies(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sigma_threshold: float = 2.0,
    min_returns: int = 3,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)

    stmt = (
        select(
            models.User.id.label("user_id"),
            models.User.username,
            models.User.full_name,
            func.count(models.SaleReturn.id).label("return_count"),
            func.coalesce(func.sum(models.SaleReturn.quantity), 0).label("units"),
            func.max(models.SaleReturn.created_at).label("last_return"),
            func.count(func.distinct(models.Sale.store_id)).label("store_count"),
        )
        .join(models.Sale, models.Sale.id == models.SaleReturn.sale_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .join(models.User, models.User.id == models.SaleReturn.processed_by_id)
        .group_by(models.User.id)
        .order_by(models.User.username.asc())
    )
    if store_filter:
        stmt = stmt.where(models.Sale.store_id.in_(store_filter))
    if start_dt:
        stmt = stmt.where(models.SaleReturn.created_at >= start_dt)
    if end_dt:
        stmt = stmt.where(models.SaleReturn.created_at <= end_dt)
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset:
        stmt = stmt.offset(offset)

    rows = list(db.execute(stmt))
    if not rows:
        return []

    counts = [int(row.return_count or 0) for row in rows]
    mean = sum(counts) / len(counts) if counts else 0.0
    variance = sum((count - mean) ** 2 for count in counts) / len(counts) if counts else 0.0
    std_dev = math.sqrt(variance)
    threshold = max(float(min_returns), mean + sigma_threshold * std_dev)

    anomalies: list[dict[str, object]] = []
    for row in rows:
        count_value = int(row.return_count or 0)
        total_units = int(row.units or 0)
        if count_value < 1:
            continue
        z_score = (count_value - mean) / std_dev if std_dev > 0 else 0.0
        is_anomalous = count_value >= threshold and count_value >= min_returns
        anomalies.append(
            {
                "user_id": int(row.user_id),
                "user_name": _user_display_name(row) or row.username,
                "return_count": count_value,
                "total_units": total_units,
                "last_return": row.last_return,
                "store_count": int(row.store_count or 0),
                "z_score": round(z_score, 2),
                "threshold": round(threshold, 2),
                "is_anomalous": is_anomalous,
            }
        )

    anomalies.sort(key=lambda item: item["return_count"], reverse=True)
    return anomalies


def calculate_realtime_store_widget(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    category: str | None = None,
    supplier: str | None = None,
    low_stock_threshold: int = 5,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    category_expr = _device_category_expr()
    today_start = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0)

    stores_stmt = select(models.Store.id, models.Store.name,
                         models.Store.inventory_value)
    if store_filter:
        stores_stmt = stores_stmt.where(models.Store.id.in_(store_filter))
    stores_stmt = stores_stmt.order_by(models.Store.name.asc())
    if offset:
        stores_stmt = stores_stmt.offset(offset)
    if limit is not None:
        stores_stmt = stores_stmt.limit(limit)

    store_rows = list(db.execute(stores_stmt))
    if not store_rows:
        return []

    store_ids_window = [int(row.id) for row in store_rows]

    low_stock_stmt = (
        select(models.Device.store_id, func.count(
            models.Device.id).label("low_stock"))
        .where(models.Device.quantity <= low_stock_threshold)
        .group_by(models.Device.store_id)
    )
    if store_ids_window:
        low_stock_stmt = low_stock_stmt.where(
            models.Device.store_id.in_(store_ids_window)
        )
    if category:
        low_stock_stmt = low_stock_stmt.where(category_expr == category)
    if supplier:
        low_stock_stmt = low_stock_stmt.where(models.Device.proveedor == supplier)

    sales_today_stmt = (
        select(
            models.Store.id.label("store_id"),
            func.coalesce(func.sum(models.SaleItem.total_line),
                          0).label("revenue"),
            func.max(models.Sale.created_at).label("last_sale_at"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .where(models.Sale.created_at >= today_start)
        .group_by(models.Store.id)
    )
    if store_ids_window:
        sales_today_stmt = sales_today_stmt.where(
            models.Store.id.in_(store_ids_window))
    if category:
        sales_today_stmt = sales_today_stmt.where(category_expr == category)
    if supplier:
        sales_today_stmt = sales_today_stmt.where(
            models.Device.proveedor == supplier)

    repairs_stmt = (
        select(
            models.RepairOrder.store_id,
            func.count(models.RepairOrder.id).label("pending"),
        )
        .where(models.RepairOrder.status != models.RepairStatus.ENTREGADO)
        .group_by(models.RepairOrder.store_id)
    )
    if store_ids_window:
        repairs_stmt = repairs_stmt.where(
            models.RepairOrder.store_id.in_(store_ids_window)
        )

    sync_stmt = (
        select(
            models.SyncSession.store_id,
            func.max(models.SyncSession.finished_at).label("last_sync"),
        )
        .group_by(models.SyncSession.store_id)
    )
    if store_ids_window:
        sync_stmt = sync_stmt.where(
            (models.SyncSession.store_id.is_(None))
            | (models.SyncSession.store_id.in_(store_ids_window))
        )

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
        int(row.store_id): max(int(row.pending or 0), 0)
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
            store_ids=store_ids_window,
            category=category,
            supplier=supplier,
            horizon_days=7,
            limit=None,
            offset=0,
        )
    }

    widgets: list[dict[str, object]] = []
    for row in store_rows:
        store_id = int(row.id)
        sales_info = sales_today_map.get(
            store_id, {"revenue": 0.0, "last_sale_at": None})
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


def calculate_purchase_supplier_metrics(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)
    category_expr = _device_category_expr()
    supplier_expr = func.coalesce(
        models.PurchaseOrder.supplier,
        models.Device.proveedor,
        literal("Sin proveedor"),
    )

    purchase_stmt = (
        select(
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
            models.Device.id.label("device_id"),
            models.Device.sku,
            models.Device.name,
            supplier_expr.label("supplier_name"),
            func.coalesce(func.sum(models.PurchaseOrderItem.quantity_ordered), 0).label(
                "ordered_units"
            ),
            func.coalesce(func.sum(models.PurchaseOrderItem.quantity_received), 0).label(
                "received_units"
            ),
            func.coalesce(
                func.sum(
                    models.PurchaseOrderItem.quantity_received
                    * models.PurchaseOrderItem.unit_cost
                ),
                0,
            ).label("received_cost"),
            func.max(models.PurchaseOrder.created_at).label("last_purchase_at"),
        )
        .join(
            models.PurchaseOrder,
            models.PurchaseOrder.id == models.PurchaseOrderItem.purchase_order_id,
        )
        .join(models.Store, models.Store.id == models.PurchaseOrder.store_id)
        .join(models.Device, models.Device.id == models.PurchaseOrderItem.device_id)
        .group_by(
            models.Store.id,
            models.Store.name,
            models.Device.id,
            models.Device.sku,
            models.Device.name,
            supplier_expr,
        )
        .order_by(func.max(models.PurchaseOrder.created_at).desc())
    )
    if store_filter:
        purchase_stmt = purchase_stmt.where(models.Store.id.in_(store_filter))
    if start_dt:
        purchase_stmt = purchase_stmt.where(models.PurchaseOrder.created_at >= start_dt)
    if end_dt:
        purchase_stmt = purchase_stmt.where(models.PurchaseOrder.created_at <= end_dt)
    if category:
        purchase_stmt = purchase_stmt.where(category_expr == category)
    if supplier:
        purchase_stmt = purchase_stmt.where(supplier_expr == supplier)
    if offset:
        purchase_stmt = purchase_stmt.offset(offset)
    if limit is not None:
        purchase_stmt = purchase_stmt.limit(limit)

    rows = list(db.execute(purchase_stmt))
    if not rows:
        return []

    store_ids_window = sorted({int(row.store_id) for row in rows})

    rotation = calculate_rotation_analytics(
        db,
        store_ids=store_ids_window,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=None,
        offset=0,
    )
    aging = calculate_aging_analytics(
        db,
        store_ids=store_ids_window,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=None,
        offset=0,
    )

    rotation_map: dict[tuple[int, int], float] = {
        (int(item["store_id"]), int(item["device_id"])): float(item["rotation_rate"])
        for item in rotation
        if item.get("device_id") is not None and item.get("store_id") is not None
    }
    aging_map: dict[tuple[int, int], float] = {
        (int(item["store_id"]), int(item["device_id"])): float(item["days_in_stock"])
        for item in aging
        if item.get("device_id") is not None and item.get("store_id") is not None
    }

    aggregates: dict[tuple[int, str], dict[str, object]] = {}
    for row in rows:
        store_id = int(row.store_id)
        supplier_name = row.supplier_name or "Sin proveedor"
        device_id = int(row.device_id)
        ordered_units = int(row.ordered_units or 0)
        received_units = int(row.received_units or 0)
        pending_units = max(ordered_units - received_units, 0)
        cost_value = Decimal(row.received_cost or 0)
        rotation_value = rotation_map.get((store_id, device_id))
        aging_value = aging_map.get((store_id, device_id))

        key = (store_id, supplier_name)
        entry = aggregates.setdefault(
            key,
            {
                "store_name": row.store_name,
                "device_ids": set(),
                "total_ordered": 0,
                "total_received": 0,
                "pending_backorders": 0,
                "total_cost": Decimal("0"),
                "rotation_sum": 0.0,
                "rotation_count": 0,
                "aging_sum": 0.0,
                "aging_count": 0,
                "last_purchase_at": None,
            },
        )
        entry["device_ids"].add(device_id)
        entry["total_ordered"] += ordered_units
        entry["total_received"] += received_units
        entry["pending_backorders"] += pending_units
        entry["total_cost"] += cost_value
        if rotation_value is not None:
            entry["rotation_sum"] += rotation_value
            entry["rotation_count"] += 1
        if aging_value is not None:
            entry["aging_sum"] += aging_value
            entry["aging_count"] += 1
        last_purchase_at = row.last_purchase_at
        current_last = entry["last_purchase_at"]
        if last_purchase_at is not None and (
            current_last is None or last_purchase_at > current_last
        ):
            entry["last_purchase_at"] = last_purchase_at

    items: list[dict[str, object]] = []
    for (store_id, supplier_name), payload in aggregates.items():
        total_received = int(payload["total_received"])
        total_cost_value: Decimal = payload["total_cost"]
        average_unit_cost = (
            float(total_cost_value / total_received)
            if total_received > 0
            else 0.0
        )
        rotation_count = int(payload["rotation_count"] or 0)
        aging_count = int(payload["aging_count"] or 0)
        average_rotation = (
            float(payload["rotation_sum"]) / rotation_count
            if rotation_count > 0
            else 0.0
        )
        average_days = (
            float(payload["aging_sum"]) / aging_count if aging_count > 0 else 0.0
        )

        items.append(
            {
                "store_id": store_id,
                "store_name": payload["store_name"],
                "supplier": supplier_name,
                "device_count": len(payload["device_ids"]),
                "total_ordered": int(payload["total_ordered"]),
                "total_received": total_received,
                "pending_backorders": int(payload["pending_backorders"]),
                "total_cost": float(total_cost_value),
                "average_unit_cost": round(average_unit_cost, 2),
                "average_rotation": round(average_rotation, 2),
                "average_days_in_stock": round(average_days, 1),
                "last_purchase_at": payload["last_purchase_at"],
            }
        )

    items.sort(key=lambda item: item["total_cost"], reverse=True)
    if offset:
        items = items[offset:]
    if limit is not None:
        items = items[:limit]
    return items


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
    with transactional_session(db):
        db.add(session)
        flush_session(db)
        db.refresh(session)

        details_payload = {
            "estado": status.value,
            "modo": mode.value,
            "eventos_procesados": processed_events,
            "diferencias_detectadas": differences_detected,
        }
        if error_message:
            details_payload["error"] = error_message

        _log_action(
            db,
            action="sync_session",
            entity_type="store" if store_id else "global",
            entity_id=str(store_id or 0),
            performed_by_id=triggered_by_id,
            details=json.dumps(details_payload, ensure_ascii=False),
        )
        if status == models.SyncStatus.FAILED:
            _log_action(
                db,
                action="sync_failure",
                entity_type="sync_session",
                entity_id=str(session.id),
                performed_by_id=triggered_by_id,
                details=json.dumps(details_payload, ensure_ascii=False),
            )
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

    with transactional_session(db):
        for discrepancy in discrepancies:
            entity_id = str(discrepancy.get("sku")
                            or discrepancy.get("entity", "global"))
            _log_action(
                db,
                action="sync_discrepancy",
                entity_type="inventory",
                entity_id=entity_id,
                performed_by_id=performed_by_id,
                details=json.dumps(
                    discrepancy, ensure_ascii=False, default=str),
            )


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

    statement = select(models.SyncOutbox).where(
        models.SyncOutbox.id.in_(ids_tuple))
    entries = list(db.scalars(statement))
    if not entries:
        return []

    now = datetime.utcnow()
    with transactional_session(db):
        for entry in entries:
            entry.status = models.SyncOutboxStatus.SENT
            entry.last_attempt_at = now
            entry.attempt_count = (entry.attempt_count or 0) + 1
            entry.error_message = None
            entry.updated_at = now
        flush_session(db)

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
            db.refresh(entry)
    return entries


def mark_outbox_entry_failed(
    db: Session,
    *,
    entry_id: int,
    error_message: str | None = None,
    performed_by_id: int | None = None,
) -> models.SyncOutbox | None:
    """Marca una entrada de outbox como fallida y registra el error."""

    entry = db.get(models.SyncOutbox, entry_id)
    if entry is None:
        return None

    now = datetime.utcnow()
    with transactional_session(db):
        entry.status = models.SyncOutboxStatus.FAILED
        entry.last_attempt_at = now
        entry.attempt_count = (entry.attempt_count or 0) + 1
        if error_message:
            entry.error_message = textwrap.shorten(str(error_message), width=250)
        entry.updated_at = now
        flush_session(db)
        db.refresh(entry)

        _log_action(
            db,
            action="sync_outbox_failed",
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "operation": entry.operation,
                    "status": entry.status.value,
                    "error": entry.error_message,
                },
                ensure_ascii=False,
            ),
        )
    return entry


def list_sync_sessions(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[models.SyncSession]:
    statement = (
        select(models.SyncSession)
        .order_by(models.SyncSession.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


def list_sync_history_by_store(
    db: Session,
    *,
    limit_per_store: int = 5,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_limit = max(limit, 0) if limit is not None else None
    store_offset = max(offset, 0)

    if store_limit == 0:
        return []

    store_name_expr = func.coalesce(models.Store.name, literal("Global"))
    store_listing_stmt = (
        select(
            models.SyncSession.store_id,
            store_name_expr.label("store_name"),
        )
        .outerjoin(models.Store, models.SyncSession.store_id == models.Store.id)
        .group_by(models.SyncSession.store_id, models.Store.name)
        .order_by(func.lower(store_name_expr), models.SyncSession.store_id)
    )
    if store_offset:
        store_listing_stmt = store_listing_stmt.offset(store_offset)
    if store_limit is not None and store_limit:
        store_listing_stmt = store_listing_stmt.limit(store_limit)

    store_rows = db.execute(store_listing_stmt).all()
    if not store_rows:
        return []

    selected_store_ids = [
        row.store_id for row in store_rows if row.store_id is not None]
    include_global = any(row.store_id is None for row in store_rows)

    ranked_sessions = (
        select(
            models.SyncSession.id.label("session_id"),
            models.SyncSession.store_id.label("store_id"),
            func.row_number()
            .over(
                partition_by=models.SyncSession.store_id,
                order_by=models.SyncSession.started_at.desc(),
            )
            .label("rank"),
        )
    ).subquery()

    statement = (
        select(models.SyncSession)
        .options(joinedload(models.SyncSession.store))
        .join(
            ranked_sessions,
            ranked_sessions.c.session_id == models.SyncSession.id,
        )
        .where(ranked_sessions.c.rank <= limit_per_store)
    )

    conditions: list[ColumnElement[bool]] = []
    if selected_store_ids:
        conditions.append(ranked_sessions.c.store_id.in_(selected_store_ids))
    if include_global:
        conditions.append(ranked_sessions.c.store_id.is_(None))
    if conditions:
        statement = statement.where(or_(*conditions))

    sessions = list(db.scalars(statement).unique())

    grouped: dict[int | None, list[models.SyncSession]] = {}
    for session in sessions:
        grouped.setdefault(session.store_id, []).append(session)

    history: list[dict[str, object]] = []
    for row in store_rows:
        store_id = row.store_id
        store_name = row.store_name or "Global"
        entries = grouped.get(store_id, [])
        if not entries:
            continue
        entries.sort(
            key=lambda entry: entry.started_at or datetime.min, reverse=True)
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
                    for entry in entries[:limit_per_store]
                ],
            }
        )

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
    with transactional_session(db):
        normalized_payload = json.loads(
            json.dumps(payload or {}, ensure_ascii=False, default=str)
        )
        resolved_priority = _resolve_outbox_priority(entity_type, priority)
        statement = select(models.SyncOutbox).where(
            models.SyncOutbox.entity_type == entity_type,
            models.SyncOutbox.entity_id == entity_id,
        )
        entry = db.scalars(statement).first()
        conflict_flag = False
        # Detectar conflicto potencial: si existe entrada PENDING distinta en operación o payload cambió.
        if entry is not None and entry.status == models.SyncOutboxStatus.PENDING:
            previous_payload = entry.payload if isinstance(entry.payload, dict) else {}
            # Heurística simple: si difiere algún campo clave declaramos conflicto.
            differing = any(
                previous_payload.get(k) != v for k, v in normalized_payload.items()
            )
            if differing or entry.operation != operation:
                conflict_flag = True
        if entry is None:
            entry = models.SyncOutbox(
                entity_type=entity_type,
                entity_id=entity_id,
                operation=operation,
                payload=normalized_payload,
                status=models.SyncOutboxStatus.PENDING,
                priority=resolved_priority,
                conflict_flag=conflict_flag,
                version=1,
            )
            db.add(entry)
        else:
            entry.operation = operation
            entry.payload = normalized_payload
            entry.status = models.SyncOutboxStatus.PENDING
            entry.attempt_count = 0
            entry.error_message = None
            entry.last_attempt_at = None
            if _priority_weight(resolved_priority) < _priority_weight(entry.priority):
                entry.priority = resolved_priority
            # Si hay conflicto, marcar y aumentar la versión.
            if conflict_flag:
                entry.conflict_flag = True
                entry.version = int(entry.version or 1) + 1
        flush_session(db)
        db.refresh(entry)
        # Registrar auditoría de conflicto potencial si aplica.
        if conflict_flag:
            log_audit_event(
                db,
                action="sync_conflict_potential",
                entity_type=entity_type,
                entity_id=entity_id,
                performed_by_id=None,
                details={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "previous_version": (int(entry.version) - 1),
                    "new_version": int(entry.version),
                    "operation": operation,
                },
            )
    # // [PACK35-backend]
    try:
        queue_event = schemas.SyncQueueEvent(
            event_type=f"{entity_type}.{operation}",
            payload={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "operation": operation,
                "payload": normalized_payload,
            },
            idempotency_key=f"outbox:{entity_type}:{entity_id}:{operation}",
        )
        enqueue_sync_queue_events(db, [queue_event])
    except Exception as exc:  # pragma: no cover - no interrumpir flujo principal
        logger.warning(
            "No se pudo reflejar el evento en sync_queue", entity_type=entity_type, error=str(exc)
        )
    return entry


# // [PACK35-backend]
def enqueue_sync_queue_events(
    db: Session,
    events: Sequence[schemas.SyncQueueEvent],
) -> tuple[list[models.SyncQueue], list[models.SyncQueue]]:
    """Registra eventos en la nueva cola híbrida respetando la idempotencia."""

    queued: list[models.SyncQueue] = []
    reused: list[models.SyncQueue] = []
    if not events:
        return queued, reused

    now = datetime.utcnow()
    with transactional_session(db):
        for event in events:
            existing: models.SyncQueue | None = None
            if event.idempotency_key:
                statement = select(models.SyncQueue).where(
                    models.SyncQueue.idempotency_key == event.idempotency_key
                )
                existing = db.scalars(statement).first()

            if existing is not None:
                existing.payload = event.payload
                existing.status = models.SyncQueueStatus.PENDING
                existing.attempts = 0
                existing.last_error = None
                existing.updated_at = now
                reused.append(existing)
                continue

            entry = models.SyncQueue(
                event_type=event.event_type,
                payload=event.payload,
                idempotency_key=event.idempotency_key,
                status=models.SyncQueueStatus.PENDING,
            )
            db.add(entry)
            queued.append(entry)

        flush_session(db)
        for entry in (*queued, *reused):
            db.refresh(entry)

    return queued, reused


# // [PACK35-backend]
def list_sync_queue_entries(
    db: Session,
    *,
    statuses: Iterable[models.SyncQueueStatus] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.SyncQueue]:
    statement = (
        select(models.SyncQueue)
        .order_by(models.SyncQueue.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if statuses is not None:
        status_tuple = tuple(statuses)
        if status_tuple:
            statement = statement.where(
                models.SyncQueue.status.in_(status_tuple))
    return list(db.scalars(statement))


# // [PACK35-backend]
def get_sync_queue_entry(db: Session, entry_id: int) -> models.SyncQueue:
    entry = db.get(models.SyncQueue, entry_id)
    if entry is None:
        raise LookupError("Entrada de cola no encontrada")
    return entry


# // [PACK35-backend]
def list_sync_attempts(
    db: Session,
    *,
    queue_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[models.SyncAttempt]:
    statement = (
        select(models.SyncAttempt)
        .where(models.SyncAttempt.queue_id == queue_id)
        .order_by(models.SyncAttempt.attempted_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


# // [PACK35-backend]
def record_sync_attempt(
    db: Session,
    *,
    queue_entry: models.SyncQueue,
    success: bool,
    error_message: str | None = None,
) -> models.SyncAttempt:
    with transactional_session(db):
        attempt = models.SyncAttempt(
            queue_id=queue_entry.id,
            success=success,
            error_message=error_message,
        )
        db.add(attempt)
        flush_session(db)
        db.refresh(attempt)
    return attempt


# // [PACK35-backend]
def update_sync_queue_entry(
    db: Session,
    entry: models.SyncQueue,
    *,
    status: models.SyncQueueStatus,
    error_message: str | None = None,
    increment_attempt: bool = False,
) -> models.SyncQueue:
    with transactional_session(db):
        if increment_attempt:
            entry.attempts += 1
        entry.status = status
        entry.last_error = error_message
        entry.updated_at = datetime.utcnow()
        flush_session(db)
        db.refresh(entry)
    return entry


# // [PACK35-backend]
def resolve_sync_queue_entry(
    db: Session,
    entry: models.SyncQueue,
) -> models.SyncQueue:
    with transactional_session(db):
        entry.status = models.SyncQueueStatus.SENT
        entry.last_error = None
        entry.updated_at = datetime.utcnow()
        flush_session(db)
        db.refresh(entry)
    return entry


# // [PACK35-backend]
def fetch_sync_queue_candidates(
    db: Session,
    *,
    limit: int = 50,
) -> list[models.SyncQueue]:
    statement = (
        select(models.SyncQueue)
        .where(
            models.SyncQueue.status.in_(
                (models.SyncQueueStatus.PENDING, models.SyncQueueStatus.FAILED)
            )
        )
        .order_by(models.SyncQueue.updated_at.asc())
        .limit(limit)
    )
    return list(db.scalars(statement))


# // [PACK35-backend]
def count_sync_queue_processed_since(db: Session, since: datetime) -> int:
    """Cuenta eventos marcados como enviados en `sync_queue` desde una fecha."""

    statement = (
        select(func.count())
        .select_from(models.SyncQueue)
        .where(
            models.SyncQueue.status == models.SyncQueueStatus.SENT,
            models.SyncQueue.updated_at >= since,
        )
    )
    return int(db.scalar(statement) or 0)


# // [PACK35-backend]
def summarize_sync_queue_statuses(
    db: Session,
) -> dict[models.SyncQueueStatus, int]:
    statement = (
        select(models.SyncQueue.status, func.count())
        .group_by(models.SyncQueue.status)
        .order_by(models.SyncQueue.status)
    )
    totals: dict[models.SyncQueueStatus, int] = {
        status: 0 for status in models.SyncQueueStatus
    }
    for status, amount in db.execute(statement):
        if isinstance(status, models.SyncQueueStatus):
            totals[status] = int(amount or 0)
    return totals


# // [PACK35-backend]
def summarize_sync_queue_by_event_type(
    db: Session,
) -> dict[str, dict[models.SyncQueueStatus, int]]:
    """Agrupa la cola híbrida por tipo de evento y estado."""

    statement = (
        select(models.SyncQueue.event_type,
               models.SyncQueue.status, func.count())
        .group_by(models.SyncQueue.event_type, models.SyncQueue.status)
        .order_by(models.SyncQueue.event_type, models.SyncQueue.status)
    )
    results: dict[str, dict[models.SyncQueueStatus, int]] = {}
    for event_type, status, amount in db.execute(statement):
        if not event_type:
            continue
        module_totals = results.setdefault(
            event_type,
            {status_key: 0 for status_key in models.SyncQueueStatus},
        )
        if isinstance(status, models.SyncQueueStatus):
            module_totals[status] = module_totals.get(
                status, 0) + int(amount or 0)
    return results


# // [PACK35-backend]
def get_latest_sync_queue_update(db: Session) -> datetime | None:
    statement = select(func.max(models.SyncQueue.updated_at))
    return db.scalar(statement)


# // [PACK35-backend]
def get_oldest_pending_sync_queue_update(db: Session) -> datetime | None:
    statement = (
        select(models.SyncQueue.updated_at)
        .where(models.SyncQueue.status == models.SyncQueueStatus.PENDING)
        .order_by(models.SyncQueue.updated_at.asc())
        .limit(1)
    )
    return db.scalar(statement)


# // [PACK35-backend]
def summarize_sync_outbox_statuses(db: Session) -> dict[models.SyncOutboxStatus, int]:
    statement = (
        select(models.SyncOutbox.status, func.count())
        .group_by(models.SyncOutbox.status)
        .order_by(models.SyncOutbox.status)
    )
    totals: dict[models.SyncOutboxStatus, int] = {
        status: 0 for status in models.SyncOutboxStatus
    }
    for status, amount in db.execute(statement):
        if isinstance(status, models.SyncOutboxStatus):
            totals[status] = int(amount or 0)
    return totals


# // [PACK35-backend]
def summarize_sync_outbox_by_entity_type(
    db: Session,
) -> dict[str, dict[models.SyncOutboxStatus, int]]:
    """Agrupa el outbox por tipo de entidad y estado."""

    statement = (
        select(models.SyncOutbox.entity_type,
               models.SyncOutbox.status, func.count())
        .group_by(models.SyncOutbox.entity_type, models.SyncOutbox.status)
        .order_by(models.SyncOutbox.entity_type, models.SyncOutbox.status)
    )
    results: dict[str, dict[models.SyncOutboxStatus, int]] = {}
    for entity_type, status, amount in db.execute(statement):
        if not entity_type:
            continue
        module_totals = results.setdefault(
            entity_type,
            {status_key: 0 for status_key in models.SyncOutboxStatus},
        )
        if isinstance(status, models.SyncOutboxStatus):
            module_totals[status] = module_totals.get(
                status, 0) + int(amount or 0)
    return results


# // [PACK35-backend]
def get_latest_sync_outbox_update(db: Session) -> datetime | None:
    statement = select(func.max(models.SyncOutbox.updated_at))
    return db.scalar(statement)


# // [PACK35-backend]
def get_oldest_pending_sync_outbox_update(db: Session) -> datetime | None:
    statement = (
        select(models.SyncOutbox.updated_at)
        .where(models.SyncOutbox.status == models.SyncOutboxStatus.PENDING)
        .order_by(models.SyncOutbox.updated_at.asc())
        .limit(1)
    )
    return db.scalar(statement)


# // [PACK35-backend]
def count_sync_outbox_processed_since(db: Session, since: datetime) -> int:
    """Cuenta eventos del outbox marcados como enviados desde una fecha."""

    statement = (
        select(func.count())
        .select_from(models.SyncOutbox)
        .where(
            models.SyncOutbox.status == models.SyncOutboxStatus.SENT,
            models.SyncOutbox.updated_at >= since,
        )
    )
    return int(db.scalar(statement) or 0)


# // [PACK35-backend]
def count_sync_attempts_since(db: Session, since: datetime) -> tuple[int, int]:
    """Obtiene intentos totales y exitosos en la ventana indicada."""

    statement = select(
        func.count(models.SyncAttempt.id),
        func.coalesce(
            func.sum(
                case(
                    (models.SyncAttempt.success.is_(True), 1),
                    else_=0,
                )
            ),
            0,
        ),
    ).where(models.SyncAttempt.attempted_at >= since)

    result = db.execute(statement).first()
    if result is None:
        return 0, 0
    total, successful = result
    return int(total or 0), int(successful or 0)


def list_sync_outbox(
    db: Session,
    *,
    statuses: Iterable[models.SyncOutboxStatus] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.SyncOutbox]:
    conflict_order = case(
        (models.SyncOutbox.conflict_flag.is_(True), 0),
        else_=1,
    )
    priority_order = case(
        (models.SyncOutbox.priority == models.SyncOutboxPriority.HIGH, 0),
        (models.SyncOutbox.priority == models.SyncOutboxPriority.NORMAL, 1),
        (models.SyncOutbox.priority == models.SyncOutboxPriority.LOW, 2),
        else_=2,
    )
    statement = (
        select(models.SyncOutbox)
        .order_by(
            conflict_order,
            priority_order,
            models.SyncOutbox.updated_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    if statuses is not None:
        status_tuple = tuple(statuses)
        if status_tuple:
            statement = statement.where(
                models.SyncOutbox.status.in_(status_tuple))
    return list(db.scalars(statement))


def list_sync_outbox_by_entity(
    db: Session,
    *,
    entity_types: Iterable[str] | None = None,
    statuses: Iterable[models.SyncOutboxStatus] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.SyncOutbox]:
    """Obtiene eventos de outbox filtrados por entidad y estado."""

    statement = (
        select(models.SyncOutbox)
        .order_by(models.SyncOutbox.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if entity_types is not None:
        entity_tuple = tuple(entity_types)
        if entity_tuple:
            statement = statement.where(models.SyncOutbox.entity_type.in_(entity_tuple))

    if statuses is not None:
        status_tuple = tuple(statuses)
        if status_tuple:
            statement = statement.where(models.SyncOutbox.status.in_(status_tuple))

    return list(db.scalars(statement))


def get_sync_outbox_entry(
    db: Session, *, entry_id: int, entity_types: Iterable[str] | None = None
) -> models.SyncOutbox | None:
    statement = select(models.SyncOutbox).where(models.SyncOutbox.id == entry_id)
    if entity_types is not None:
        entity_tuple = tuple(entity_types)
        if entity_tuple:
            statement = statement.where(models.SyncOutbox.entity_type.in_(entity_tuple))
    return db.scalars(statement).first()


def reset_outbox_entries(
    db: Session,
    entry_ids: Iterable[int],
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[models.SyncOutbox]:
    ids_tuple = tuple({int(entry_id) for entry_id in entry_ids})
    if not ids_tuple:
        return []

    statement = select(models.SyncOutbox).where(
        models.SyncOutbox.id.in_(ids_tuple))
    entries = list(db.scalars(statement))
    if not entries:
        return []

    now = datetime.utcnow()
    with transactional_session(db):
        for entry in entries:
            entry.status = models.SyncOutboxStatus.PENDING
            entry.attempt_count = 0
            entry.last_attempt_at = None
            entry.error_message = None
            entry.updated_at = now
        flush_session(db)

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
    refreshed = list(db.scalars(statement))
    normalized_offset = max(offset, 0)
    if limit is None:
        return refreshed[normalized_offset:]
    normalized_limit = max(limit, 0)
    end_index = normalized_offset + \
        normalized_limit if normalized_limit else normalized_offset
    return refreshed[normalized_offset:end_index]


def update_outbox_priority(
    db: Session,
    entry_id: int,
    *,
    priority: models.SyncOutboxPriority,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.SyncOutbox | None:
    statement = select(models.SyncOutbox).where(models.SyncOutbox.id == entry_id)
    entry = db.scalars(statement).first()
    if entry is None:
        return None

    with transactional_session(db):
        entry.priority = priority
        entry.updated_at = datetime.utcnow()
        flush_session(db)
        db.refresh(entry)
        details_payload = {"priority": priority.value, "operation": entry.operation}
        if reason:
            details_payload["reason"] = reason
        _log_action(
            db,
            action="sync_outbox_reprioritized",
            entity_type=entry.entity_type,
            entity_id=str(entry.id),
            performed_by_id=performed_by_id,
            details=json.dumps(details_payload, ensure_ascii=False),
        )
    return entry


def get_sync_outbox_statistics(
    db: Session, *, limit: int | None = None, offset: int = 0
) -> list[dict[str, object]]:
    query_limit = None if limit is None else max(limit + offset, 0)
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
                   (
                       models.SyncOutbox.status == models.SyncOutboxStatus.FAILED,
                        case(
                            (
                                models.SyncOutbox.attempt_count
                                >= 1,
                                models.SyncOutbox.attempt_count,
                            ),
                            else_=1,
                        ),
                   ),
                   else_=0,
               )
           ).label("failed"),
            func.sum(
                case(
                    (models.SyncOutbox.status == models.SyncOutboxStatus.FAILED, 1),
                    else_=0,
                )
            ).label("failed"),
            func.max(
                case(
                    (
                        models.SyncOutbox.status == models.SyncOutboxStatus.FAILED,
                        models.SyncOutbox.attempt_count,
                    ),
                    else_=0,
                )
            ).label("failed_attempts"),
            func.sum(
                case(
                    (models.SyncOutbox.conflict_flag.is_(True), 1),
                    else_=0,
                )
            ).label("conflicts"),
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
            func.max(
                case(
                    (models.SyncOutbox.conflict_flag.is_(True), models.SyncOutbox.updated_at),
                    else_=None,
                )
            ).label("last_conflict_at"),
        )
        .group_by(models.SyncOutbox.entity_type, models.SyncOutbox.priority)
    )
    if query_limit is not None:
        statement = statement.limit(query_limit)
    results: list[dict[str, object]] = []
    for row in db.execute(statement):
        priority = row.priority or models.SyncOutboxPriority.NORMAL
        results.append(
            {
                "entity_type": row.entity_type,
                "priority": priority,
                "total": int(row.total or 0),
                "pending": max(int(row.pending or 0), 0),
                "failed": max(
                    int(row.failed or 0), int(getattr(row, "failed_attempts", 0) or 0)
                ),
                "conflicts": max(int(row.conflicts or 0), 0),
                "latest_update": row.latest_update,
                "oldest_pending": row.oldest_pending,
                "last_conflict_at": row.last_conflict_at,
            }
        )
    results.sort(key=lambda item: (_priority_weight(
        item["priority"]), item["entity_type"]))
    if limit is None:
        return results[offset:]
    return results[offset: offset + limit]


def resolve_outbox_conflicts(
    db: Session,
    entry_ids: Iterable[int],
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[models.SyncOutbox]:
    ids_tuple = tuple({int(entry_id) for entry_id in entry_ids})
    if not ids_tuple:
        return []

    statement = select(models.SyncOutbox).where(
        models.SyncOutbox.id.in_(ids_tuple))
    entries = list(db.scalars(statement))
    if not entries:
        return []

    now = datetime.utcnow()
    with transactional_session(db):
        for entry in entries:
            previous_version = int(entry.version or 1)
            entry.conflict_flag = False
            entry.status = models.SyncOutboxStatus.PENDING
            entry.attempt_count = 0
            entry.last_attempt_at = None
            entry.error_message = None
            entry.updated_at = now
            entry.version = previous_version + 1
            details_payload = {
                "operation": entry.operation,
                "version": entry.version,
                "reason": reason,
                "entity_id": entry.entity_id,
            }
            log_audit_event(
                db,
                action="sync_conflict_resolved",
                entity_type=entry.entity_type,
                entity_id=entry.id,
                performed_by_id=performed_by_id,
                details=details_payload,
            )
    refreshed = list(db.scalars(statement))
    normalized_offset = max(offset, 0)
    if limit is None:
        return refreshed[normalized_offset:]
    normalized_limit = max(limit, 0)
    end_index = normalized_offset + (
        normalized_limit if normalized_limit else normalized_offset)
    return refreshed[normalized_offset:end_index]


def get_store_sync_overview(
    db: Session,
    *,
    store_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
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
    if offset and store_id is None:
        stores_stmt = stores_stmt.offset(offset)
    if limit is not None and store_id is None:
        stores_stmt = stores_stmt.limit(limit)

    store_rows = list(db.execute(stores_stmt))
    if not store_rows:
        return []

    store_ids_window = [int(row.id) for row in store_rows]

    session_stmt = select(models.SyncSession).order_by(
        models.SyncSession.finished_at.desc(),
        models.SyncSession.started_at.desc(),
    )
    if store_id is not None:
        session_stmt = session_stmt.where(
            (models.SyncSession.store_id.is_(None))
            | (models.SyncSession.store_id == store_id)
        )
    elif store_ids_window:
        session_stmt = session_stmt.where(
            (models.SyncSession.store_id.is_(None))
            | (models.SyncSession.store_id.in_(store_ids_window))
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
    elif store_ids_window:
        pending_stmt = pending_stmt.where(
            (models.TransferOrder.origin_store_id.in_(store_ids_window))
            | (models.TransferOrder.destination_store_id.in_(store_ids_window))
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
                store_candidate = entry.get(
                    "store_id") or entry.get("sucursal_id")
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
    limit: int = 50,
    offset: int = 0,
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

    if offset:
        statement = statement.offset(offset)
    fetch_limit = max(limit * 3, 200)
    raw_logs = list(db.scalars(statement.limit(fetch_limit)))
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
        difference_raw = payload.get(
            "diferencia") or payload.get("difference") or 0
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


def get_sync_discrepancies_report(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    severity: schemas.SyncBranchHealth | None = None,
    min_difference: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> schemas.SyncDiscrepancyReport:
    normalized_store_ids = sorted(
        {
            int(store_id)
            for store_id in store_ids or []
            if isinstance(store_id, int) or str(store_id).isdigit()
        }
    )
    store_filter: int | None = None
    if len(normalized_store_ids) == 1:
        store_filter = normalized_store_ids[0]

    fetch_limit = max(limit * 3, 200)
    base_conflicts = list_sync_conflicts(
        db,
        store_id=store_filter,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
        limit=fetch_limit,
        offset=0,
    )

    conflicts = base_conflicts
    if normalized_store_ids and store_filter is None:
        store_set = set(normalized_store_ids)

        def _matches(conflict: schemas.SyncConflictLog) -> bool:
            stores = conflict.stores_max + conflict.stores_min
            return any(detail.store_id in store_set for detail in stores)

        conflicts = [conflict for conflict in conflicts if _matches(conflict)]

    if min_difference is not None:
        min_diff = max(int(min_difference), 0)
        conflicts = [
            conflict for conflict in conflicts if conflict.difference >= min_diff
        ]

    if offset:
        conflicts = conflicts[offset:]
    if limit:
        conflicts = conflicts[:limit]

    warnings = sum(
        1
        for conflict in conflicts
        if conflict.severity is schemas.SyncBranchHealth.WARNING
    )
    critical = sum(
        1
        for conflict in conflicts
        if conflict.severity is schemas.SyncBranchHealth.CRITICAL
    )
    max_difference = (
        max((conflict.difference for conflict in conflicts), default=None)
        if conflicts
        else None
    )
    affected_skus = len({conflict.sku for conflict in conflicts})

    totals = schemas.SyncDiscrepancyReportTotals(
        total_conflicts=len(conflicts),
        warnings=warnings,
        critical=critical,
        max_difference=max_difference,
        affected_skus=affected_skus,
    )

    filters = schemas.SyncDiscrepancyReportFilters(
        store_ids=normalized_store_ids,
        date_from=date_from,
        date_to=date_to,
        severity=severity,
        min_difference=min_difference,
    )

    return schemas.SyncDiscrepancyReport(
        generated_at=datetime.utcnow(),
        filters=filters,
        totals=totals,
        items=conflicts,
    )


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
    with transactional_session(db):
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
        flush_session(db)
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


def list_store_memberships(
    db: Session,
    store_id: int,
    *,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.StoreMembership]:
    statement = (
        select(models.StoreMembership)
        .options(joinedload(models.StoreMembership.user))
        .where(models.StoreMembership.store_id == store_id)
        .order_by(models.StoreMembership.user_id.asc())
    )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement))


def count_store_memberships(db: Session, store_id: int) -> int:
    statement = select(func.count()).select_from(models.StoreMembership)
    statement = statement.where(models.StoreMembership.store_id == store_id)
    return int(db.scalar(statement) or 0)


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
        origin_store_id=origin_store.id,
        destination_store_id=destination_store.id,
        status=models.TransferStatus.SOLICITADA,
        requested_by_id=requested_by_id,
        reason=payload.reason,
    )
    with transactional_session(db):
        db.add(order)
        flush_session(db)

        expire_reservations(
            db, store_id=origin_store.id, device_ids=[item.device_id for item in payload.items]
        )

        for item in payload.items:
            device = get_device(db, origin_store.id, item.device_id)
            if item.quantity <= 0:
                raise ValueError("transfer_invalid_quantity")
            reservation_id = getattr(item, "reservation_id", None)
            reservation = None
            if reservation_id is not None:
                reservation = get_inventory_reservation(db, reservation_id)
                if reservation.store_id != origin_store.id:
                    raise ValueError("reservation_store_mismatch")
                if reservation.device_id != device.id:
                    raise ValueError("reservation_device_mismatch")
                if reservation.status != models.InventoryState.RESERVADO:
                    raise ValueError("reservation_not_active")
                if reservation.quantity != item.quantity:
                    raise ValueError("reservation_quantity_mismatch")
                if reservation.expires_at <= datetime.utcnow():
                    raise ValueError("reservation_expired")
            order_item = models.TransferOrderItem(
                transfer_order=order,
                device=device,
                quantity=item.quantity,
                reservation_id=reservation.id if reservation is not None else None,
            )
            db.add(order_item)

        flush_session(db)
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
    db.refresh(order)
    order = get_transfer_order(db, order.id)
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_transfer_order_payload(order),
        priority=models.SyncOutboxPriority.HIGH,
    )
    return order


def get_transfer_order(db: Session, transfer_id: int) -> models.TransferOrder:
    statement = (
        select(models.TransferOrder)
        .options(
            joinedload(models.TransferOrder.items).joinedload(
                models.TransferOrderItem.device),
            joinedload(models.TransferOrder.origin_store),
            joinedload(models.TransferOrder.destination_store),
        )
        .where(models.TransferOrder.id == transfer_id)
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("transfer_not_found") from exc


def _normalize_reception_quantities(
    order: models.TransferOrder,
    reception_items: list[schemas.TransferReceptionItem] | None,
) -> dict[int, int]:
    quantities: dict[int, int] = {}
    valid_ids = {item.id for item in order.items}
    provided_ids: set[int] = set()

    for entry in reception_items or []:
        if entry.item_id not in valid_ids:
            raise ValueError("transfer_item_mismatch")
        if entry.received_quantity < 0:
            raise ValueError("transfer_invalid_received_quantity")
        provided_ids.add(entry.item_id)
        quantities[entry.item_id] = entry.received_quantity

    for item in order.items:
        shipped = item.dispatched_quantity or item.quantity
        received = quantities.get(item.id, shipped)
        if received < 0 or received > shipped:
            raise ValueError("transfer_invalid_received_quantity")
        quantities[item.id] = received

    return quantities


def _apply_transfer_dispatch(
    db: Session,
    order: models.TransferOrder,
    *,
    performed_by_id: int,
    reason: str | None,
) -> None:
    device_ids = [item.device_id for item in order.items]
    expire_reservations(db, store_id=order.origin_store_id, device_ids=device_ids)
    reservation_map: dict[int, models.InventoryReservation] = {}
    reserved_allowances: dict[int, int] = {}
    for item in order.items:
        if item.dispatched_quantity > 0:
            continue
        if item.reservation_id is None:
            continue
        reservation = get_inventory_reservation(db, item.reservation_id)
        if reservation.store_id != order.origin_store_id:
            raise ValueError("reservation_store_mismatch")
        if reservation.device_id != item.device_id:
            raise ValueError("reservation_device_mismatch")
        if reservation.status != models.InventoryState.RESERVADO:
            raise ValueError("reservation_not_active")
        if reservation.quantity != item.quantity:
            raise ValueError("reservation_quantity_mismatch")
        if reservation.expires_at <= datetime.utcnow():
            raise ValueError("reservation_expired")
        reservation_map[item.reservation_id] = reservation
        reserved_allowances[item.device_id] = reserved_allowances.get(
            item.device_id, 0
        ) + reservation.quantity

    active_reserved_map = _active_reservations_by_device(
        db, store_id=order.origin_store_id, device_ids=set(device_ids)
    )
    blocked_map: dict[int, int] = {}
    for device_id in device_ids:
        active_total = active_reserved_map.get(device_id, 0)
        allowance = reserved_allowances.get(device_id, 0)
        blocked_map[device_id] = max(active_total - allowance, 0)

    for item in order.items:
        if item.dispatched_quantity > 0:
            continue
        device = item.device
        if device.store_id != order.origin_store_id:
            raise ValueError("transfer_device_mismatch")
        if item.quantity <= 0:
            raise ValueError("transfer_invalid_quantity")
        active_reserved = blocked_map.get(device.id, 0)
        effective_stock = device.quantity - active_reserved
        if effective_stock < item.quantity:
            raise ValueError("transfer_insufficient_stock")

        if (device.imei or device.serial) and device.quantity != item.quantity:
            raise ValueError("transfer_requires_full_unit")

        if item.reservation_id is not None:
            reservation = reservation_map.get(item.reservation_id)
            if reservation is None:
                raise ValueError("reservation_not_active")
            blocked_map[device.id] = max(active_reserved - reservation.quantity, 0)

        origin_unit_cost = _quantize_currency(_to_decimal(device.costo_unitario))
        movement = _register_inventory_movement(
            db,
            store_id=order.origin_store_id,
            device_id=device.id,
            movement_type=models.MovementType.OUT,
            quantity=item.quantity,
            comment=_build_transfer_movement_comment(order, device, "OUT", order.reason),
            performed_by_id=performed_by_id,
            source_store_id=order.origin_store_id,
            reference_type="transfer_order",
            reference_id=str(order.id),
        )
        dispatch_unit_cost = movement.unit_cost or origin_unit_cost
        item.dispatched_quantity = item.quantity
        item.dispatched_unit_cost = (
            _quantize_currency(_to_decimal(dispatch_unit_cost))
            if dispatch_unit_cost is not None
            else None
        )

        if item.reservation_id is not None:
            reservation = reservation_map[item.reservation_id]
            release_reservation(
                db,
                reservation.id,
                performed_by_id=performed_by_id,
                reason=reason or order.reason,
                target_state=models.InventoryState.CONSUMIDO,
                reference_type="transfer_order",
                reference_id=str(order.id),
            )

    order.dispatched_by_id = order.dispatched_by_id or performed_by_id
    order.dispatched_at = order.dispatched_at or datetime.utcnow()
    if reason:
        order.reason = reason

    _recalculate_store_inventory_value(db, order.origin_store_id)


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

    with transactional_session(db):
        _apply_transfer_dispatch(
            db, order, performed_by_id=performed_by_id, reason=reason
        )
        order.status = models.TransferStatus.EN_TRANSITO
        order.dispatched_by_id = performed_by_id
        order.dispatched_at = datetime.utcnow()
        order.reason = reason or order.reason

        flush_session(db)

        _log_action(
            db,
            action="transfer_dispatched",
            entity_type="transfer_order",
            entity_id=str(order.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {"status": order.status.value, "reason": reason}),
        )

        db.refresh(order)
    order = get_transfer_order(db, order.id)
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_transfer_order_payload(order),
        priority=models.SyncOutboxPriority.HIGH,
    )
    return order


def _build_transfer_movement_comment(
    order: models.TransferOrder,
    device: models.Device,
    direction: Literal["OUT", "IN"],
    reason: str | None,
) -> str:
    segments = [f"Transferencia #{order.id}"]
    if direction == "OUT":
        segments.append("Salida")
        target = order.destination_store.name if order.destination_store else None
        if target:
            segments.append(f"Destino: {target}")
    else:
        segments.append("Entrada")
        origin = order.origin_store.name if order.origin_store else None
        if origin:
            segments.append(f"Origen: {origin}")
    if device.sku:
        segments.append(f"SKU {device.sku}")
    if reason:
        segments.append(reason)
    return " — ".join(segments)[:255]


def _apply_transfer_reception(
    db: Session,
    order: models.TransferOrder,
    *,
    performed_by_id: int,
    received_map: dict[int, int],
) -> None:
    reservation_map: dict[int, models.InventoryReservation] = {}
    reserved_allowances: dict[int, int] = {}
    device_ids = [item.device_id for item in order.items]
    for item in order.items:
        if item.reservation_id is None:
            continue
        reservation = get_inventory_reservation(db, item.reservation_id)
        reservation_map[item.reservation_id] = reservation
        reserved_allowances[item.device_id] = reserved_allowances.get(
            item.device_id, 0
        ) + reservation.quantity

    active_reserved_map = _active_reservations_by_device(
        db, store_id=order.origin_store_id, device_ids=set(device_ids)
    )
    blocked_map: dict[int, int] = {}
    for device_id in device_ids:
        active_total = active_reserved_map.get(device_id, 0)
        allowance = reserved_allowances.get(device_id, 0)
        blocked_map[device_id] = max(active_total - allowance, 0)

    for item in order.items:
        device = item.device
        shipped_quantity = item.dispatched_quantity or item.quantity
        accepted_quantity = received_map.get(item.id, shipped_quantity)
        if shipped_quantity <= 0:
            raise ValueError("transfer_missing_dispatch")

        origin_unit_cost = _quantize_currency(
            _to_decimal(item.dispatched_unit_cost or device.costo_unitario)
        )

        destination_device: models.Device | None = None
        if accepted_quantity > 0:
            if device.imei or device.serial:
                if device.store_id != order.destination_store_id:
                    device.store_id = order.destination_store_id
                    flush_session(db)
                destination_device = device
        if device.store_id != order.origin_store_id:
            raise ValueError("transfer_device_mismatch")
        if item.quantity <= 0:
            raise ValueError("transfer_invalid_quantity")
        if (device.imei or device.serial) and (
            device.estado and device.estado.lower() == "vendido"
        ):
            raise ValueError("transfer_device_already_sold")
        active_reserved = blocked_map.get(device.id, 0)
        effective_stock = device.quantity - active_reserved
        if effective_stock < item.quantity:
            raise ValueError("transfer_insufficient_stock")

        if (device.imei or device.serial) and device.quantity != item.quantity:
            raise ValueError("transfer_requires_full_unit")

        if item.reservation_id is not None:
            reservation = reservation_map.get(item.reservation_id)
            if reservation is None:
                raise ValueError("reservation_not_active")
            blocked_map[device.id] = max(active_reserved - reservation.quantity, 0)

        origin_cost = _to_decimal(device.costo_unitario)
        origin_unit_cost = _quantize_currency(origin_cost)
        origin_device = device

        if not item.dispatched_quantity:
            outgoing_movement = _register_inventory_movement(
                db,
                store_id=order.origin_store_id,
                device_id=device.id,
                movement_type=models.MovementType.OUT,
                quantity=item.quantity,
                comment=_build_transfer_movement_comment(
                    order, device, "OUT", order.reason
                ),
                performed_by_id=performed_by_id,
                source_store_id=order.origin_store_id,
                reference_type="transfer_order",
                reference_id=str(order.id),
            )
            origin_device = outgoing_movement.device or device
            dispatch_unit_cost = outgoing_movement.unit_cost or origin_unit_cost
            item.dispatched_quantity = item.quantity
            item.dispatched_unit_cost = (
                _quantize_currency(_to_decimal(dispatch_unit_cost))
                if dispatch_unit_cost is not None
                else None
            )
        elif item.dispatched_unit_cost is None:
            item.dispatched_unit_cost = origin_unit_cost

        if origin_device.imei or origin_device.serial:
            origin_device.store_id = order.destination_store_id
            origin_device.quantity = 0
            flush_session(db)
            destination_device = origin_device
        else:
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
                    quantity=0,
                    unit_price=device.unit_price,
                    marca=device.marca,
                    modelo=device.modelo,
                    categoria=device.categoria,
                    condicion=device.condicion,
                    color=device.color,
                    capacidad_gb=device.capacidad_gb,
                    capacidad=device.capacidad,
                    estado_comercial=device.estado_comercial,
                    estado=device.estado,
                    proveedor=device.proveedor,
                    costo_unitario=origin_unit_cost,
                    margen_porcentaje=device.margen_porcentaje,
                    garantia_meses=device.garantia_meses,
                    lote=device.lote,
                    fecha_compra=device.fecha_compra,
                    fecha_ingreso=device.fecha_ingreso,
                    ubicacion=device.ubicacion,
                    completo=device.completo,
                    descripcion=device.descripcion,
                    imei=device.imei,
                    serial=device.serial,
                    imagen_url=device.imagen_url,
                )
                db.add(clone)
                flush_session(db)
                destination_device = clone
            else:
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
                        quantity=0,
                        unit_price=device.unit_price,
                        marca=device.marca,
                        modelo=device.modelo,
                        categoria=device.categoria,
                        condicion=device.condicion,
                        color=device.color,
                        capacidad_gb=device.capacidad_gb,
                        capacidad=device.capacidad,
                        estado_comercial=device.estado_comercial,
                        estado=device.estado,
                        proveedor=device.proveedor,
                        costo_unitario=origin_unit_cost,
                        margen_porcentaje=device.margen_porcentaje,
                        garantia_meses=device.garantia_meses,
                        lote=device.lote,
                        fecha_compra=device.fecha_compra,
                        fecha_ingreso=device.fecha_ingreso,
                        ubicacion=device.ubicacion,
                        completo=device.completo,
                        descripcion=device.descripcion,
                        imei=device.imei,
                        serial=device.serial,
                        imagen_url=device.imagen_url,
                    )
                    db.add(clone)
                    flush_session(db)
                    destination_device = clone
                else:
                    flush_session(db)

            _register_inventory_movement(
                db,
                store_id=order.destination_store_id,
                device_id=destination_device.id,
                movement_type=models.MovementType.IN,
                quantity=accepted_quantity,
                comment=_build_transfer_movement_comment(
                    order, destination_device, "IN", order.reason
                ),
                performed_by_id=performed_by_id,
                source_store_id=order.origin_store_id,
                destination_store_id=order.destination_store_id,
                unit_cost=item.dispatched_unit_cost or origin_unit_cost,
                reference_type="transfer_order",
                reference_id=str(order.id),
            )

        pending_return = shipped_quantity - accepted_quantity
        if pending_return > 0:
            _register_inventory_movement(
                db,
                store_id=order.origin_store_id,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=pending_return,
                comment=_build_transfer_movement_comment(
                    order, device, "IN", "Reverso por faltante/rechazo"
                ),
                performed_by_id=performed_by_id,
                source_store_id=order.destination_store_id,
                destination_store_id=order.origin_store_id,
                unit_cost=origin_unit_cost,
                reference_type="transfer_order",
                reference_id=str(order.id),
            )

        item.received_quantity = accepted_quantity

    _recalculate_store_inventory_value(db, order.origin_store_id)
    _recalculate_store_inventory_value(db, order.destination_store_id)


def receive_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
    items: list[schemas.TransferReceptionItem] | None = None,
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

    with transactional_session(db):
        if not any(item.dispatched_quantity > 0 for item in order.items):
            _apply_transfer_dispatch(
                db, order, performed_by_id=performed_by_id, reason=reason
            )

        reception_map = _normalize_reception_quantities(order, items)
        _apply_transfer_reception(
            db, order, performed_by_id=performed_by_id, received_map=reception_map
        )

        order.status = models.TransferStatus.RECIBIDA
        order.received_by_id = performed_by_id
        order.received_at = datetime.utcnow()
        order.reason = reason or order.reason

        flush_session(db)

        _log_action(
            db,
            action="transfer_received",
            entity_type="transfer_order",
            entity_id=str(order.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {"status": order.status.value, "reason": reason}),
        )

        db.refresh(order)
    order = get_transfer_order(db, order.id)
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_transfer_order_payload(order),
        priority=models.SyncOutboxPriority.HIGH,
    )
    return order


def reject_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
    items: list[schemas.TransferReceptionItem] | None = None,
) -> models.TransferOrder:
    order = get_transfer_order(db, transfer_id)
    if order.status not in {models.TransferStatus.EN_TRANSITO}:
        raise ValueError("transfer_invalid_transition")

    _require_store_permission(
        db,
        user_id=performed_by_id,
        store_id=order.destination_store_id,
        permission="receive",
    )

    with transactional_session(db):
        reception_map = _normalize_reception_quantities(order, items)
        rejection_map = {item_id: 0 for item_id in reception_map}
        _apply_transfer_reception(
            db,
            order,
            performed_by_id=performed_by_id,
            received_map=rejection_map,
        )

        order.status = models.TransferStatus.RECHAZADA
        order.received_by_id = performed_by_id
        order.received_at = datetime.utcnow()
        order.reason = reason or order.reason

        flush_session(db)

        _log_action(
            db,
            action="transfer_rejected",
            entity_type="transfer_order",
            entity_id=str(order.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"status": order.status.value, "reason": reason}),
        )

        db.refresh(order)
    order = get_transfer_order(db, order.id)
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_transfer_order_payload(order),
        priority=models.SyncOutboxPriority.HIGH,
    )
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

    with transactional_session(db):
        order.status = models.TransferStatus.CANCELADA
        order.cancelled_by_id = performed_by_id
        order.cancelled_at = datetime.utcnow()
        order.reason = reason or order.reason

        flush_session(db)

        _log_action(
            db,
            action="transfer_cancelled",
            entity_type="transfer_order",
            entity_id=str(order.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {"status": order.status.value, "reason": reason}),
        )

        db.refresh(order)
    order = get_transfer_order(db, order.id)
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload=_transfer_order_payload(order),
        priority=models.SyncOutboxPriority.HIGH,
    )
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
    offset: int = 0,
) -> list[models.TransferOrder]:
    statement = (
        select(models.TransferOrder)
        .options(
            joinedload(models.TransferOrder.items).joinedload(
                models.TransferOrderItem.device),
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
        statement = statement.where(
            models.TransferOrder.origin_store_id == origin_store_id)
    if destination_store_id is not None:
        statement = statement.where(
            models.TransferOrder.destination_store_id == destination_store_id)
    if status is not None:
        statement = statement.where(models.TransferOrder.status == status)
    if date_from is not None:
        statement = statement.where(
            models.TransferOrder.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(models.TransferOrder.created_at <= date_to)
    if offset:
        statement = statement.offset(offset)
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
    reason: str | None = None,
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
    with transactional_session(db):
        db.add(job)
        flush_session(db)

        componentes = ",".join(components)
        detalles = (
            f"modo={mode.value}; tamaño={total_size_bytes}; componentes={componentes}; archivos={archive_path}"
        )
        if reason:
            detalles = f"{detalles}; motivo={reason}"
        _log_action(
            db,
            action="backup_generated",
            entity_type="backup",
            entity_id=str(job.id),
            performed_by_id=triggered_by_id,
            details=detalles,
        )
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
    reason: str | None = None,
) -> None:
    detalles = (
        f"componentes={','.join(components)}; destino={destination}; aplicar_db={applied_database}"
    )
    if reason:
        detalles = f"{detalles}; motivo={reason}"
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
            joinedload(models.Compra.detalles).joinedload(
                models.DetalleCompra.producto),
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
        statement = statement.where(func.lower(
            models.Compra.estado) == estado.lower())
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
    limit: int | None = 50,
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
    limit: int | None = 50,
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


def count_purchase_records(
    db: Session,
    *,
    proveedor_id: int | None = None,
    usuario_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    estado: str | None = None,
    query: str | None = None,
) -> int:
    statement = select(func.count()).select_from(models.Compra)
    if proveedor_id is not None:
        statement = statement.where(models.Compra.proveedor_id == proveedor_id)
    if usuario_id is not None:
        statement = statement.where(models.Compra.usuario_id == usuario_id)
    if date_from is not None:
        statement = statement.where(models.Compra.fecha >= date_from)
    if date_to is not None:
        statement = statement.where(models.Compra.fecha <= date_to)
    if estado is not None:
        statement = statement.where(func.lower(
            models.Compra.estado) == estado.lower())
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.join(models.Proveedor).where(
            func.lower(models.Proveedor.nombre).like(normalized)
        )
    return int(db.scalar(statement) or 0)


def get_purchase_record(db: Session, record_id: int) -> schemas.PurchaseRecordResponse:
    statement = _purchase_record_statement().where(
        models.Compra.id_compra == record_id)
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
    with transactional_session(db):
        db.add(purchase)
        flush_session(db)

        for item in payload.items:
            if item.cantidad <= 0:
                raise ValueError("purchase_record_invalid_quantity")
            if item.costo_unitario < 0:
                raise ValueError("purchase_record_invalid_cost")

            device = get_device_global(db, item.producto_id)
            unit_cost = _to_decimal(item.costo_unitario).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP)
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
        impuesto = (subtotal_total *
                    tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = (subtotal_total + impuesto).quantize(Decimal("0.01"),
                                                     rounding=ROUND_HALF_UP)
        purchase.total = total
        purchase.impuesto = impuesto

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
    limit: int = 50,
    offset: int = 0,
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
        offset=offset,
    )
    records = [_build_purchase_record_response(
        purchase) for purchase in purchases]

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
    total_value, tax_value, count_value, last_purchase = db.execute(
        summary_stmt).one()

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
        top_vendors_stmt = top_vendors_stmt.where(
            models.Compra.fecha >= date_from)
    if date_to is not None:
        top_vendors_stmt = top_vendors_stmt.where(
            models.Compra.fecha <= date_to)
    top_vendors_stmt = (
        top_vendors_stmt.group_by(
            models.Proveedor.id_proveedor, models.Proveedor.nombre)
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
            func.coalesce(models.User.full_name,
                          models.User.username).label("nombre"),
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
        top_users_stmt.group_by(
            models.User.id, models.User.full_name, models.User.username)
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
    db: Session,
    *,
    store_id: int | None = None,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.PurchaseOrder]:
    statement = (
        select(models.PurchaseOrder)
        .options(
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.returns),
        )
        .order_by(models.PurchaseOrder.created_at.desc())
    )
    if store_id is not None:
        statement = statement.where(models.PurchaseOrder.store_id == store_id)
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def count_purchase_orders(db: Session, *, store_id: int | None = None) -> int:
    statement = select(func.count()).select_from(models.PurchaseOrder)
    if store_id is not None:
        statement = statement.where(models.PurchaseOrder.store_id == store_id)
    return int(db.scalar(statement) or 0)


def get_purchase_order(db: Session, order_id: int) -> models.PurchaseOrder:
    statement = (
        select(models.PurchaseOrder)
        .where(models.PurchaseOrder.id == order_id)
        .options(
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.returns),
            joinedload(models.PurchaseOrder.documents),
            joinedload(models.PurchaseOrder.status_events).joinedload(
                models.PurchaseOrderStatusEvent.created_by
            ),
            joinedload(models.PurchaseOrder.approved_by),
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

    total_amount = Decimal("0")
    for item in payload.items:
        total_amount += Decimal(item.quantity_ordered) * _to_decimal(item.unit_cost)
    approval_threshold = _to_decimal(
        getattr(settings, "purchases_large_order_threshold", Decimal("0"))
    )
    requires_approval = approval_threshold > 0 and total_amount >= approval_threshold

    order = models.PurchaseOrder(
        store_id=payload.store_id,
        supplier=payload.supplier,
        notes=payload.notes,
        created_by_id=created_by_id,
        requires_approval=requires_approval,
    )
    with transactional_session(db):
        db.add(order)
        flush_session(db)

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
                unit_cost=_to_decimal(item.unit_cost).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP),
            )
            db.add(order_item)

        db.refresh(order)

        _register_purchase_status_event(
            db,
            order,
            status=order.status,
            created_by_id=created_by_id,
            note="Creación de orden",
        )
        db.refresh(order)

        _log_action(
            db,
            action="purchase_order_created",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=created_by_id,
            details=json.dumps(
                {"store_id": order.store_id, "supplier": order.supplier}
            ),
        )
        db.refresh(order)
        enqueue_sync_outbox(
            db,
            entity_type="purchase_order",
            entity_id=str(order.id),
            operation="UPSERT",
            payload=_purchase_order_payload(order),
        )
    db.refresh(order)
    return order


def create_purchase_order_from_suggestion(
    db: Session,
    payload: schemas.PurchaseOrderCreate,
    *,
    created_by_id: int | None = None,
    reason: str,
) -> models.PurchaseOrder:
    """Genera una orden de compra desde una sugerencia automatizada."""

    order = create_purchase_order(db, payload, created_by_id=created_by_id)

    items_details = [
        {"device_id": item.device_id, "quantity_ordered": item.quantity_ordered}
        for item in order.items
    ]

    with transactional_session(db):
        _log_action(
            db,
            action="purchase_order_generated_from_suggestion",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=created_by_id,
            details=json.dumps(
                {
                    "store_id": order.store_id,
                    "supplier": order.supplier,
                    "reason": reason,
                    "source": "purchase_suggestion",
                    "items": items_details,
                }
            ),
        )
        flush_session(db)

    db.refresh(order)
    return order


def _build_purchase_movement_comment(
    action: str,
    order: models.PurchaseOrder,
    device: models.Device,
    reason: str | None,
) -> str:
    """Genera una descripción legible para los movimientos de compras."""

    parts: list[str] = [
        action, f"OC #{order.id}", f"Proveedor: {order.supplier}"]
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
    if order.requires_approval and order.approved_by_id is None:
        raise PermissionError("purchase_requires_approval")
    if order.status == models.PurchaseStatus.BORRADOR:
        raise ValueError("purchase_not_receivable")
    if not payload.items:
        raise ValueError("purchase_items_required")

    items_by_device = {item.device_id: item for item in order.items}
    reception_details: dict[str, int] = {}
    batch_updates: dict[str, int] = {}
    store = get_store(db, order.store_id)

    for receive_item in payload.items:
        order_item = items_by_device.get(receive_item.device_id)
        if order_item is None:
            raise LookupError("purchase_item_not_found")
        pending = order_item.quantity_ordered - order_item.quantity_received
        if receive_item.quantity <= 0 or receive_item.quantity > pending:
            raise ValueError("purchase_invalid_quantity")

        order_item.quantity_received += receive_item.quantity

        device = get_device(db, order.store_id, order_item.device_id)
        movement = _register_inventory_movement(
            db,
            store_id=order.store_id,
            device_id=device.id,
            movement_type=models.MovementType.IN,
            quantity=receive_item.quantity,
            comment=_build_purchase_movement_comment(
                "Recepción OC",
                order,
                device,
                reason,
            ),
            performed_by_id=received_by_id,
            unit_cost=_to_decimal(order_item.unit_cost),
            reference_type="purchase_order",
            reference_id=str(order.id),
        )
        movement_device = movement.device or device
        movement_device.proveedor = order.supplier
        reception_details[str(device.id)] = receive_item.quantity

        batch_code = getattr(receive_item, "batch_code", None)
        if batch_code:
            batch = assign_supplier_batch(
                db,
                supplier_name=order.supplier,
                store=store,
                device=movement_device,
                batch_code=batch_code,
                quantity=receive_item.quantity,
                unit_cost=_to_decimal(order_item.unit_cost),
                purchase_date=datetime.utcnow().date(),
            )
            movement_device.lote = batch.batch_code
            movement_device.fecha_compra = batch.purchase_date
            movement_device.costo_unitario = batch.unit_cost
            if batch.supplier and batch.supplier.name:
                movement_device.proveedor = batch.supplier.name
            db.add(movement_device)
            batch_updates[batch.batch_code] = (
                batch_updates.get(batch.batch_code, 0) + receive_item.quantity
            )

    with transactional_session(db):
        if all(item.quantity_received == item.quantity_ordered for item in order.items):
            order.status = models.PurchaseStatus.COMPLETADA
            order.closed_at = datetime.utcnow()
        else:
            order.status = models.PurchaseStatus.PARCIAL

        flush_session(db)
        db.refresh(order)
        _register_purchase_status_event(
            db,
            order,
            status=order.status,
            created_by_id=received_by_id,
            note=reason,
        )
        db.refresh(order)
        _recalculate_store_inventory_value(db, order.store_id)

        _log_action(
            db,
            action="purchase_order_received",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=received_by_id,
            details=json.dumps(
                {
                    "items": reception_details,
                    "status": order.status.value,
                    "reason": reason,
                    "batches": batch_updates,
                }
            ),
        )
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

        _register_inventory_movement(
            db,
            store_id=order.store_id,
            device_id=device.id,
            movement_type=models.MovementType.OUT,
            quantity=received_qty,
            comment=_build_purchase_movement_comment(
                "Reversión OC",
                order,
                device,
                reason,
            ),
            performed_by_id=cancelled_by_id,
            source_store_id=order.store_id,
            unit_cost=_to_decimal(order_item.unit_cost),
            reference_type="purchase_order",
            reference_id=str(order.id),
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

    with transactional_session(db):
        reversal_details = _revert_purchase_inventory(
            db,
            order,
            cancelled_by_id=cancelled_by_id,
            reason=reason,
        )

        order.status = models.PurchaseStatus.CANCELADA
        order.closed_at = datetime.utcnow()
        if reason:
            order.notes = (order.notes or "") + \
                f" | Cancelación: {reason}" if order.notes else reason

        flush_session(db)
        db.refresh(order)
        _register_purchase_status_event(
            db,
            order,
            status=order.status,
            created_by_id=cancelled_by_id,
            note=reason,
        )
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
        db.refresh(order)
        enqueue_sync_outbox(
            db,
            entity_type="purchase_order",
            entity_id=str(order.id),
            operation="UPSERT",
            payload=_purchase_order_payload(order),
        )
    return order


def _register_supplier_credit_note(
    db: Session,
    *,
    supplier_name: str | None,
    purchase_order_id: int,
    credit_amount: Decimal,
    corporate_reason: str | None,
    processed_by_id: int | None,
) -> models.SupplierLedgerEntry | None:
    supplier = _get_supplier_by_name(db, supplier_name)
    if supplier is None:
        return None

    normalized_amount = _to_decimal(credit_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if normalized_amount <= Decimal("0"):
        return None

    current_debt = _to_decimal(supplier.outstanding_debt).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    new_debt = (current_debt - normalized_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if new_debt < Decimal("0"):
        new_debt = Decimal("0")

    supplier.outstanding_debt = new_debt
    db.add(supplier)
    flush_session(db)

    details: dict[str, object] = {
        "source": "purchase_return",
        "purchase_order_id": purchase_order_id,
        "credit_amount": float(normalized_amount),
    }
    if corporate_reason:
        details["corporate_reason"] = corporate_reason

    entry = _create_supplier_ledger_entry(
        db,
        supplier=supplier,
        entry_type=models.SupplierLedgerEntryType.CREDIT_NOTE,
        amount=-normalized_amount,
        note=corporate_reason,
        reference_type="purchase_return",
        reference_id=str(purchase_order_id),
        details=details,
        created_by_id=processed_by_id,
    )
    _sync_supplier_ledger_entry(db, entry)
    return entry


def register_purchase_return(
    db: Session,
    order_id: int,
    payload: schemas.PurchaseReturnCreate,
    *,
    processed_by_id: int,
    reason: str | None = None,
) -> models.PurchaseReturn:
    order = get_purchase_order(db, order_id)
    order_item = next(
        (item for item in order.items if item.device_id == payload.device_id), None)
    if order_item is None:
        raise LookupError("purchase_item_not_found")
    if payload.quantity <= 0:
        raise ValueError("purchase_invalid_quantity")

    received_total = order_item.quantity_received
    returned_total = sum(
        ret.quantity for ret in order.returns if ret.device_id == payload.device_id)
    if payload.quantity > received_total - returned_total:
        raise ValueError("purchase_return_exceeds_received")

    device = get_device(db, order.store_id, payload.device_id)
    disposition = payload.disposition
    warehouse_id = payload.warehouse_id
    if warehouse_id is not None and warehouse_id <= 0:
        raise ValueError("purchase_return_invalid_warehouse")
    warehouse: models.Warehouse | None = None
    if warehouse_id is not None:
        warehouse = get_warehouse(db, warehouse_id)
        if warehouse.store_id != order.store_id:
            raise ValueError("purchase_return_invalid_warehouse")
    if device.quantity < payload.quantity:
        raise ValueError("purchase_return_insufficient_stock")
    unit_cost = _to_decimal(order_item.unit_cost)
    credit_note_amount = (
        unit_cost * _to_decimal(payload.quantity)
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    corporate_reason = reason.strip() if isinstance(reason, str) else None
    with transactional_session(db):
        movement_reason = payload.reason or reason
        if movement_reason:
            movement_reason = movement_reason.strip()
        if disposition != schemas.ReturnDisposition.VENDIBLE:
            note = f"estado={disposition.value}"
            movement_reason = f"{movement_reason} | {note}" if movement_reason else note
        if warehouse and warehouse.id != order.store_id:
            warehouse_note = f"almacen={warehouse.name}"
            movement_reason = (
                f"{movement_reason} | {warehouse_note}"
                if movement_reason
                else warehouse_note
            )
        _register_inventory_movement(
            db,
            store_id=order.store_id,
            device_id=device.id,
            movement_type=models.MovementType.OUT,
            quantity=payload.quantity,
            comment=_build_purchase_movement_comment(
                "Devolución proveedor",
                order,
                device,
                movement_reason,
            ),
            performed_by_id=processed_by_id,
            source_store_id=order.store_id,
            source_warehouse_id=device.warehouse_id,
            warehouse_id=warehouse.id if warehouse else device.warehouse_id,
            unit_cost=_to_decimal(order_item.unit_cost),
            reference_type="purchase_return",
            reference_id=str(order.id),
        )

        ledger_entry = _register_supplier_credit_note(
            db,
            supplier_name=order.supplier,
            purchase_order_id=order.id,
            credit_amount=credit_note_amount,
            corporate_reason=corporate_reason,
            processed_by_id=processed_by_id,
        )

        purchase_return = models.PurchaseReturn(
            purchase_order_id=order.id,
            device_id=device.id,
            quantity=payload.quantity,
            reason=payload.reason,
            reason_category=payload.category,
            disposition=disposition,
            warehouse_id=warehouse_id,
            processed_by_id=processed_by_id,
            corporate_reason=corporate_reason,
            credit_note_amount=credit_note_amount,
            supplier_ledger_entry_id=ledger_entry.id if ledger_entry else None,
        )
        db.add(purchase_return)
        flush_session(db)
        db.refresh(purchase_return)

        _log_action(
            db,
            action="purchase_return_registered",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=processed_by_id,
            details=json.dumps(
                {
                    "device_id": payload.device_id,
                    "quantity": payload.quantity,
                    "return_reason": payload.reason,
                    "request_reason": reason,
                    "credit_note_amount": float(credit_note_amount),
                }
            ),
        )
        db.refresh(order)
        enqueue_sync_outbox(
            db,
            entity_type="purchase_order",
            entity_id=str(order.id),
            operation="UPSERT",
            payload=_purchase_order_payload(order),
        )
    return purchase_return


def add_purchase_order_document(
    db: Session,
    order_id: int,
    *,
    filename: str,
    content_type: str,
    content: bytes,
    uploaded_by_id: int | None = None,
) -> models.PurchaseOrderDocument:
    order = get_purchase_order(db, order_id)
    normalized_filename = (filename or "documento.pdf").strip() or "documento.pdf"
    normalized_type = (content_type or "").lower()
    if not normalized_filename.lower().endswith(".pdf") or "pdf" not in normalized_type:
        raise ValueError("purchase_document_not_pdf")

    storage = purchase_documents.get_storage()
    stored = storage.save(
        filename=normalized_filename,
        content_type="application/pdf",
        content=content,
    )
    document = models.PurchaseOrderDocument(
        purchase_order_id=order.id,
        filename=normalized_filename,
        content_type="application/pdf",
        storage_backend=stored.backend,
        object_path=stored.path,
        uploaded_by_id=uploaded_by_id,
    )

    with transactional_session(db):
        db.add(document)
        flush_session(db)
        db.refresh(document)
        _log_action(
            db,
            action="purchase_order_document_uploaded",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=uploaded_by_id,
            details=json.dumps(
                {
                    "document_id": document.id,
                    "filename": document.filename,
                    "storage_backend": document.storage_backend,
                }
            ),
        )
        db.refresh(order)
        enqueue_sync_outbox(
            db,
            entity_type="purchase_order",
            entity_id=str(order.id),
            operation="UPSERT",
            payload=_purchase_order_payload(order),
        )

    return document


def load_purchase_order_document(
    db: Session, order_id: int, document_id: int
) -> tuple[models.PurchaseOrderDocument, bytes]:
    statement = (
        select(models.PurchaseOrderDocument)
        .where(
            models.PurchaseOrderDocument.id == document_id,
            models.PurchaseOrderDocument.purchase_order_id == order_id,
        )
        .options(joinedload(models.PurchaseOrderDocument.uploaded_by))
    )
    document = db.scalars(statement).one_or_none()
    if document is None:
        raise LookupError("purchase_document_not_found")
    storage = purchase_documents.get_storage()
    content = storage.open(document.object_path)
    return document, content


def transition_purchase_order_status(
    db: Session,
    order_id: int,
    *,
    status: models.PurchaseStatus,
    note: str | None = None,
    performed_by_id: int | None = None,
) -> models.PurchaseOrder:
    allowed_statuses = {
        models.PurchaseStatus.BORRADOR,
        models.PurchaseStatus.PENDIENTE,
        models.PurchaseStatus.APROBADA,
        models.PurchaseStatus.ENVIADA,
    }
    if status not in allowed_statuses:
        raise ValueError("purchase_status_not_allowed")

    order = get_purchase_order(db, order_id)
    if order.status in {
        models.PurchaseStatus.CANCELADA,
        models.PurchaseStatus.COMPLETADA,
    }:
        raise ValueError("purchase_status_locked")
    if order.status == status:
        raise ValueError("purchase_status_noop")

    with transactional_session(db):
        order.status = status
        if status == models.PurchaseStatus.APROBADA:
            order.approved_by_id = performed_by_id
        elif status in {
            models.PurchaseStatus.BORRADOR,
            models.PurchaseStatus.PENDIENTE,
        }:
            order.approved_by_id = None
        order.updated_at = datetime.utcnow()
        flush_session(db)
        db.refresh(order)
        _register_purchase_status_event(
            db,
            order,
            status=status,
            note=note,
            created_by_id=performed_by_id,
        )
        db.refresh(order)
        _log_action(
            db,
            action="purchase_order_status_transition",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "status": status.value,
                    "note": _normalize_optional_note(note),
                }
            ),
        )
        db.refresh(order)
        enqueue_sync_outbox(
            db,
            entity_type="purchase_order",
            entity_id=str(order.id),
            operation="UPSERT",
            payload=_purchase_order_payload(order),
        )

    return order


def send_purchase_order_email(
    db: Session,
    order_id: int,
    *,
    recipients: Sequence[str],
    message: str | None = None,
    include_documents: bool = False,
    requested_by_id: int | None = None,
) -> models.PurchaseOrder:
    order = get_purchase_order(db, order_id)
    normalized_recipients = [
        recipient.strip()
        for recipient in recipients
        if isinstance(recipient, str) and recipient.strip()
    ]
    if not normalized_recipients:
        raise ValueError("purchase_email_recipients_required")

    purchase_documents.send_purchase_order_email(
        order=order,
        recipients=normalized_recipients,
        message=_normalize_optional_note(message),
        include_documents=include_documents,
    )

    with transactional_session(db):
        _log_action(
            db,
            action="purchase_order_email_sent",
            entity_type="purchase_order",
            entity_id=str(order.id),
            performed_by_id=requested_by_id,
            details=json.dumps(
                {
                    "recipients": normalized_recipients,
                    "include_documents": include_documents,
                }
            ),
        )
        flush_session(db)

    return order


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
    required_headers = {"store_id", "supplier",
                        "device_id", "quantity", "unit_cost"}
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
            errors.append(
                f"Fila {line_number}: la cantidad debe ser mayor a cero")
            continue

        try:
            unit_cost_value = _to_decimal(normalized.get("unit_cost"))
        except Exception:  # pragma: no cover - validaciones de Decimal
            errors.append(f"Fila {line_number}: costo unitario inválido")
            continue

        if unit_cost_value < Decimal("0"):
            errors.append(
                f"Fila {line_number}: el costo unitario no puede ser negativo")
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

        items_map: defaultdict[int, dict[str, Decimal | int]
                               ] = group["items"]  # type: ignore[assignment]
        bucket = items_map[device_id]
        bucket["quantity"] += quantity
        bucket["unit_cost"] = unit_cost_value.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
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
            errors.append(f"Orden {reference}: {exc}")
            continue
        orders.append(order)

    if orders:
        with transactional_session(db):
            _log_action(
                db,
                action="purchase_orders_imported",
                entity_type="purchase_order",
                entity_id="bulk",
                performed_by_id=created_by_id,
                details=json.dumps(
                    {"imported": len(orders), "errors": len(errors)}),
            )

    return orders, errors


def list_recurring_orders(
    db: Session,
    *,
    order_type: models.RecurringOrderType | None = None,
    limit: int = 50,
    offset: int = 0,
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
        statement = statement.where(
            models.RecurringOrder.order_type == order_type)
    if offset:
        statement = statement.offset(offset)
    statement = statement.limit(limit)
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
        store_scope = int(payload_data.get("store_id")) if payload_data.get(
            "store_id") is not None else None
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
    with transactional_session(db):
        db.add(template)
        flush_session(db)
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
        purchase_payload = schemas.PurchaseOrderCreate.model_validate(
            template.payload)
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
        transfer_payload = schemas.TransferOrderCreate.model_validate(
            template.payload)
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

    with transactional_session(db):
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
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.RepairOrder]:
    statement = (
        select(models.RepairOrder)
        .options(
            joinedload(models.RepairOrder.parts).joinedload(
                models.RepairOrderPart.device)
        )
        .order_by(models.RepairOrder.opened_at.desc())
    )
    if store_id is not None:
        statement = statement.where(models.RepairOrder.store_id == store_id)
    if status is not None:
        statement = statement.where(models.RepairOrder.status == status)
    if date_from is not None or date_to is not None:
        start_dt, end_dt = _normalize_date_range(date_from, date_to)
        statement = statement.where(
            models.RepairOrder.opened_at >= start_dt,
            models.RepairOrder.opened_at <= end_dt,
        )
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.RepairOrder.customer_name).like(normalized),
                func.lower(models.RepairOrder.technician_name).like(
                    normalized),
                func.lower(models.RepairOrder.damage_type).like(normalized),
                func.lower(models.RepairOrder.device_model).like(normalized),
                func.lower(models.RepairOrder.imei).like(normalized),
            )
        )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def get_repair_order(db: Session, order_id: int) -> models.RepairOrder:
    statement = (
        select(models.RepairOrder)
        .where(models.RepairOrder.id == order_id)
        .options(
            joinedload(models.RepairOrder.parts).joinedload(
                models.RepairOrderPart.device),
            joinedload(models.RepairOrder.customer),
        )
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("repair_order_not_found") from exc


def _apply_repair_parts(  # // [PACK37-backend]
    db: Session,
    order: models.RepairOrder,
    parts_payload: list[schemas.RepairOrderPartPayload],
    *,
    performed_by_id: int | None,
    reason: str | None,
) -> Decimal:
    def _part_key(
        device_id: int | None,
        part_name: str | None,
        source: models.RepairPartSource,
    ) -> tuple[int, str, str]:
        normalized_name = (part_name or "").strip().lower()
        return (device_id or 0, normalized_name, source.value)

    existing_parts: dict[tuple[int, str, str], models.RepairOrderPart] = {}
    for part in order.parts:
        part_source = part.source if part.source else models.RepairPartSource.STOCK
        existing_parts[_part_key(
            part.device_id, part.part_name, part_source)] = part

    aggregated: dict[tuple[int, str, str], dict[str, object]] = {}
    for payload in parts_payload:
        normalized = schemas.RepairOrderPartPayload(
            device_id=payload.device_id,
            part_name=payload.part_name,
            source=payload.source,
            quantity=payload.quantity,
            unit_cost=payload.unit_cost,
        )
        if normalized.quantity <= 0:
            raise ValueError("repair_invalid_quantity")
        source = models.RepairPartSource(normalized.source)
        part_name = normalized.part_name
        device_id = normalized.device_id
        if source == models.RepairPartSource.STOCK and not device_id:
            raise ValueError("repair_part_device_required")
        if source == models.RepairPartSource.EXTERNAL and not part_name:
            raise ValueError("repair_part_name_required")
        unit_cost = _to_decimal(normalized.unit_cost or 0).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        key = _part_key(device_id, part_name, source)
        entry = aggregated.get(key)
        if entry:
            entry["quantity"] = int(entry["quantity"]) + normalized.quantity
            if unit_cost > Decimal("0"):
                entry["unit_cost"] = unit_cost
            if part_name and not entry.get("part_name"):
                entry["part_name"] = part_name
        else:
            aggregated[key] = {
                "device_id": device_id,
                "part_name": part_name,
                "source": source,
                "quantity": normalized.quantity,
                "unit_cost": unit_cost,
            }

    processed_keys: set[tuple[int, str, str]] = set()
    processed_devices: set[int] = set()
    total_cost = Decimal("0")
    snapshot: list[dict[str, object]] = []

    for key, data in aggregated.items():
        device_id = data.get("device_id")
        part_name = data.get("part_name")
        source = data["source"]
        quantity = int(data["quantity"])
        unit_cost = _to_decimal(data["unit_cost"]).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        device = None
        if source == models.RepairPartSource.STOCK and device_id:
            device = get_device(db, order.store_id, int(device_id))
        previous_part = existing_parts.get(key)
        previous_quantity = previous_part.quantity if previous_part else 0
        delta = quantity - previous_quantity

        if device and delta != 0:
            movement_type = (
                models.MovementType.OUT
                if delta > 0
                else models.MovementType.IN
            )
            adjust_quantity = abs(delta)
            if movement_type == models.MovementType.OUT and device.quantity < adjust_quantity:
                raise ValueError("repair_insufficient_stock")
            _register_inventory_movement(
                db,
                store_id=order.store_id,
                device_id=device.id,
                movement_type=movement_type,
                quantity=adjust_quantity,
                comment=reason or f"Reparación #{order.id}",
                performed_by_id=performed_by_id,
                source_store_id=order.store_id,
                reference_type="repair_order",
                reference_id=str(order.id),
            )
            processed_devices.add(device.id)

        if previous_part:
            previous_part.quantity = quantity
            previous_part.unit_cost = unit_cost
            previous_part.part_name = part_name
            previous_part.source = source
            previous_part.device_id = device.id if device else None
            db.add(previous_part)
            part_record = previous_part
        else:
            part_record = models.RepairOrderPart(
                repair_order_id=order.id,
                device_id=device.id if device else None,
                part_name=part_name,
                quantity=quantity,
                unit_cost=unit_cost,
                source=source,
            )
            order.parts.append(part_record)

        snapshot.append(
            {
                "device_id": part_record.device_id,
                "part_name": part_name,
                "source": source.value,
                "quantity": quantity,
                "unit_cost": float(unit_cost),
            }
        )
        total_cost += unit_cost * Decimal(quantity)
        processed_keys.add(key)

    for key, part in list(existing_parts.items()):
        if key in processed_keys:
            continue
        if part.source == models.RepairPartSource.STOCK and part.device_id:
            device = get_device(db, order.store_id, part.device_id)
            _register_inventory_movement(
                db,
                store_id=order.store_id,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=part.quantity,
                comment=reason or f"Reverso reparación #{order.id}",
                performed_by_id=performed_by_id,
                source_store_id=order.store_id,
                reference_type="repair_order",
                reference_id=str(order.id),
            )
            processed_devices.add(device.id)
        order.parts.remove(part)
        db.delete(part)

    order.parts_cost = total_cost.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    order.parts_snapshot = snapshot
    order.inventory_adjusted = bool(processed_devices)
    _recalculate_store_inventory_value(db, order.store_id)
    return order.parts_cost


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
    labor_cost = _to_decimal(payload.labor_cost).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    customer_name = payload.customer_name or (
        customer.name if customer else None)
    order = models.RepairOrder(
        store_id=payload.store_id,
        customer_id=payload.customer_id,
        customer_name=customer_name,
        customer_contact=payload.customer_contact,
        technician_name=payload.technician_name,
        damage_type=payload.damage_type,
        diagnosis=payload.diagnosis,
        device_model=payload.device_model,
        imei=payload.imei,
        device_description=payload.device_description,
        notes=payload.notes,
        labor_cost=labor_cost,
    )
    with transactional_session(db):
        db.add(order)
        flush_session(db)

        parts_cost = Decimal("0")
        if payload.parts:
            parts_cost = _apply_repair_parts(
                db,
                order,
                payload.parts,
                performed_by_id=performed_by_id,
                reason=reason,
            )
        order.total_cost = (
            labor_cost + parts_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        db.add(order)

        if customer:
            _append_customer_history(
                customer, f"Orden de reparación #{order.id} creada")
            db.add(customer)

        flush_session(db)
        db.refresh(order)
        if customer:
            db.refresh(customer)

        _log_action(
            db,
            action="repair_order_created",
            entity_type="repair_order",
            entity_id=str(order.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "store_id": order.store_id,
                    "status": order.status.value,
                    "reason": reason,
                }
            ),
        )
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
            _append_customer_history(
                customer, f"Orden de reparación #{order.id} actualizada")
            db.add(customer)
            updated_fields["customer_id"] = customer.id
        else:
            order.customer_id = None
            updated_fields["customer_id"] = None
    if payload.customer_name is not None:
        order.customer_name = payload.customer_name
        updated_fields["customer_name"] = payload.customer_name
    if payload.customer_contact is not None:
        order.customer_contact = payload.customer_contact
        updated_fields["customer_contact"] = payload.customer_contact
    if payload.technician_name is not None:
        order.technician_name = payload.technician_name
        updated_fields["technician_name"] = payload.technician_name
    if payload.damage_type is not None:
        order.damage_type = payload.damage_type
        updated_fields["damage_type"] = payload.damage_type
    if payload.diagnosis is not None:
        order.diagnosis = payload.diagnosis
        updated_fields["diagnosis"] = payload.diagnosis
    if payload.device_model is not None:
        order.device_model = payload.device_model
        updated_fields["device_model"] = payload.device_model
    if payload.imei is not None:
        order.imei = payload.imei
        updated_fields["imei"] = payload.imei
    if payload.device_description is not None:
        order.device_description = payload.device_description
        updated_fields["device_description"] = payload.device_description
    if payload.notes is not None:
        order.notes = payload.notes
        updated_fields["notes"] = payload.notes
    if payload.status is not None and payload.status != order.status:
        order.status = payload.status
        updated_fields["status"] = payload.status.value
        if payload.status in {
            models.RepairStatus.ENTREGADO,
            models.RepairStatus.CANCELADO,
        }:  # // [PACK37-backend]
            order.delivered_at = datetime.utcnow()
        elif payload.status in {models.RepairStatus.PENDIENTE, models.RepairStatus.EN_PROCESO}:
            order.delivered_at = None
    if payload.labor_cost is not None:
        order.labor_cost = _to_decimal(payload.labor_cost).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
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
    with transactional_session(db):
        order.total_cost = (order.labor_cost + order.parts_cost).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        db.add(order)
        flush_session(db)
        db.refresh(order)

        if updated_fields:
            if reason is not None:
                updated_fields["reason"] = reason
            _log_action(
                db,
                action="repair_order_updated",
                entity_type="repair_order",
                entity_id=str(order.id),
                performed_by_id=performed_by_id,
                details=json.dumps(updated_fields),
            )
            db.refresh(order)
        enqueue_sync_outbox(
            db,
            entity_type="repair_order",
            entity_id=str(order.id),
            operation="UPSERT",
            payload=_repair_payload(order),
        )
    return order


def append_repair_parts(  # // [PACK37-backend]
    db: Session,
    order_id: int,
    parts_payload: list[schemas.RepairOrderPartPayload],
    *,
    performed_by_id: int | None,
    reason: str | None,
) -> models.RepairOrder:
    order = get_repair_order(db, order_id)
    if not parts_payload:
        return order

    def _payload_key(value: schemas.RepairOrderPartPayload) -> tuple[int, str, str]:
        source = models.RepairPartSource(value.source)
        part_name = (value.part_name or "").strip().lower()
        return (value.device_id or 0, part_name, source.value)

    existing_payloads: dict[tuple[int, str, str],
                            schemas.RepairOrderPartPayload] = {}
    for part in order.parts:
        source = part.source or models.RepairPartSource.STOCK
        existing_payloads[(part.device_id or 0, (part.part_name or "").strip().lower(), source.value)] = (
            schemas.RepairOrderPartPayload(
                device_id=part.device_id,
                part_name=part.part_name,
                source=source,
                quantity=part.quantity,
                unit_cost=Decimal(part.unit_cost),
            )
        )

    for payload in parts_payload:
        normalized = schemas.RepairOrderPartPayload(
            device_id=payload.device_id,
            part_name=payload.part_name,
            source=payload.source,
            quantity=payload.quantity,
            unit_cost=payload.unit_cost,
        )
        key = _payload_key(normalized)
        previous = existing_payloads.get(key)
        if previous:
            quantity = previous.quantity + normalized.quantity
            unit_cost = normalized.unit_cost or previous.unit_cost
            part_name = normalized.part_name or previous.part_name
            existing_payloads[key] = schemas.RepairOrderPartPayload(
                device_id=previous.device_id,
                part_name=part_name,
                source=previous.source,
                quantity=quantity,
                unit_cost=unit_cost,
            )
        else:
            existing_payloads[key] = normalized

    merged = list(existing_payloads.values())
    update_payload = schemas.RepairOrderUpdate(parts=merged)
    return update_repair_order(
        db,
        order_id,
        update_payload,
        performed_by_id=performed_by_id,
        reason=reason,
    )


def remove_repair_part(  # // [PACK37-backend]
    db: Session,
    order_id: int,
    part_id: int,
    *,
    performed_by_id: int | None,
    reason: str | None,
) -> models.RepairOrder:
    order = get_repair_order(db, order_id)
    target = next((part for part in order.parts if part.id == part_id), None)
    if target is None:
        raise LookupError("repair_part_not_found")

    remaining = [
        schemas.RepairOrderPartPayload(
            device_id=part.device_id,
            part_name=part.part_name,
            source=part.source or models.RepairPartSource.STOCK,
            quantity=part.quantity,
            unit_cost=Decimal(part.unit_cost),
        )
        for part in order.parts
        if part.id != part_id
    ]
    update_payload = schemas.RepairOrderUpdate(parts=remaining)
    return update_repair_order(
        db,
        order_id,
        update_payload,
        performed_by_id=performed_by_id,
        reason=reason,
    )


def close_repair_order(  # // [PACK37-backend]
    db: Session,
    order_id: int,
    close_payload: schemas.RepairOrderCloseRequest | None,
    *,
    performed_by_id: int | None,
    reason: str | None,
) -> models.RepairOrder:
    payload = schemas.RepairOrderUpdate(
        status=models.RepairStatus.ENTREGADO,
        labor_cost=close_payload.labor_cost if close_payload else None,
        parts=close_payload.parts if close_payload else None,
    )
    return update_repair_order(
        db,
        order_id,
        payload,
        performed_by_id=performed_by_id,
        reason=reason,
    )


def delete_repair_order(
    db: Session,
    order_id: int,
    *,
    performed_by_id: int | None,
    reason: str | None = None,
) -> None:
    order = get_repair_order(db, order_id)
    with transactional_session(db):
        for part in list(order.parts):
            device = get_device(db, order.store_id, part.device_id)
            _register_inventory_movement(
                db,
                store_id=order.store_id,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=part.quantity,
                comment=reason or f"Cancelación reparación #{order.id}",
                performed_by_id=performed_by_id,
                reference_type="repair_order",
                reference_id=str(order.id),
            )
        _recalculate_store_inventory_value(db, order.store_id)
        db.delete(order)
        flush_session(db)

        _log_action(
            db,
            action="repair_order_deleted",
            entity_type="repair_order",
            entity_id=str(order_id),
            performed_by_id=performed_by_id,
            details=json.dumps({"reason": reason}),
        )
        enqueue_sync_outbox(
            db,
            entity_type="repair_order",
            entity_id=str(order_id),
            operation="DELETE",
            payload={"id": order_id},
        )


def refresh_expired_warranties(db: Session) -> int:
    today = date.today()
    statement = (
        select(models.WarrantyAssignment)
        .options(
            joinedload(models.WarrantyAssignment.sale_item)
        )
        .where(
            models.WarrantyAssignment.status == models.WarrantyStatus.ACTIVA,
            models.WarrantyAssignment.expiration_date < today,
        )
    )
    expired_assignments = list(db.scalars(statement).unique())
    if not expired_assignments:
        return 0

    for assignment in expired_assignments:
        assignment.status = models.WarrantyStatus.VENCIDA
        if assignment.sale_item:
            assignment.sale_item.warranty_status = models.WarrantyStatus.VENCIDA
        db.add(assignment)

    flush_session(db)
    return len(expired_assignments)


def list_warranty_assignments(
    db: Session,
    *,
    store_id: int | None = None,
    status: models.WarrantyStatus | None = None,
    query: str | None = None,
    expiring_before: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.WarrantyAssignment]:
    refresh_expired_warranties(db)

    statement = (
        select(models.WarrantyAssignment)
        .join(models.WarrantyAssignment.sale_item)
        .join(models.SaleItem.sale)
        .join(models.WarrantyAssignment.device)
        .options(
            joinedload(models.WarrantyAssignment.device),
            joinedload(models.WarrantyAssignment.sale_item)
            .joinedload(models.SaleItem.sale)
            .joinedload(models.Sale.customer),
            joinedload(models.WarrantyAssignment.claims),
        )
        .order_by(models.WarrantyAssignment.activation_date.desc(), models.WarrantyAssignment.id.desc())
    )

    if store_id is not None:
        statement = statement.where(models.Sale.store_id == store_id)
    if status is not None:
        statement = statement.where(models.WarrantyAssignment.status == status)
    if expiring_before is not None:
        statement = statement.where(
            models.WarrantyAssignment.expiration_date <= expiring_before
        )
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.Device.name).like(normalized),
                func.lower(models.Device.sku).like(normalized),
                func.lower(models.Device.imei).like(normalized),
                func.lower(models.Device.serial).like(normalized),
                func.lower(models.WarrantyAssignment.serial_number).like(normalized),
                func.lower(models.Sale.customer_name).like(normalized),
                cast(models.Sale.id, String).like(f"%{query.strip()}%"),
            )
        )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)

    return list(db.scalars(statement).unique())


def get_warranty_assignment(
    db: Session, assignment_id: int
) -> models.WarrantyAssignment:
    refresh_expired_warranties(db)
    statement = (
        select(models.WarrantyAssignment)
        .where(models.WarrantyAssignment.id == assignment_id)
        .options(
            joinedload(models.WarrantyAssignment.device),
            joinedload(models.WarrantyAssignment.sale_item)
            .joinedload(models.SaleItem.sale)
            .joinedload(models.Sale.customer),
            joinedload(models.WarrantyAssignment.claims),
        )
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("warranty_assignment_not_found") from exc


def register_warranty_claim(
    db: Session,
    assignment_id: int,
    payload: schemas.WarrantyClaimCreate,
    *,
    performed_by_id: int | None,
    reason: str | None,
) -> models.WarrantyAssignment:
    assignment = get_warranty_assignment(db, assignment_id)
    if assignment.status == models.WarrantyStatus.VENCIDA:
        raise ValueError("warranty_expired")

    with transactional_session(db):
        claim = models.WarrantyClaim(
            assignment_id=assignment.id,
            claim_type=models.WarrantyClaimType(payload.claim_type),
            status=models.WarrantyClaimStatus.ABIERTO,
            notes=payload.notes,
            performed_by_id=performed_by_id,
        )
        if payload.repair_order:
            repair_order = create_repair_order(
                db,
                payload.repair_order,
                performed_by_id=performed_by_id,
                reason=reason,
            )
            claim.repair_order_id = repair_order.id
            claim.status = models.WarrantyClaimStatus.EN_PROCESO
        assignment.claims.append(claim)
        assignment.status = models.WarrantyStatus.RECLAMO
        if assignment.sale_item:
            assignment.sale_item.warranty_status = models.WarrantyStatus.RECLAMO
        db.add(claim)
        db.add(assignment)
        flush_session(db)

    return get_warranty_assignment(db, assignment_id)


def update_warranty_claim_status(
    db: Session,
    claim_id: int,
    payload: schemas.WarrantyClaimStatusUpdate,
    *,
    performed_by_id: int | None,
) -> models.WarrantyClaim:
    statement = (
        select(models.WarrantyClaim)
        .where(models.WarrantyClaim.id == claim_id)
        .options(
            joinedload(models.WarrantyClaim.assignment)
            .joinedload(models.WarrantyAssignment.sale_item)
        )
    )
    try:
        claim = db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("warranty_claim_not_found") from exc

    new_status = models.WarrantyClaimStatus(payload.status)

    with transactional_session(db):
        claim.status = new_status
        if payload.notes is not None:
            claim.notes = payload.notes
        if payload.repair_order_id is not None:
            claim.repair_order_id = payload.repair_order_id
        if new_status in {
            models.WarrantyClaimStatus.RESUELTO,
            models.WarrantyClaimStatus.CANCELADO,
        }:
            claim.resolved_at = datetime.utcnow()
        assignment = claim.assignment
        if assignment:
            if new_status == models.WarrantyClaimStatus.RESUELTO:
                assignment.status = models.WarrantyStatus.RESUELTA
                if assignment.sale_item:
                    assignment.sale_item.warranty_status = models.WarrantyStatus.RESUELTA
            elif new_status == models.WarrantyClaimStatus.CANCELADO:
                assignment.status = models.WarrantyStatus.ACTIVA
                if assignment.sale_item:
                    assignment.sale_item.warranty_status = models.WarrantyStatus.ACTIVA
            else:
                assignment.status = models.WarrantyStatus.RECLAMO
                if assignment.sale_item:
                    assignment.sale_item.warranty_status = models.WarrantyStatus.RECLAMO
            assignment.updated_at = datetime.utcnow()
            db.add(assignment)
        claim.performed_by_id = performed_by_id or claim.performed_by_id
        db.add(claim)

    return claim


def get_warranty_metrics(
    db: Session,
    *,
    store_id: int | None = None,
    horizon_days: int = 30,
) -> schemas.WarrantyMetrics:
    refresh_expired_warranties(db)
    filters: list[ColumnElement[bool]] = []
    if store_id is not None:
        filters.append(models.Sale.store_id == store_id)

    statement = (
        select(models.WarrantyAssignment)
        .join(models.WarrantyAssignment.sale_item)
        .join(models.SaleItem.sale)
        .options(joinedload(models.WarrantyAssignment.claims))
        .where(*filters)
    )
    assignments = list(db.scalars(statement).unique())

    total = len(assignments)
    active = sum(1 for a in assignments if a.status == models.WarrantyStatus.ACTIVA)
    expired = sum(1 for a in assignments if a.status == models.WarrantyStatus.VENCIDA)
    expiring_limit = date.today() + timedelta(days=max(horizon_days, 0))
    expiring = sum(
        1
        for a in assignments
        if a.status == models.WarrantyStatus.ACTIVA
        and a.expiration_date <= expiring_limit
    )
    claims_open = 0
    claims_resolved = 0
    total_days = 0
    for assignment in assignments:
        coverage_days = max((assignment.expiration_date - assignment.activation_date).days, 0)
        total_days += coverage_days
        for claim in assignment.claims:
            if claim.status in {
                models.WarrantyClaimStatus.ABIERTO,
                models.WarrantyClaimStatus.EN_PROCESO,
            }:
                claims_open += 1
            if claim.status == models.WarrantyClaimStatus.RESUELTO:
                claims_resolved += 1

    average_days = float(total_days / total) if total else 0.0
    return schemas.WarrantyMetrics(
        total_assignments=total,
        active_assignments=active,
        expired_assignments=expired,
        claims_open=claims_open,
        claims_resolved=claims_resolved,
        expiring_soon=expiring,
        average_coverage_days=round(average_days, 2),
        generated_at=datetime.utcnow(),
    )


def list_sales(
    db: Session,
    *,
    store_id: int | None = None,
    limit: int | None = 50,
    offset: int = 0,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    customer_id: int | None = None,
    performed_by_id: int | None = None,
    product_id: int | None = None,
    query: str | None = None,
) -> list[models.Sale]:
    statement = (
        select(models.Sale)
        .options(
            joinedload(models.Sale.store),
            joinedload(models.Sale.items).joinedload(models.SaleItem.device),
            joinedload(models.Sale.returns),
            joinedload(models.Sale.customer).joinedload(
                models.Customer.loyalty_account
            ),
            joinedload(models.Sale.cash_session),
            joinedload(models.Sale.performed_by),
            joinedload(models.Sale.loyalty_transactions),
        )
        .order_by(models.Sale.created_at.desc())
    )
    if store_id is not None:
        statement = statement.where(models.Sale.store_id == store_id)
    if customer_id is not None:
        statement = statement.where(models.Sale.customer_id == customer_id)
    if performed_by_id is not None:
        statement = statement.where(
            models.Sale.performed_by_id == performed_by_id)
    if date_from is not None or date_to is not None:
        start, end = _normalize_date_range(date_from, date_to)
        statement = statement.where(
            models.Sale.created_at >= start, models.Sale.created_at <= end
        )

    joined_items = False
    if product_id is not None or query:
        statement = statement.join(models.Sale.items)
        joined_items = True
    if query:
        normalized = f"%{query.lower()}%"
        if not joined_items:
            statement = statement.join(models.Sale.items)
            joined_items = True
        statement = statement.join(models.SaleItem.device)
        statement = statement.where(
            or_(
                func.lower(models.Device.sku).like(normalized),
                func.lower(models.Device.name).like(normalized),
                func.lower(models.Device.modelo).like(normalized),
                func.lower(models.Device.imei).like(normalized),
                func.lower(models.Device.serial).like(normalized),
            )
        )
    if product_id is not None:
        statement = statement.where(models.SaleItem.device_id == product_id)
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    sales = list(db.scalars(statement).unique())
    _attach_last_audit_trails(
        db,
        entity_type="sale",
        records=sales,
    )
    return sales


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
        sale = db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("sale_not_found") from exc

    _attach_last_audit_trails(
        db,
        entity_type="sale",
        records=[sale],
    )
    return sale


def _extract_sale_id(value: object | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.isdigit():
            return int(normalized)
        digits = re.findall(r"\d+", normalized)
        if digits:
            try:
                return int(digits[-1])
            except ValueError:
                return None
    return None


def _parse_qr_payload(raw: str | None) -> dict[str, object] | None:
    if not raw:
        return None
    normalized = raw.strip()
    if not normalized:
        return None

    candidates = [normalized]
    try:
        decoded = base64.b64decode(normalized).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        decoded = None
    if decoded and decoded not in candidates:
        candidates.append(decoded)

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _load_sales_for_statement(db: Session, statement: Select, *, limit: int) -> list[models.Sale]:
    final_statement = statement.limit(limit)
    sales = list(db.scalars(final_statement).unique())
    _attach_last_audit_trails(
        db,
        entity_type="sale",
        records=sales,
    )
    return sales


def search_sales_history(
    db: Session,
    *,
    ticket: str | None = None,
    date_value: date | None = None,
    customer: str | None = None,
    qr: str | None = None,
    limit: int = 25,
) -> schemas.SaleHistorySearchResponse:
    bucket_ticket: list[models.Sale] = []
    bucket_date: list[models.Sale] = []
    bucket_customer: list[models.Sale] = []
    bucket_qr: list[models.Sale] = []

    if ticket:
        sale_id = _extract_sale_id(ticket)
        if sale_id:
            try:
                bucket_ticket = [get_sale(db, sale_id)]
            except LookupError:
                bucket_ticket = []

    if date_value is not None:
        start_dt = datetime.combine(date_value, datetime.min.time()).replace(tzinfo=None)
        end_dt = datetime.combine(date_value, datetime.max.time()).replace(tzinfo=None)
        bucket_date = list_sales(
            db,
            date_from=start_dt,
            date_to=end_dt,
            limit=limit,
        )

    if customer:
        normalized = f"%{customer.strip().lower()}%"
        if normalized.strip("%"):
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
                .outerjoin(models.Customer)
                .where(
                    or_(
                        func.lower(models.Sale.customer_name).like(normalized),
                        func.lower(models.Customer.name).like(normalized),
                        func.lower(models.Customer.contact_name).like(normalized),
                    )
                )
                .order_by(models.Sale.created_at.desc())
            )
            bucket_customer = _load_sales_for_statement(db, statement, limit=limit)

    if qr:
        payload = _parse_qr_payload(qr)
        sale_id = None
        if payload:
            sale_id = _extract_sale_id(payload.get("sale_id"))
            if sale_id is None:
                sale_id = _extract_sale_id(payload.get("doc"))
        if sale_id:
            try:
                bucket_qr = [get_sale(db, sale_id)]
            except LookupError:
                bucket_qr = []

    return schemas.SaleHistorySearchResponse(
        by_ticket=bucket_ticket,
        by_date=bucket_date,
        by_customer=bucket_customer,
        by_qr=bucket_qr,
    )


def _normalize_reservation_reason(reason: str | None) -> str:
    normalized = (reason or "").strip()
    if len(normalized) < 5:
        raise ValueError("reservation_reason_required")
    return normalized[:255]


def _active_reservations_by_device(
    db: Session,
    *,
    store_id: int,
    device_ids: Iterable[int] | None = None,
) -> dict[int, int]:
    ids = set(device_ids or [])
    now = datetime.utcnow()
    statement = (
        select(
            models.InventoryReservation.device_id,
            func.coalesce(func.sum(models.InventoryReservation.quantity), 0).label(
                "reserved"
            ),
        )
        .where(models.InventoryReservation.store_id == store_id)
        .where(models.InventoryReservation.status == models.InventoryState.RESERVADO)
        .where(models.InventoryReservation.expires_at > now)
        .group_by(models.InventoryReservation.device_id)
    )
    if ids:
        statement = statement.where(models.InventoryReservation.device_id.in_(ids))
    rows = db.execute(statement).all()
    reserved_map: dict[int, int] = {}
    for row in rows:
        device_id = int(row.device_id)
        reserved_value = int(row.reserved or 0)
        reserved_map[device_id] = reserved_value
    return reserved_map


def expire_reservations(
    db: Session,
    *,
    store_id: int | None = None,
    device_ids: Iterable[int] | None = None,
) -> int:
    now = datetime.utcnow()
    ids = set(device_ids or [])
    statement = select(models.InventoryReservation).where(
        models.InventoryReservation.status == models.InventoryState.RESERVADO,
        models.InventoryReservation.expires_at <= now,
    )
    if store_id is not None:
        statement = statement.where(models.InventoryReservation.store_id == store_id)
    if ids:
        statement = statement.where(models.InventoryReservation.device_id.in_(ids))
    expirations = list(db.scalars(statement).unique())
    if not expirations:
        return 0

    reason = "Expiración automática"
    for reservation in expirations:
        reservation.status = models.InventoryState.EXPIRADO
        reservation.resolution_reason = reservation.resolution_reason or reason
        reservation.resolved_at = now
        reservation.quantity = 0
        if reservation.device and (reservation.device.imei or reservation.device.serial):
            reservation.device.estado = "disponible"
    return len(expirations)


def get_inventory_reservation(
    db: Session, reservation_id: int
) -> models.InventoryReservation:
    reservation = db.get(models.InventoryReservation, reservation_id)
    if reservation is None:
        raise LookupError("reservation_not_found")
    return reservation


def list_inventory_reservations(
    db: Session,
    *,
    store_id: int | None = None,
    device_id: int | None = None,
    status: models.InventoryState | None = None,
    include_expired: bool = False,
) -> list[models.InventoryReservation]:
    statement = (
        select(models.InventoryReservation)
        .options(
            joinedload(models.InventoryReservation.device),
            joinedload(models.InventoryReservation.store),
        )
        .order_by(models.InventoryReservation.created_at.desc())
    )
    now = datetime.utcnow()
    if store_id is not None:
        statement = statement.where(models.InventoryReservation.store_id == store_id)
    if device_id is not None:
        statement = statement.where(models.InventoryReservation.device_id == device_id)
    if status is not None:
        statement = statement.where(models.InventoryReservation.status == status)
    if not include_expired:
        statement = statement.where(
            or_(
                models.InventoryReservation.status != models.InventoryState.RESERVADO,
                models.InventoryReservation.expires_at > now,
            )
        )
    return list(db.scalars(statement).unique())


def create_reservation(
    db: Session,
    *,
    store_id: int,
    device_id: int,
    quantity: int,
    expires_at: datetime,
    reserved_by_id: int | None,
    reason: str,
) -> models.InventoryReservation:
    if quantity <= 0:
        raise ValueError("reservation_invalid_quantity")
    if expires_at <= datetime.utcnow():
        raise ValueError("reservation_invalid_expiration")

    normalized_reason = _normalize_reservation_reason(reason)
    store = get_store(db, store_id)
    device = get_device(db, store_id, device_id)

    expire_reservations(db, store_id=store.id, device_ids=[device.id])
    active_reserved = _active_reservations_by_device(
        db, store_id=store.id, device_ids=[device.id]
    ).get(device.id, 0)
    available_quantity = device.quantity - active_reserved
    if available_quantity < quantity:
        raise ValueError("reservation_insufficient_stock")
    if device.imei or device.serial:
        if quantity != 1:
            raise ValueError("reservation_requires_single_unit")
        if device.estado and device.estado.lower() == "vendido":
            raise ValueError("reservation_device_unavailable")

    reservation = models.InventoryReservation(
        store_id=store.id,
        device_id=device.id,
        reserved_by_id=reserved_by_id,
        initial_quantity=quantity,
        quantity=quantity,
        status=models.InventoryState.RESERVADO,
        reason=normalized_reason,
        expires_at=expires_at,
    )

    with transactional_session(db):
        db.add(reservation)
        if device.imei or device.serial:
            device.estado = "reservado"
        flush_session(db)
        db.refresh(reservation)
        details = json.dumps(
            {
                "store_id": store.id,
                "device_id": device.id,
                "quantity": quantity,
                "expires_at": expires_at.isoformat(),
            }
        )
        _log_action(
            db,
            action="inventory_reservation_created",
            entity_type="inventory_reservation",
            entity_id=str(reservation.id),
            performed_by_id=reserved_by_id,
            details=details,
        )
    return reservation


def renew_reservation(
    db: Session,
    reservation_id: int,
    *,
    expires_at: datetime,
    performed_by_id: int | None,
    reason: str,
) -> models.InventoryReservation:
    reservation = get_inventory_reservation(db, reservation_id)
    if reservation.status != models.InventoryState.RESERVADO:
        raise ValueError("reservation_not_active")
    if expires_at <= datetime.utcnow():
        raise ValueError("reservation_invalid_expiration")

    _ = _normalize_reservation_reason(reason)

    with transactional_session(db):
        reservation.expires_at = expires_at
        reservation.updated_at = datetime.utcnow()
        flush_session(db)
        details = json.dumps(
            {
                "expires_at": expires_at.isoformat(),
                "reason": reason,
            }
        )
        _log_action(
            db,
            action="inventory_reservation_renewed",
            entity_type="inventory_reservation",
            entity_id=str(reservation.id),
            performed_by_id=performed_by_id,
            details=details,
        )
        db.refresh(reservation)
    return reservation


def release_reservation(
    db: Session,
    reservation_id: int,
    *,
    performed_by_id: int | None,
    reason: str | None = None,
    target_state: models.InventoryState = models.InventoryState.CANCELADO,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> models.InventoryReservation:
    if target_state not in {
        models.InventoryState.CANCELADO,
        models.InventoryState.CONSUMIDO,
    }:
        raise ValueError("reservation_invalid_transition")

    reservation = get_inventory_reservation(db, reservation_id)
    if reservation.status != models.InventoryState.RESERVADO:
        raise ValueError("reservation_not_active")

    normalized_reason = (reason or "").strip() or None
    now = datetime.utcnow()

    with transactional_session(db):
        reservation.status = target_state
        reservation.resolved_by_id = performed_by_id
        reservation.resolution_reason = normalized_reason
        reservation.resolved_at = now
        reservation.reference_type = reference_type
        reservation.reference_id = reference_id
        reservation.quantity = 0
        if target_state == models.InventoryState.CONSUMIDO:
            reservation.consumed_at = now
        else:
            if reservation.device and (reservation.device.imei or reservation.device.serial):
                reservation.device.estado = "disponible"
        flush_session(db)

        details = json.dumps(
            {
                "target_state": target_state.value,
                "reason": normalized_reason,
                "reference_type": reference_type,
                "reference_id": reference_id,
            }
        )
        action = (
            "inventory_reservation_consumed"
            if target_state == models.InventoryState.CONSUMIDO
            else "inventory_reservation_released"
        )
        _log_action(
            db,
            action=action,
            entity_type="inventory_reservation",
            entity_id=str(reservation.id),
            performed_by_id=performed_by_id,
            details=details,
        )
        db.refresh(reservation)
    return reservation


def _ensure_device_available_for_sale(
    device: models.Device, quantity: int, *, active_reserved: int = 0
) -> None:
    if quantity <= 0:
        raise ValueError("sale_invalid_quantity")
    effective_stock = device.quantity - active_reserved
    if effective_stock < quantity:
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
    device: models.Device,
    quantity: int,
    *,
    reserved_quantity: int = 0,
    active_reserved: int = 0,
) -> None:
    if quantity <= 0:
        raise ValueError("sale_invalid_quantity")
    effective_stock = max(device.quantity - active_reserved, 0)
    available_quantity = effective_stock + reserved_quantity
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
    active_reservations: dict[int, int] | None = None,
) -> tuple[Decimal, Decimal]:
    gross_total = Decimal("0")
    total_discount = Decimal("0")
    reserved = reserved_quantities or {}
    blocked = active_reservations or {}

    for item in items:
        device = get_device(db, store_id, item.device_id)
        reserved_quantity = reserved.get(device.id, 0)
        _ensure_device_available_for_preview(
            device,
            item.quantity,
            reserved_quantity=reserved_quantity,
            active_reserved=blocked.get(device.id, 0),
        )

        # // [PACK34-pricing]
        override_price = getattr(item, "unit_price_override", None)
        if override_price is not None:
            line_unit_price = _to_decimal(override_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            line_unit_price = _to_decimal(device.unit_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        quantity_decimal = _to_decimal(item.quantity)
        line_total = (line_unit_price * quantity_decimal).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        gross_total += line_total

        line_discount_percent = _to_decimal(
            getattr(item, "discount_percent", None))
        if line_discount_percent == Decimal("0"):
            line_discount_percent = sale_discount_percent
        discount_fraction = line_discount_percent / Decimal("100")
        line_discount_amount = (line_total * discount_fraction).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_discount += line_discount_amount

    return gross_total, total_discount


def _build_sale_movement_comment(
    sale: models.Sale, device: models.Device, reason: str | None
) -> str:
    segments = [f"Venta #{sale.id}"]
    if device.sku:
        segments.append(f"SKU {device.sku}")
    if reason:
        segments.append(reason)
    return " — ".join(segments)[:255]


def _build_sale_return_comment(
    sale: models.Sale,
    device: models.Device,
    reason: str | None,
    *,
    disposition: schemas.ReturnDisposition | None = None,
    warehouse_name: str | None = None,
) -> str:
    segments = [f"Devolución venta #{sale.id}"]
    if device.sku:
        segments.append(f"SKU {device.sku}")
    if reason:
        segments.append(reason)
    if disposition is not None:
        segments.append(f"estado={disposition.value}")
    if warehouse_name:
        segments.append(f"almacen={warehouse_name}")
    return " — ".join(segments)[:255]


def _apply_sale_items(
    db: Session,
    sale: models.Sale,
    items: list[schemas.SaleItemCreate],
    *,
    store: models.Store,
    sale_discount_percent: Decimal,
    performed_by_id: int,
    reason: str | None,
    reservations: dict[int, models.InventoryReservation] | None = None,
    active_reservations: dict[int, int] | None = None,
) -> tuple[Decimal, Decimal]:
    gross_total = Decimal("0")
    total_discount = Decimal("0")
    reservation_map = reservations or {}
    blocked_reserved = dict(active_reservations or {})
    consumed: list[models.InventoryReservation] = []
    batch_consumption: dict[str, int] = {}

    for item in items:
        device = get_device(db, sale.store_id, item.device_id)
        reservation_id = getattr(item, "reservation_id", None)
        allowance = 0
        reservation: models.InventoryReservation | None = None
        if reservation_id is not None:
            reservation = reservation_map.get(reservation_id)
            if reservation is None:
                raise ValueError("reservation_not_active")
            if reservation.device_id != device.id:
                raise ValueError("reservation_device_mismatch")
            allowance = reservation.quantity
        active_reserved = max(blocked_reserved.get(device.id, 0) - allowance, 0)
        _ensure_device_available_for_sale(
            device, item.quantity, active_reserved=active_reserved
        )
        blocked_reserved[device.id] = active_reserved

        # // [PACK34-pricing]
        override_price = getattr(item, "unit_price_override", None)
        if override_price is not None:
            line_unit_price = _to_decimal(override_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            line_unit_price = _to_decimal(device.unit_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        quantity_decimal = _to_decimal(item.quantity)
        line_total = (line_unit_price * quantity_decimal).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        gross_total += line_total

        line_discount_percent = _to_decimal(
            getattr(item, "discount_percent", None))
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

        sale_item = models.SaleItem(
            sale_id=sale.id,
            device_id=device.id,
            quantity=item.quantity,
            unit_price=line_unit_price,
            discount_amount=line_discount_amount,
            total_line=net_line_total,
            reservation_id=reservation.id if reservation is not None else None,
        )
        sale_item.warranty_status = models.WarrantyStatus.SIN_GARANTIA
        sale.items.append(sale_item)

        batch_code = getattr(item, "batch_code", None)
        movement_comment = _build_sale_movement_comment(sale, device, reason)
        if batch_code:
            batch_comment = batch_code.strip()
            if batch_comment:
                movement_comment = f"{movement_comment} | Lote {batch_comment}"[:255]

        movement = _register_inventory_movement(
            db,
            store_id=sale.store_id,
            device_id=device.id,
            movement_type=models.MovementType.OUT,
            quantity=item.quantity,
            comment=movement_comment,
            performed_by_id=performed_by_id,
            source_store_id=sale.store_id,
            reference_type="sale",
            reference_id=str(sale.id),
        )
        movement_device = movement.device or device
        if movement_device.quantity <= 0:
            _mark_device_sold(movement_device)
        if batch_code:
            batch = consume_supplier_batch(
                db,
                store=store,
                device=movement_device,
                batch_code=batch_code,
                quantity=item.quantity,
            )
            if batch.supplier and batch.supplier.name:
                movement_device.proveedor = batch.supplier.name
            movement_device.lote = batch.batch_code
            db.add(movement_device)
            batch_consumption[batch.batch_code] = (
                batch_consumption.get(batch.batch_code, 0) + item.quantity
            )
        if reservation is not None:
            consumed.append(reservation)

    for reservation in consumed:
        release_reservation(
            db,
            reservation.id,
            performed_by_id=performed_by_id,
            reason=reason,
            target_state=models.InventoryState.CONSUMIDO,
            reference_type="sale",
            reference_id=str(sale.id),
        )
    sale.__dict__.setdefault("_batch_consumption", batch_consumption)
    return gross_total, total_discount


def _add_months_to_date(base_date: date, months: int) -> date:
    if months <= 0:
        return base_date
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(base_date.day, last_day)
    return date(year, month, day)


def _resolve_warranty_serial(device: models.Device) -> str | None:
    identifier = (device.imei or "").strip()
    if identifier:
        return identifier
    serial = (device.serial or "").strip()
    return serial or None


def _create_warranty_assignments(
    db: Session, sale: models.Sale
) -> list[models.WarrantyAssignment]:
    activation_dt = sale.created_at or datetime.utcnow()
    activation_date = activation_dt.date()
    assignments: list[models.WarrantyAssignment] = []

    for sale_item in sale.items:
        device = get_device(db, sale.store_id, sale_item.device_id)
        coverage_months = int(device.garantia_meses or 0)
        if coverage_months <= 0:
            sale_item.warranty_status = models.WarrantyStatus.SIN_GARANTIA
            continue
        expiration_date = _add_months_to_date(activation_date, coverage_months)
        assignment = models.WarrantyAssignment(
            sale_item_id=sale_item.id,
            device_id=device.id,
            coverage_months=coverage_months,
            activation_date=activation_date,
            expiration_date=expiration_date,
            status=models.WarrantyStatus.ACTIVA,
            serial_number=_resolve_warranty_serial(device),
        )
        sale_item.warranty_status = models.WarrantyStatus.ACTIVA
        db.add(assignment)
        assignments.append(assignment)

    if assignments:
        flush_session(db)
    return assignments


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

    store = get_store(db, payload.store_id)

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
    with transactional_session(db):
        db.add(sale)

        expire_reservations(db, store_id=sale.store_id, device_ids=[item.device_id for item in payload.items])
        reservation_map: dict[int, models.InventoryReservation] = {}
        reserved_allowances: dict[int, int] = {}
        device_ids = {item.device_id for item in payload.items}
        for item in payload.items:
            reservation_id = getattr(item, "reservation_id", None)
            if reservation_id is None:
                continue
            reservation = get_inventory_reservation(db, reservation_id)
            if reservation.store_id != sale.store_id:
                raise ValueError("reservation_store_mismatch")
            if reservation.device_id != item.device_id:
                raise ValueError("reservation_device_mismatch")
            if reservation.status != models.InventoryState.RESERVADO:
                raise ValueError("reservation_not_active")
            if reservation.quantity != item.quantity:
                raise ValueError("reservation_quantity_mismatch")
            if reservation.expires_at <= datetime.utcnow():
                raise ValueError("reservation_expired")
            reservation_map[reservation.id] = reservation
            reserved_allowances[item.device_id] = reserved_allowances.get(
                item.device_id, 0
            ) + reservation.quantity

        active_reserved_map = _active_reservations_by_device(
            db, store_id=sale.store_id, device_ids=device_ids
        )
        blocked_map: dict[int, int] = {}
        for device_id in device_ids:
            active_total = active_reserved_map.get(device_id, 0)
            allowance = reserved_allowances.get(device_id, 0)
            blocked_map[device_id] = max(active_total - allowance, 0)

        tax_value = _to_decimal(tax_rate)
        if tax_value < Decimal("0"):
            tax_value = Decimal("0")
        tax_fraction = tax_value / \
            Decimal("100") if tax_value else Decimal("0")

        try:
            preview_gross_total, preview_discount = _preview_sale_totals(
                db,
                sale.store_id,
                payload.items,
                sale_discount_percent=sale_discount_percent,
                reserved_quantities=reserved_allowances,
                active_reservations=blocked_map,
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

        flush_session(db)

        ledger_entry: models.CustomerLedgerEntry | None = None
        customer_to_sync: models.Customer | None = None

        gross_total, total_discount = _apply_sale_items(
            db,
            sale,
            payload.items,
            store=store,
            sale_discount_percent=sale_discount_percent,
            performed_by_id=performed_by_id,
            reason=reason,
            reservations=reservation_map,
            active_reservations=blocked_map,
        )

        subtotal = (gross_total - total_discount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        sale.subtotal_amount = subtotal
        tax_amount = (
            subtotal * tax_fraction).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sale.tax_amount = tax_amount
        sale.total_amount = (subtotal + tax_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        flush_session(db)
        _create_warranty_assignments(db, sale)

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
            customer_to_sync = customer

        flush_session(db)
        db.refresh(sale)
        if customer_to_sync:
            db.refresh(customer_to_sync)

        if customer_to_sync and sale.payment_method == models.PaymentMethod.CREDITO:
            enqueue_sync_outbox(
                db,
                entity_type="customer",
                entity_id=str(customer_to_sync.id),
                operation="UPSERT",
                payload=_customer_payload(customer_to_sync),
            )
        if ledger_entry:
            _sync_customer_ledger_entry(db, ledger_entry)

        batch_consumption = getattr(sale, "_batch_consumption", {})
        _log_action(
            db,
            action="sale_registered",
            entity_type="sale",
            entity_id=str(sale.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "store_id": sale.store_id,
                    "total_amount": float(sale.total_amount),
                    "reason": reason,
                    "batches": batch_consumption,
                }
            ),
        )
        sale.__dict__.pop("_batch_consumption", None)
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
    _attach_last_audit_trails(
        db,
        entity_type="sale",
        records=[sale],
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
    if any(getattr(item, "batch_code", None) for item in payload.items):
        raise ValueError("sale_batches_update_not_supported")

    previous_customer = sale.customer
    previous_payment_method = sale.payment_method
    previous_total_amount = _to_decimal(sale.total_amount)
    reserved_quantities: dict[int, int] = {}
    for existing_item in sale.items:
        reserved_quantities[existing_item.device_id] = (
            reserved_quantities.get(
                existing_item.device_id, 0) + existing_item.quantity
        )
    ledger_reversal: models.CustomerLedgerEntry | None = None
    ledger_new: models.CustomerLedgerEntry | None = None
    customers_to_sync: dict[int, models.Customer] = {}

    store = get_store(db, sale.store_id)

    with transactional_session(db):
        sale_discount_percent = _to_decimal(payload.discount_percent or 0)
        new_payment_method = models.PaymentMethod(payload.payment_method)
        sale_status = (
            payload.status or sale.status or "COMPLETADA").strip() or "COMPLETADA"
        normalized_status = sale_status.upper()

        customer = None
        customer_name = payload.customer_name
        if payload.customer_id:
            customer = get_customer(db, payload.customer_id)
            customer_name = customer_name or customer.name

        expire_reservations(db, store_id=sale.store_id, device_ids=[item.device_id for item in payload.items])
        reservation_map: dict[int, models.InventoryReservation] = {}
        reserved_allowances: dict[int, int] = {}
        device_ids = {item.device_id for item in payload.items}
        for item in payload.items:
            reservation_id = getattr(item, "reservation_id", None)
            if reservation_id is None:
                continue
            reservation = get_inventory_reservation(db, reservation_id)
            if reservation.store_id != sale.store_id:
                raise ValueError("reservation_store_mismatch")
            if reservation.device_id != item.device_id:
                raise ValueError("reservation_device_mismatch")
            if reservation.status != models.InventoryState.RESERVADO:
                raise ValueError("reservation_not_active")
            if reservation.quantity != item.quantity:
                raise ValueError("reservation_quantity_mismatch")
            if reservation.expires_at <= datetime.utcnow():
                raise ValueError("reservation_expired")
            reservation_map[reservation.id] = reservation
            reserved_allowances[item.device_id] = reserved_allowances.get(
                item.device_id, 0
            ) + reservation.quantity

        combined_reserved = reserved_quantities.copy()
        for device_id, qty in reserved_allowances.items():
            combined_reserved[device_id] = combined_reserved.get(device_id, 0) + qty

        active_reserved_map = _active_reservations_by_device(
            db, store_id=sale.store_id, device_ids=device_ids
        )
        blocked_map: dict[int, int] = {}
        for device_id in device_ids:
            active_total = active_reserved_map.get(device_id, 0)
            allowance = reserved_allowances.get(device_id, 0)
            blocked_map[device_id] = max(active_total - allowance, 0)

        preview_gross_total, preview_discount = _preview_sale_totals(
            db,
            sale.store_id,
            payload.items,
            sale_discount_percent=sale_discount_percent,
            reserved_quantities=combined_reserved,
            active_reservations=blocked_map,
        )
        preview_subtotal = (preview_gross_total - preview_discount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        tax_value = _to_decimal(None)
        tax_fraction = tax_value / \
            Decimal("100") if tax_value else Decimal("0")
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
            movement = _register_inventory_movement(
                db,
                store_id=sale.store_id,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=existing_item.quantity,
                comment=reversal_comment,
                performed_by_id=performed_by_id,
                reference_type="sale",
                reference_id=str(sale.id),
            )
            movement_device = movement.device or device
            _restore_device_availability(movement_device)
        sale.items.clear()
        sale.__dict__.pop("_batch_consumption", None)
        flush_session(db)

        if (
            previous_customer
            and previous_payment_method == models.PaymentMethod.CREDITO
            and previous_total_amount > Decimal("0")
        ):
            updated_debt = (
                _to_decimal(previous_customer.outstanding_debt) -
                previous_total_amount
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
            store=store,
            sale_discount_percent=sale_discount_percent,
            performed_by_id=performed_by_id,
            reason=reason,
            reservations=reservation_map,
            active_reservations=blocked_map,
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
                    _to_decimal(target_customer.outstanding_debt) +
                    sale.total_amount
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

        flush_session(db)
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
        flush_session(db)
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
    _attach_last_audit_trails(
        db,
        entity_type="sale",
        records=[sale],
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

    with transactional_session(db):
        cancel_reason = reason or f"Anulación venta #{sale.id}"
        ledger_entry: models.CustomerLedgerEntry | None = None
        customer_to_sync: models.Customer | None = None
        credit_note: models.StoreCredit | None = None
        for item in sale.items:
            device = get_device(db, sale.store_id, item.device_id)
            movement = _register_inventory_movement(
                db,
                store_id=sale.store_id,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=item.quantity,
                comment=cancel_reason,
                performed_by_id=performed_by_id,
                reference_type="sale",
                reference_id=str(sale.id),
            )
            movement_device = movement.device or device
            if movement_device.quantity > 0:
                _restore_device_availability(movement_device)

        if sale.customer and sale.payment_method == models.PaymentMethod.CREDITO and sale.total_amount > Decimal("0"):
            updated_debt = (
                _to_decimal(sale.customer.outstanding_debt) -
                _to_decimal(sale.total_amount)
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

        if sale.invoice_reported and sale.total_amount > Decimal("0"):
            if sale.customer_id is None:
                raise ValueError("sale_reported_requires_customer")
            config = get_pos_config(db, sale.store_id)
            invoice_number = f"{config.invoice_prefix}-{sale.id:06d}"
            credit_request = schemas.StoreCreditIssueRequest(
                customer_id=sale.customer_id,
                amount=float(_to_decimal(sale.total_amount)),
                notes=f"Nota de crédito por anulación de la factura {invoice_number}",
                context={
                    "origin": "sale_cancellation",
                    "sale_id": sale.id,
                    "invoice_number": invoice_number,
                },
            )
            credit_note = issue_store_credit(
                db,
                credit_request,
                performed_by_id=performed_by_id,
                reason=cancel_reason,
            )
            sale.invoice_reported = False
            sale.invoice_annulled_at = datetime.utcnow()
            sale.invoice_credit_note_code = credit_note.code

        sale.status = "CANCELADA"
        _recalculate_store_inventory_value(db, sale.store_id)

        flush_session(db)
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
            details=json.dumps(
                {
                    "reason": cancel_reason,
                    "credit_note_code": credit_note.code if credit_note else None,
                }
            ),
        )
        flush_session(db)
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
    _attach_last_audit_trails(
        db,
        entity_type="sale",
        records=[sale],
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
    approval_required = False
    approval_reference: str | None = None
    approved_supervisor: models.User | None = None
    now_utc = datetime.now(timezone.utc)
    sale_created_at = sale.created_at
    if sale_created_at.tzinfo is None:
        sale_created_at = sale_created_at.replace(tzinfo=timezone.utc)
    else:
        sale_created_at = sale_created_at.astimezone(timezone.utc)
    limit_days = max(0, return_policy_settings.sale_without_supervisor_days)
    if (now_utc - sale_created_at) > timedelta(days=limit_days):
        approval_required = True
        approval = payload.approval
        if approval is None:
            raise PermissionError("sale_return_supervisor_required")
        supervisor = get_user_by_username(db, approval.supervisor_username)
        fallback_hash = return_policy_settings.supervisor_pin_hashes.get(
            approval.supervisor_username
        )
        if supervisor is None:
            if not fallback_hash:
                raise PermissionError("sale_return_supervisor_not_found")
            if not _verify_supervisor_pin_hash(fallback_hash, approval.pin):
                raise PermissionError("sale_return_invalid_supervisor_pin")
            approval_reference = approval.supervisor_username
        else:
            supervisor_roles = {supervisor.rol}
            supervisor_roles.update(
                role.role.name for role in supervisor.roles if role.role
            )
            if not return_policy_settings.has_authorizer_role(supervisor_roles):
                raise PermissionError("sale_return_supervisor_not_authorized")
            pin_hash = supervisor.supervisor_pin_hash or fallback_hash
            if not pin_hash:
                raise PermissionError("sale_return_supervisor_pin_not_configured")
            if not _verify_supervisor_pin_hash(pin_hash, approval.pin):
                raise PermissionError("sale_return_invalid_supervisor_pin")
            approved_supervisor = supervisor
            approval_reference = supervisor.username
    elif payload.approval is not None:
        approval_reference = payload.approval.supervisor_username

    non_sellable_dispositions = {
        schemas.ReturnDisposition.DEFECTUOSO,
        schemas.ReturnDisposition.NO_VENDIBLE,
        schemas.ReturnDisposition.REPARACION,
    }

    with transactional_session(db):
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
            previous_cost = _to_decimal(device.costo_unitario)
            disposition = item.disposition
            warehouse_id = item.warehouse_id
            if warehouse_id is not None and warehouse_id <= 0:
                raise ValueError("sale_return_invalid_warehouse")
            warehouse: models.Warehouse | None = None
            if warehouse_id is not None:
                warehouse = get_warehouse(db, warehouse_id)
                if warehouse.store_id != sale.store_id:
                    raise ValueError("sale_return_invalid_warehouse")
            if (
                warehouse is None
                and disposition in non_sellable_dispositions
                and settings.defective_returns_store_id
            ):
                try:
                    warehouse = get_warehouse(
                        db, settings.defective_returns_store_id, store_id=sale.store_id
                    )
                except LookupError:
                    warehouse = None

            movement = _register_inventory_movement(
                db,
                store_id=sale.store_id,
                device_id=item.device_id,
                movement_type=models.MovementType.IN,
                quantity=item.quantity,
                comment=_build_sale_return_comment(
                    sale,
                    device,
                    item.reason or reason,
                    disposition=disposition,
                    warehouse_name=warehouse.name if warehouse else None,
                ),
                performed_by_id=processed_by_id,
                source_warehouse_id=device.warehouse_id,
                warehouse_id=warehouse.id if warehouse else device.warehouse_id,
                unit_cost=_quantize_currency(previous_cost),
                reference_type="sale_return",
                reference_id=str(sale.id),
            )
            movement_device = movement.device or device
            if (
                disposition == schemas.ReturnDisposition.VENDIBLE
                and movement_device.quantity > 0
            ):
                _restore_device_availability(movement_device)
            elif movement_device.imei or movement_device.serial:
                movement_device.estado = "no_vendible"

            sale_return = models.SaleReturn(
                sale_id=sale.id,
                device_id=item.device_id,
                quantity=item.quantity,
                reason=item.reason,
                reason_category=item.category,
                disposition=disposition,
                warehouse_id=warehouse.id if warehouse else device.warehouse_id,
                processed_by_id=processed_by_id,
                approved_by_id=approved_supervisor.id if approved_supervisor else None,
            )
            db.add(sale_return)
            returns.append(sale_return)

            unit_refund = (sale_item.total_line / Decimal(sale_item.quantity)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            refund_total += (unit_refund * Decimal(item.quantity)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        _recalculate_store_inventory_value(db, sale.store_id)

        flush_session(db)
        for sale_return in returns:
            db.refresh(sale_return)

        _log_action(
            db,
            action="sale_return_registered",
            entity_type="sale",
            entity_id=str(sale.id),
            performed_by_id=processed_by_id,
            details=json.dumps(
                {
                    "items": [item.model_dump() for item in payload.items],
                    "reason": reason,
                    "approval": {
                        "required": approval_required,
                        "supervisor": approval_reference,
                    },
                }
            ),
        )
        flush_session(db)

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
            flush_session(db)
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


def _get_sale_return(db: Session, return_id: int) -> models.SaleReturn:
    statement = (
        select(models.SaleReturn)
        .options(
            joinedload(models.SaleReturn.sale).joinedload(models.Sale.store),
            joinedload(models.SaleReturn.device),
        )
        .where(models.SaleReturn.id == return_id)
    )
    result = db.scalars(statement).unique().first()
    if result is None:
        raise LookupError("sale_return_not_found")
    return result


def _get_purchase_return(db: Session, return_id: int) -> models.PurchaseReturn:
    statement = (
        select(models.PurchaseReturn)
        .options(
            joinedload(models.PurchaseReturn.order).joinedload(models.PurchaseOrder.store),
            joinedload(models.PurchaseReturn.device),
        )
        .where(models.PurchaseReturn.id == return_id)
    )
    result = db.scalars(statement).unique().first()
    if result is None:
        raise LookupError("purchase_return_not_found")
    return result


def _append_rma_history(
    db: Session,
    *,
    rma: models.RMARequest,
    status: models.RMAStatus,
    message: str | None,
    created_by_id: int | None,
) -> models.RMAEvent:
    event = models.RMAEvent(
        rma=rma,
        status=status,
        message=message,
        created_by_id=created_by_id,
    )
    db.add(event)
    flush_session(db)
    return event


def _rma_sync_payload(rma: models.RMARequest) -> dict[str, Any]:
    return {
        "id": rma.id,
        "sale_return_id": rma.sale_return_id,
        "purchase_return_id": rma.purchase_return_id,
        "store_id": rma.store_id,
        "device_id": rma.device_id,
        "status": rma.status.value,
        "disposition": rma.disposition.value,
        "notes": rma.notes,
        "repair_order_id": rma.repair_order_id,
        "replacement_sale_id": rma.replacement_sale_id,
    }


def create_rma_request(
    db: Session,
    payload: schemas.RMACreate,
    *,
    created_by_id: int,
) -> models.RMARequest:
    sale_return: models.SaleReturn | None = None
    purchase_return: models.PurchaseReturn | None = None
    if payload.sale_return_id:
        sale_return = _get_sale_return(db, payload.sale_return_id)
        store_id = sale_return.sale.store_id if sale_return.sale else sale_return.warehouse_id
        device_id = sale_return.device_id
    else:
        purchase_return = _get_purchase_return(db, payload.purchase_return_id or 0)
        order = purchase_return.order
        store_id = order.store_id if order else purchase_return.warehouse_id
        device_id = purchase_return.device_id

    if payload.repair_order_id is not None:
        get_repair_order(db, payload.repair_order_id)
    if payload.replacement_sale_id is not None:
        get_sale(db, payload.replacement_sale_id)

    with transactional_session(db):
        rma = models.RMARequest(
            sale_return_id=sale_return.id if sale_return else None,
            purchase_return_id=purchase_return.id if purchase_return else None,
            store_id=store_id,
            device_id=device_id,
            disposition=payload.disposition,
            notes=payload.notes,
            repair_order_id=payload.repair_order_id,
            replacement_sale_id=payload.replacement_sale_id,
            created_by_id=created_by_id,
        )
        db.add(rma)
        flush_session(db)
        _append_rma_history(
            db,
            rma=rma,
            status=models.RMAStatus.PENDIENTE,
            message="RMA creada",
            created_by_id=created_by_id,
        )
        enqueue_sync_outbox(
            db,
            entity_type="rma_request",
            entity_id=str(rma.id),
            operation="UPSERT",
            payload=_rma_sync_payload(rma),
        )
        db.refresh(rma)
        return rma


def get_rma_request(db: Session, rma_id: int) -> models.RMARequest:
    statement = (
        select(models.RMARequest)
        .options(
            joinedload(models.RMARequest.history).joinedload(models.RMAEvent.created_by),
            joinedload(models.RMARequest.sale_return).joinedload(models.SaleReturn.sale),
            joinedload(models.RMARequest.purchase_return).joinedload(models.PurchaseReturn.order),
        )
        .where(models.RMARequest.id == rma_id)
    )
    result = db.scalars(statement).unique().first()
    if result is None:
        raise LookupError("rma_request_not_found")
    return result


def _update_rma_status(
    db: Session,
    rma_id: int,
    *,
    status: models.RMAStatus,
    notes: str | None,
    repair_order_id: int | None,
    replacement_sale_id: int | None,
    actor_id: int,
    disposition: schemas.ReturnDisposition | None = None,
) -> models.RMARequest:
    rma = get_rma_request(db, rma_id)
    if rma.status == models.RMAStatus.CERRADA:
        raise ValueError("rma_request_closed")

    if repair_order_id is not None:
        get_repair_order(db, repair_order_id)
    if replacement_sale_id is not None:
        get_sale(db, replacement_sale_id)

    if status == models.RMAStatus.AUTORIZADA and rma.status != models.RMAStatus.PENDIENTE:
        raise ValueError("rma_request_invalid_status")
    if status == models.RMAStatus.EN_PROCESO and rma.status not in (
        models.RMAStatus.PENDIENTE,
        models.RMAStatus.AUTORIZADA,
    ):
        raise ValueError("rma_request_invalid_status")

    with transactional_session(db):
        rma.status = status
        if notes:
            rma.notes = notes
        if repair_order_id is not None:
            rma.repair_order_id = repair_order_id
        if replacement_sale_id is not None:
            rma.replacement_sale_id = replacement_sale_id
        if disposition is not None:
            rma.disposition = disposition

        if status == models.RMAStatus.AUTORIZADA:
            rma.authorized_by_id = actor_id
        elif status == models.RMAStatus.EN_PROCESO:
            rma.processed_by_id = actor_id
        elif status == models.RMAStatus.CERRADA:
            rma.closed_by_id = actor_id

        _append_rma_history(
            db,
            rma=rma,
            status=status,
            message=notes,
            created_by_id=actor_id,
        )
        enqueue_sync_outbox(
            db,
            entity_type="rma_request",
            entity_id=str(rma.id),
            operation="UPSERT",
            payload=_rma_sync_payload(rma),
        )
        db.refresh(rma)
        return rma


def authorize_rma_request(
    db: Session,
    rma_id: int,
    *,
    notes: str | None,
    actor_id: int,
) -> models.RMARequest:
    return _update_rma_status(
        db,
        rma_id,
        status=models.RMAStatus.AUTORIZADA,
        notes=notes,
        repair_order_id=None,
        replacement_sale_id=None,
        actor_id=actor_id,
    )


def process_rma_request(
    db: Session,
    rma_id: int,
    *,
    payload: schemas.RMAUpdate,
    actor_id: int,
) -> models.RMARequest:
    return _update_rma_status(
        db,
        rma_id,
        status=models.RMAStatus.EN_PROCESO,
        notes=payload.notes,
        repair_order_id=payload.repair_order_id,
        replacement_sale_id=payload.replacement_sale_id,
        actor_id=actor_id,
        disposition=payload.disposition,
    )


def close_rma_request(
    db: Session,
    rma_id: int,
    *,
    payload: schemas.RMAUpdate,
    actor_id: int,
) -> models.RMARequest:
    return _update_rma_status(
        db,
        rma_id,
        status=models.RMAStatus.CERRADA,
        notes=payload.notes,
        repair_order_id=payload.repair_order_id,
        replacement_sale_id=payload.replacement_sale_id,
        actor_id=actor_id,
        disposition=payload.disposition,
    )


def list_operations_history(
    db: Session,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    store_id: int | None = None,
    technician_id: int | None = None,
    limit: int | None = 50,
    offset: int = 0,
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
        purchase_stmt = purchase_stmt.where(
            models.PurchaseOrder.store_id == store_id)
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
    paginated_records = records[offset:] if offset else records[:]
    if limit is not None:
        paginated_records = paginated_records[:limit]

    technician_ids = {
        entry.technician_id
        for entry in paginated_records
        if entry.technician_id is not None and entry.technician_id in technicians
    }
    technicians_list = [
        schemas.OperationHistoryTechnician(
            id=tech_id, name=technicians[tech_id])
        for tech_id in sorted(technician_ids, key=lambda ident: technicians[ident].lower())
    ]

    return schemas.OperationsHistoryResponse(
        records=paginated_records,
        technicians=technicians_list,
    )


def list_cash_sessions(
    db: Session,
    *,
    store_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[models.CashRegisterSession]:
    statement = (
        select(models.CashRegisterSession)
        .where(models.CashRegisterSession.store_id == store_id)
        .order_by(models.CashRegisterSession.opened_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).unique())


def count_cash_sessions(db: Session, *, store_id: int) -> int:
    statement = select(func.count()).select_from(models.CashRegisterSession).where(
        models.CashRegisterSession.store_id == store_id
    )
    return int(db.scalar(statement) or 0)


def get_cash_session(db: Session, session_id: int) -> models.CashRegisterSession:
    statement = select(models.CashRegisterSession).where(
        models.CashRegisterSession.id == session_id)
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("cash_session_not_found") from exc


def get_open_cash_session(db: Session, *, store_id: int) -> models.CashRegisterSession:
    statement = (
        select(models.CashRegisterSession)
        .where(
            models.CashRegisterSession.store_id == store_id,
            models.CashRegisterSession.status == models.CashSessionStatus.ABIERTO,
        )
        .order_by(models.CashRegisterSession.opened_at.desc())
    )
    session = db.scalars(statement).first()
    if session is None:
        raise LookupError("cash_session_not_found")
    return session


# // [PACK34-lookup]
def get_last_cash_session_for_store(
    db: Session, *, store_id: int
) -> models.CashRegisterSession:
    statement = (
        select(models.CashRegisterSession)
        .where(models.CashRegisterSession.store_id == store_id)
        .order_by(models.CashRegisterSession.opened_at.desc())
    )
    session = db.scalars(statement).first()
    if session is None:
        raise LookupError("cash_session_not_found")
    return session


def paginate_cash_sessions(
    db: Session,
    *,
    store_id: int,
    page: int,
    size: int,
) -> tuple[int, list[models.CashRegisterSession]]:
    total = count_cash_sessions(db, store_id=store_id)
    offset = max(page - 1, 0) * size
    sessions = list_cash_sessions(db, store_id=store_id, limit=size, offset=offset)
    return total, sessions


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
    with transactional_session(db):
        db.add(session)
        flush_session(db)
        db.refresh(session)

        _log_action(
            db,
            action="cash_session_opened",
            entity_type="cash_session",
            entity_id=str(session.id),
            performed_by_id=opened_by_id,
            details=json.dumps(
                {"store_id": session.store_id, "reason": reason}),
        )
        flush_session(db)
        db.refresh(session)
    return session


def _cash_entries_totals(
    db: Session,
    *,
    session_id: int,
) -> tuple[Decimal, Decimal]:
    """Resume los ingresos y egresos registrados en la sesión."""

    entries_stmt = (
        select(
            models.CashRegisterEntry.entry_type,
            func.coalesce(func.sum(models.CashRegisterEntry.amount), 0),
        )
        .where(models.CashRegisterEntry.session_id == session_id)
        .group_by(models.CashRegisterEntry.entry_type)
    )
    incomes = Decimal("0")
    expenses = Decimal("0")
    for entry_type, total in db.execute(entries_stmt):
        normalized_total = _to_decimal(total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if entry_type == models.CashEntryType.INGRESO:
            incomes = normalized_total
        elif entry_type == models.CashEntryType.EGRESO:
            expenses = normalized_total
    return incomes, expenses


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
        totals_value = _to_decimal(total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        sales_totals[method.value] = totals_value

    session.closing_amount = _to_decimal(payload.closing_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    session.closed_by_id = closed_by_id
    session.closed_at = datetime.utcnow()
    session.status = models.CashSessionStatus.CERRADO
    breakdown_snapshot = dict(session.payment_breakdown or {})
    for key, value in sales_totals.items():
        breakdown_snapshot[key] = float(value)

    for method_key, reported_amount in payload.payment_breakdown.items():
        breakdown_snapshot[f"reportado_{method_key.upper()}"] = float(
            Decimal(str(reported_amount))
        )

    incomes_total, expenses_total = _cash_entries_totals(
        db, session_id=session.id
    )
    expected_cash = (
        session.opening_amount
        + sales_totals.get(models.PaymentMethod.EFECTIVO.value, Decimal("0"))
        + incomes_total
        - expenses_total
    )
    session.payment_breakdown = breakdown_snapshot

    expected_cash = session.opening_amount + \
        sales_totals.get(models.PaymentMethod.EFECTIVO.value, Decimal("0"))
    session.expected_amount = expected_cash.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    session.difference_amount = (
        session.closing_amount - session.expected_amount
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    session.reconciliation_notes = payload.reconciliation_notes

    if session.difference_amount != Decimal("0") and not payload.difference_reason:
        raise ValueError("difference_reason_required")
    session.difference_reason = payload.difference_reason

    denomination_breakdown: dict[str, int] = {}
    for denomination in payload.denominations:
        value = _to_decimal(denomination.value).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        quantity = max(0, int(denomination.quantity))
        if quantity <= 0:
            continue
        key = f"{value:.2f}"
        denomination_breakdown[key] = quantity
    session.denomination_breakdown = denomination_breakdown

    if payload.notes:
        session.notes = (session.notes or "") + \
            f"\n{payload.notes}" if session.notes else payload.notes

    with transactional_session(db):
        db.add(session)
        flush_session(db)
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
                    "difference_reason": session.difference_reason,
                    "denominations": denomination_breakdown,
                    "reason": reason,
                }
            ),
        )
        flush_session(db)
        db.refresh(session)
    return session


def record_cash_entry(
    db: Session,
    payload: schemas.CashRegisterEntryCreate,
    *,
    created_by_id: int | None,
    reason: str | None = None,
) -> models.CashRegisterEntry:
    session = get_cash_session(db, payload.session_id)
    if session.status != models.CashSessionStatus.ABIERTO:
        raise ValueError("cash_session_not_open")

    amount = _to_decimal(payload.amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    entry = models.CashRegisterEntry(
        session_id=session.id,
        entry_type=payload.entry_type,
        amount=amount,
        reason=payload.reason,
        notes=payload.notes,
        created_by_id=created_by_id,
    )

    with transactional_session(db):
        db.add(entry)

        expected_delta = amount if payload.entry_type == models.CashEntryType.INGRESO else -amount
        session.expected_amount = (
            session.expected_amount + expected_delta
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        db.add(session)
        flush_session(db)
        db.refresh(entry)
        db.refresh(session)

        _log_action(
            db,
            action="cash_entry_recorded",
            entity_type="cash_session",
            entity_id=str(session.id),
            performed_by_id=created_by_id,
            details=json.dumps(
                {
                    "entry_type": payload.entry_type,
                    "amount": float(amount),
                    "reason": payload.reason,
                    "notes": payload.notes,
                    "reason_header": reason,
                }
            ),
        )
        flush_session(db)
        db.refresh(entry)
    return entry


def list_cash_entries(
    db: Session,
    *,
    session_id: int,
) -> list[models.CashRegisterEntry]:
    statement = (
        select(models.CashRegisterEntry)
        .where(models.CashRegisterEntry.session_id == session_id)
        .order_by(models.CashRegisterEntry.created_at.desc())
    )
    return list(db.scalars(statement))


def get_pos_config(db: Session, store_id: int) -> models.POSConfig:
    store = get_store(db, store_id)
    statement = select(models.POSConfig).where(
        models.POSConfig.store_id == store_id)
    config = db.scalars(statement).first()
    if config is None:
        prefix = store.name[:3].upper() if store.name else "POS"
        generated_prefix = f"{prefix}-{store_id:03d}"[:12]
        config = models.POSConfig(
            store_id=store_id, invoice_prefix=generated_prefix)
        with transactional_session(db):
            db.add(config)
            flush_session(db)
            db.refresh(config)
    else:
        db.refresh(config)
    normalized_hardware = _normalize_hardware_settings(
        config.hardware_settings if isinstance(config.hardware_settings, dict) else None
    )
    if config.hardware_settings != normalized_hardware:
        with transactional_session(db):
            config.hardware_settings = normalized_hardware
            db.add(config)
            flush_session(db)
            db.refresh(config)
    else:
        config.hardware_settings = normalized_hardware
    return config


def update_pos_config(
    db: Session,
    payload: schemas.POSConfigUpdate,
    *,
    updated_by_id: int | None,
    reason: str | None = None,
) -> models.POSConfig:
    config = get_pos_config(db, payload.store_id)
    with transactional_session(db):
        config.tax_rate = _to_decimal(payload.tax_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        config.invoice_prefix = payload.invoice_prefix.strip().upper()
        config.printer_name = payload.printer_name.strip() if payload.printer_name else None
        config.printer_profile = (
            payload.printer_profile.strip() if payload.printer_profile else None
        )
        config.quick_product_ids = payload.quick_product_ids
        if payload.hardware_settings is not None:
            config.hardware_settings = payload.hardware_settings.model_dump()
        else:
            config.hardware_settings = _normalize_hardware_settings(
                config.hardware_settings
            )
        db.add(config)
        flush_session(db)
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
        flush_session(db)
        db.refresh(config)
        enqueue_sync_outbox(
            db,
            entity_type="pos_config",
            entity_id=str(payload.store_id),
            operation="UPSERT",
            payload=_pos_config_payload(config),
        )
    return config


# // [POS-promotions]
def get_pos_promotions(db: Session, store_id: int) -> schemas.POSPromotionsResponse:
    config = get_pos_config(db, store_id)
    return _build_pos_promotions_response(config)


def update_pos_promotions(
    db: Session,
    payload: schemas.POSPromotionsUpdate,
    *,
    updated_by_id: int | None,
    reason: str | None = None,
) -> schemas.POSPromotionsResponse:
    config = get_pos_config(db, payload.store_id)
    normalized = schemas.POSPromotionsConfig.model_validate(
        payload.model_dump(exclude={"store_id"})
    )
    serialized = normalized.model_dump(mode="json")

    with transactional_session(db):
        config.promotions_config = serialized
        db.add(config)
        flush_session(db)
        db.refresh(config)

        _log_action(
            db,
            action="pos_promotions_update",
            entity_type="store",
            entity_id=str(payload.store_id),
            performed_by_id=updated_by_id,
            details=json.dumps({
                "reason": reason,
                "volume": normalized.feature_flags.volume,
                "combos": normalized.feature_flags.combos,
                "coupons": normalized.feature_flags.coupons,
            }),
        )
        enqueue_sync_outbox(
            db,
            entity_type="pos_config",
            entity_id=str(payload.store_id),
            operation="UPSERT",
            payload=_pos_config_payload(config),
        )
    db.refresh(config)
    return _build_pos_promotions_response(config)


# // [PACK34-taxes]
def list_pos_taxes(db: Session) -> list[schemas.POSTaxInfo]:
    statement = (
        select(models.POSConfig.tax_rate,
               models.POSConfig.store_id, models.Store.name)
        .join(models.Store, models.Store.id == models.POSConfig.store_id)
        .order_by(models.POSConfig.tax_rate.desc())
    )
    taxes: list[schemas.POSTaxInfo] = []
    seen_rates: set[str] = set()
    for tax_rate, store_id, store_name in db.execute(statement):
        normalized_rate = _to_decimal(tax_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        rate_key = f"{normalized_rate:.2f}"
        if rate_key in seen_rates:
            continue
        seen_rates.add(rate_key)
        label = store_name or f"Sucursal #{store_id}"
        taxes.append(
            schemas.POSTaxInfo(
                code=f"POS-{rate_key.replace('.', '')}",
                name=f"IVA {rate_key}% ({label})",
                rate=normalized_rate,
            )
        )
    if not taxes:
        taxes.append(
            schemas.POSTaxInfo(
                code="POS-DEFAULT",
                name="Impuesto estándar",
                rate=Decimal("0"),
            )
        )
    return taxes


def register_pos_config_access(
    db: Session,
    *,
    store_id: int,
    performed_by_id: int | None,
    reason: str,
) -> None:
    details = json.dumps({"store_id": store_id, "reason": reason.strip()})
    _log_action(
        db,
        action="pos_config_viewed",
        entity_type="store",
        entity_id=str(store_id),
        performed_by_id=performed_by_id,
        details=details,
    )


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
        statement = select(models.POSDraftSale).where(
            models.POSDraftSale.id == payload.draft_id)
        draft = db.scalars(statement).first()
        if draft is None:
            raise LookupError("pos_draft_not_found")
        draft.store_id = payload.store_id
    else:
        draft = models.POSDraftSale(store_id=payload.store_id)
        db.add(draft)

    with transactional_session(db):
        serialized = payload.model_dump(
            mode="json",
            exclude_none=True,
            exclude={"confirm", "save_as_draft"},
        )
        draft.payload = serialized
        db.add(draft)
        flush_session(db)
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
        flush_session(db)
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
    statement = select(models.POSDraftSale).where(
        models.POSDraftSale.id == draft_id)
    draft = db.scalars(statement).first()
    if draft is None:
        raise LookupError("pos_draft_not_found")
    store_id = draft.store_id
    with transactional_session(db):
        db.delete(draft)
        flush_session(db)
        _log_action(
            db,
            action="pos_draft_removed",
            entity_type="pos_draft",
            entity_id=str(draft_id),
            performed_by_id=removed_by_id,
            details=json.dumps({"store_id": store_id}),
        )
        flush_session(db)
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
) -> tuple[models.Sale, list[str], dict[str, object] | None, schemas.POSLoyaltySaleSummary | None]:
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
                unit_price_override=getattr(
                    item, "unit_price_override", None),  # // [PACK34-pricing]
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
    loyalty_amount = Decimal("0")
    if payload.payments:
        for payment in payload.payments:
            if payment.method == models.PaymentMethod.PUNTOS:
                loyalty_amount += _to_decimal(payment.amount)
    elif payload.payment_breakdown:
        puntos_key = models.PaymentMethod.PUNTOS.value
        if puntos_key in payload.payment_breakdown:
            loyalty_amount = _to_decimal(payload.payment_breakdown[puntos_key])
    loyalty_amount = _quantize_currency(loyalty_amount)
    loyalty_summary: schemas.POSLoyaltySaleSummary | None = None
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
            delete_pos_draft(db, payload.draft_id,
                             removed_by_id=performed_by_id)
        except LookupError:
            logger.debug(
                f"Borrador POS {payload.draft_id} no encontrado al confirmar la venta."
            )

    store_credit_redemptions: list[models.StoreCreditRedemption] = []

    with transactional_session(db):
        if payload.cash_session_id:
            session = get_cash_session(db, payload.cash_session_id)
            if session.status != models.CashSessionStatus.ABIERTO:
                raise ValueError("cash_session_not_open")
            sale.cash_session_id = session.id
            db.add(sale)
            flush_session(db)
            if payload.payments:
                breakdown = dict(session.payment_breakdown or {})
                for payment in payload.payments:
                    try:
                        total_amount = Decimal(str(payment.amount))
                    except (TypeError, ValueError):
                        continue
                    tip_value = Decimal("0")
                    if getattr(payment, "tip_amount", None) is not None:
                        tip_value = Decimal(str(payment.tip_amount))
                        tip_key = f"propina_{payment.method.value}"
                        breakdown[tip_key] = float(
                            Decimal(str(breakdown.get(tip_key, 0))) + tip_value
                        )
                    collected_key = f"cobrado_{payment.method.value}"
                    breakdown[collected_key] = float(
                        Decimal(str(breakdown.get(collected_key, 0)))
                        + total_amount
                        + tip_value
                    )
                session.payment_breakdown = breakdown
                db.add(session)
                flush_session(db)
            elif payload.payment_breakdown:
                breakdown = dict(session.payment_breakdown or {})
                for method_key, reported_amount in payload.payment_breakdown.items():
                    try:
                        method_enum = models.PaymentMethod(method_key)
                    except ValueError:
                        continue
                    total_amount = _to_decimal(reported_amount).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    if total_amount <= Decimal("0"):
                        continue
                    collected_key = f"cobrado_{method_enum.value}"
                    breakdown[collected_key] = float(
                        Decimal(str(breakdown.get(collected_key, 0)))
                        + total_amount
                    )
                session.payment_breakdown = breakdown
                db.add(session)
                flush_session(db)
        db.refresh(sale)

    if payload.payment_breakdown:
        store_credit_key = models.PaymentMethod.NOTA_CREDITO.value
        breakdown_value = payload.payment_breakdown.get(store_credit_key)
        if breakdown_value is not None:
            store_credit_amount = _to_decimal(breakdown_value).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if store_credit_amount > Decimal("0"):
                if not sale.customer_id:
                    raise ValueError("store_credit_requires_customer")
                redemptions = redeem_store_credit_for_customer(
                    db,
                    customer_id=sale.customer_id,
                    amount=store_credit_amount,
                    sale_id=sale.id,
                    notes=payload.notes,
                    performed_by_id=performed_by_id,
                    reason=reason,
                )
                store_credit_redemptions.extend(redemptions)
                warnings.append(
                    f"Se aplicaron notas de crédito por ${_format_currency(store_credit_amount)}"
                )

    loyalty_summary = apply_loyalty_for_sale(
        db,
        sale,
        points_payment_amount=loyalty_amount,
        performed_by_id=performed_by_id,
        reason=reason,
    )

    payments_applied_total = Decimal("0")
    payment_outcomes: list[CustomerPaymentOutcome] = []
    if (
        payload.payments
        and sale.customer_id
        and sale.payment_method == models.PaymentMethod.CREDITO
    ):
        for payment in payload.payments:
            payment_amount = _to_decimal(payment.amount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if payment_amount <= Decimal("0"):
                continue
            method_value = (
                payment.method.value
                if isinstance(payment.method, models.PaymentMethod)
                else str(payment.method).strip()
            )
            if method_value == models.PaymentMethod.PUNTOS.value:
                # La redención de puntos se maneja por el módulo de lealtad y
                # no debe registrar abonos sobre la deuda del cliente.
                continue
            if not method_value:
                method_value = "manual"
            note_source = payload.notes or "Abono registrado desde POS"
            payment_payload = schemas.CustomerPaymentCreate(
                amount=payment_amount,
                method=method_value,
                sale_id=sale.id,
                note=note_source,
            )
            outcome = register_customer_payment(
                db,
                sale.customer_id,
                payment_payload,
                performed_by_id=performed_by_id,
            )
            payment_outcomes.append(outcome)
            payments_applied_total += outcome.applied_amount

    customer_after_operations: models.Customer | None = None
    if sale.customer_id:
        try:
            customer_after_operations = get_customer(db, sale.customer_id)
        except LookupError:
            customer_after_operations = None

    debt_context: dict[str, object] | None = None
    if customer_after_operations is not None:
        remaining_balance = _to_decimal(
            customer_after_operations.outstanding_debt
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        new_charge = (
            _to_decimal(sale.total_amount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if sale.payment_method == models.PaymentMethod.CREDITO
            else Decimal("0.00")
        )
        previous_balance = (
            remaining_balance + payments_applied_total - new_charge
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        snapshot = credit.build_debt_snapshot(
            previous_balance=previous_balance,
            new_charges=new_charge,
            payments_applied=payments_applied_total,
        )
        schedule = credit.build_credit_schedule(
            base_date=sale.created_at,
            remaining_balance=snapshot.remaining_balance,
        )
        debt_context = {
            "snapshot": snapshot,
            "schedule": schedule,
            "payments": payment_outcomes,
            "customer": customer_after_operations,
        }

    _attach_last_audit_trails(
        db,
        entity_type="sale",
        records=[sale],
    )
    return sale, warnings, debt_context, loyalty_summary


def list_backup_jobs(
    db: Session, *, limit: int = 50, offset: int = 0
) -> list[models.BackupJob]:
    statement = (
        select(models.BackupJob)
        .order_by(models.BackupJob.executed_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


def register_pos_receipt_download(
    db: Session,
    *,
    sale_id: int,
    performed_by_id: int | None,
    reason: str,
) -> None:
    detalles = f"motivo={reason.strip()}"
    _log_action(
        db,
        action="pos_receipt_downloaded",
        entity_type="sale",
        entity_id=str(sale_id),
        performed_by_id=performed_by_id,
        details=detalles,
    )


def register_pos_receipt_delivery(
    db: Session,
    *,
    sale_id: int,
    performed_by_id: int | None,
    reason: str,
    channel: str,
    recipient: str,
) -> None:
    detalles = {
        "motivo": reason.strip(),
        "canal": channel,
        "destinatario": recipient,
    }
    _log_action(
        db,
        action="pos_receipt_sent",
        entity_type="sale",
        entity_id=str(sale_id),
        performed_by_id=performed_by_id,
        details=detalles,
    )


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

    movements_stmt = select(models.InventoryMovement).order_by(
        models.InventoryMovement.created_at.desc()
    )
    movements = list(db.scalars(movements_stmt))
    _hydrate_movement_references(db, movements)

    sync_stmt = select(models.SyncSession).order_by(
        models.SyncSession.started_at.desc())
    sync_sessions = list(db.scalars(sync_stmt))

    audit_stmt = select(models.AuditLog).order_by(
        models.AuditLog.created_at.desc())
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

    integrity_report = inventory_audit.build_inventory_integrity_report(db)

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
                "costo_unitario": (
                    float(_to_decimal(movement.unit_cost))
                    if movement.unit_cost is not None
                    else None
                ),
                "referencia_tipo": getattr(movement, "reference_type", None),
                "referencia_id": getattr(movement, "reference_id", None),
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
                total_inventory_value.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
        },
        "integrity_report": integrity_report.model_dump(mode="json"),
    }
    return snapshot


def create_inventory_import_record(
    db: Session,
    *,
    filename: str,
    columnas_detectadas: dict[str, str | None],
    registros_incompletos: int,
    total_registros: int,
    nuevos: int,
    actualizados: int,
    advertencias: list[str],
    patrones_columnas: dict[str, str],
    duration_seconds: float | None = None,
) -> models.InventoryImportTemp:
    duration_value = None
    if duration_seconds is not None:
        duration_value = Decimal(str(round(duration_seconds, 2)))
    record = models.InventoryImportTemp(
        nombre_archivo=filename,
        columnas_detectadas=columnas_detectadas,
        registros_incompletos=registros_incompletos,
        total_registros=total_registros,
        nuevos=nuevos,
        actualizados=actualizados,
        advertencias=advertencias,
        patrones_columnas=patrones_columnas,
        duracion_segundos=duration_value,
    )
    with transactional_session(db):
        db.add(record)
        flush_session(db)
        db.refresh(record)
    return record


def list_inventory_import_history(
    db: Session, *, limit: int | None = 10, offset: int = 0
) -> list[models.InventoryImportTemp]:
    statement = select(models.InventoryImportTemp).order_by(
        models.InventoryImportTemp.fecha.desc()
    )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement))


def count_inventory_import_history(db: Session) -> int:
    statement = select(func.count()).select_from(models.InventoryImportTemp)
    return int(db.scalar(statement) or 0)


def get_known_import_column_patterns(db: Session) -> dict[str, str]:
    patterns: dict[str, str] = {}
    statement = select(models.InventoryImportTemp.patrones_columnas)
    for mapping in db.scalars(statement):
        if not mapping:
            continue
        for key, value in mapping.items():
            if key not in patterns:
                patterns[key] = value
    return patterns


def list_import_validations(
    db: Session,
    *,
    corregido: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.ImportValidation]:
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    statement = (
        select(models.ImportValidation)
        .order_by(models.ImportValidation.fecha.desc())
        .offset(safe_offset)
        .limit(safe_limit)
    )
    if corregido is not None:
        statement = statement.where(
            models.ImportValidation.corregido.is_(corregido))
    return list(db.scalars(statement))


def list_import_validation_details(
    db: Session,
    *,
    corregido: bool | None = None,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.ImportValidation]:
    statement = (
        select(models.ImportValidation)
        .options(joinedload(models.ImportValidation.device).joinedload(models.Device.store))
        .order_by(models.ImportValidation.fecha.desc())
    )
    if corregido is not None:
        statement = statement.where(
            models.ImportValidation.corregido.is_(corregido))
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement))


def mark_import_validation_corrected(
    db: Session, validation_id: int, *, corrected: bool = True
) -> models.ImportValidation:
    validation = db.get(models.ImportValidation, validation_id)
    if validation is None:
        raise LookupError("validation_not_found")
    with transactional_session(db):
        validation.corregido = corrected
        validation.fecha = datetime.utcnow()
        db.add(validation)
        flush_session(db)
        db.refresh(validation)
    return validation


def get_import_validation_report(db: Session) -> schemas.ImportValidationSummary:
    total_errors = db.scalar(
        select(func.count()).where(
            models.ImportValidation.severidad == "error",
            models.ImportValidation.corregido.is_(False),
        )
    )
    total_warnings = db.scalar(
        select(func.count()).where(
            models.ImportValidation.severidad == "advertencia",
            models.ImportValidation.corregido.is_(False),
        )
    )
    last_import = db.scalar(
        select(models.InventoryImportTemp)
        .order_by(models.InventoryImportTemp.fecha.desc())
        .limit(1)
    )
    registros_revisados = last_import.total_registros if last_import else 0
    duration = float(
        last_import.duracion_segundos) if last_import and last_import.duracion_segundos is not None else None
    campos_faltantes: set[str] = set()
    if last_import and last_import.columnas_detectadas:
        for canonical, header in last_import.columnas_detectadas.items():
            if header is None:
                campos_faltantes.add(canonical)
    structure_statements = db.scalars(
        select(models.ImportValidation.descripcion).where(
            models.ImportValidation.tipo == "estructura",
            models.ImportValidation.descripcion.ilike("Columna faltante:%"),
        )
    )
    for description in structure_statements:
        try:
            _, column_name = description.split(":", 1)
            column = column_name.strip()
            if column:
                campos_faltantes.add(column)
        except ValueError:
            continue
    return schemas.ImportValidationSummary(
        registros_revisados=registros_revisados,
        advertencias=int(total_warnings or 0),
        errores=int(total_errors or 0),
        campos_faltantes=sorted(campos_faltantes),
        tiempo_total=duration,
    )


def create_dte_authorization(
    db: Session,
    payload: schemas.DTEAuthorizationCreate,
) -> models.DTEAuthorization:
    document_type = payload.document_type.strip().upper()
    serie = payload.serie.strip().upper()
    store_id = payload.store_id

    statement = select(models.DTEAuthorization).where(
        func.upper(models.DTEAuthorization.document_type) == document_type,
        func.upper(models.DTEAuthorization.serie) == serie,
        models.DTEAuthorization.range_start <= payload.range_end,
        models.DTEAuthorization.range_end >= payload.range_start,
    )
    if store_id is None:
        statement = statement.where(models.DTEAuthorization.store_id.is_(None))
    else:
        statement = statement.where(models.DTEAuthorization.store_id == store_id)

    conflict = db.scalars(statement).first()
    if conflict:
        raise ValueError("dte_authorization_conflict")

    authorization = models.DTEAuthorization(
        store_id=store_id,
        document_type=document_type,
        serie=serie,
        range_start=payload.range_start,
        range_end=payload.range_end,
        current_number=payload.range_start,
        cai=payload.cai,
        expiration_date=payload.expiration_date,
        active=payload.active,
        notes=payload.notes,
    )
    db.add(authorization)
    db.flush()
    db.refresh(authorization)
    return authorization


def list_dte_authorizations(
    db: Session,
    *,
    store_id: int | None = None,
    document_type: str | None = None,
    active: bool | None = None,
) -> list[models.DTEAuthorization]:
    statement = (
        select(models.DTEAuthorization)
        .order_by(models.DTEAuthorization.created_at.desc())
    )
    if store_id is not None:
        statement = statement.where(
            or_(
                models.DTEAuthorization.store_id == store_id,
                models.DTEAuthorization.store_id.is_(None),
            )
        )
    if document_type:
        statement = statement.where(
            func.upper(models.DTEAuthorization.document_type)
            == document_type.strip().upper()
        )
    if active is not None:
        statement = statement.where(models.DTEAuthorization.active.is_(active))
    return list(db.scalars(statement))


def get_dte_authorization(db: Session, authorization_id: int) -> models.DTEAuthorization:
    authorization = db.get(models.DTEAuthorization, authorization_id)
    if authorization is None:
        raise LookupError("dte_authorization_not_found")
    return authorization


def update_dte_authorization(
    db: Session,
    authorization_id: int,
    payload: schemas.DTEAuthorizationUpdate,
) -> models.DTEAuthorization:
    authorization = get_dte_authorization(db, authorization_id)

    if payload.expiration_date is not None:
        authorization.expiration_date = payload.expiration_date
    if payload.notes is not None:
        authorization.notes = payload.notes
    if payload.active is not None:
        authorization.active = payload.active

    db.add(authorization)
    db.flush()
    db.refresh(authorization)
    return authorization


def reserve_dte_folio(
    db: Session,
    authorization: models.DTEAuthorization,
) -> int:
    next_number = authorization.current_number
    if next_number < authorization.range_start:
        next_number = authorization.range_start
    if next_number > authorization.range_end:
        raise ValueError("dte_authorization_exhausted")

    authorization.current_number = next_number + 1
    db.add(authorization)
    db.flush()
    db.refresh(authorization)
    return next_number


def register_dte_document(
    db: Session,
    *,
    sale: models.Sale,
    authorization: models.DTEAuthorization,
    xml_content: str,
    signature: str,
    control_number: str,
    correlative: int,
    reference_code: str | None,
) -> models.DTEDocument:
    document = models.DTEDocument(
        sale_id=sale.id,
        authorization_id=authorization.id if authorization else None,
        document_type=authorization.document_type,
        serie=authorization.serie,
        correlative=correlative,
        control_number=control_number,
        cai=authorization.cai,
        xml_content=xml_content,
        signature=signature,
        reference_code=reference_code,
    )
    sale.dte_status = models.DTEStatus.PENDIENTE
    sale.dte_reference = control_number
    db.add(document)
    db.add(sale)
    db.flush()
    db.refresh(document)
    return document


def log_dte_event(
    db: Session,
    *,
    document: models.DTEDocument,
    event_type: str,
    status: models.DTEStatus,
    detail: str | None,
    performed_by_id: int | None,
) -> models.DTEEvent:
    event = models.DTEEvent(
        document=document,
        event_type=event_type,
        status=status,
        detail=detail,
        performed_by_id=performed_by_id,
    )
    db.add(event)
    db.flush()
    db.refresh(event)
    return event


def list_dte_documents(
    db: Session,
    *,
    store_id: int | None = None,
    sale_id: int | None = None,
    status: models.DTEStatus | str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.DTEDocument]:
    safe_limit = None if limit is None else max(1, min(limit, 200))
    statement = (
        select(models.DTEDocument)
        .options(
            joinedload(models.DTEDocument.sale).joinedload(models.Sale.store),
            joinedload(models.DTEDocument.authorization),
            selectinload(models.DTEDocument.events),
            selectinload(models.DTEDocument.dispatch_entries),
        )
        .order_by(models.DTEDocument.created_at.desc())
    )
    if store_id is not None:
        statement = statement.join(models.DTEDocument.sale).where(
            models.Sale.store_id == store_id
        )
    if sale_id is not None:
        statement = statement.where(models.DTEDocument.sale_id == sale_id)
    if status is not None:
        enum_status = (
            status
            if isinstance(status, models.DTEStatus)
            else models.DTEStatus(status)
        )
        statement = statement.where(models.DTEDocument.status == enum_status)
    if offset:
        statement = statement.offset(offset)
    if safe_limit is not None:
        statement = statement.limit(safe_limit)
    return list(db.scalars(statement))


def get_dte_document(db: Session, document_id: int) -> models.DTEDocument:
    document = db.get(models.DTEDocument, document_id)
    if document is None:
        raise LookupError("dte_document_not_found")
    return document


def register_dte_ack(
    db: Session,
    *,
    document: models.DTEDocument,
    status: models.DTEStatus,
    code: str | None,
    detail: str | None,
    received_at: datetime,
) -> models.DTEDocument:
    ack_time = received_at
    if ack_time.tzinfo is not None:
        ack_time = ack_time.astimezone(timezone.utc).replace(tzinfo=None)
    document.status = status
    document.ack_code = code
    document.ack_message = detail
    document.acknowledged_at = ack_time
    if document.sale:
        document.sale.dte_status = status
        if code:
            document.sale.dte_reference = code
    db.add(document)
    if document.sale:
        db.add(document.sale)
    db.flush()
    db.refresh(document)
    return document


def enqueue_dte_dispatch(
    db: Session,
    *,
    document: models.DTEDocument,
    error_message: str | None,
) -> models.DTEDispatchQueue:
    existing = db.scalar(
        select(models.DTEDispatchQueue).where(
            models.DTEDispatchQueue.document_id == document.id
        )
    )
    now = datetime.utcnow()
    if existing:
        existing.status = models.DTEDispatchStatus.PENDING
        existing.last_error = error_message
        existing.scheduled_at = now
        existing.updated_at = now
        if existing.attempts <= 0:
            existing.attempts = 0
        existing.document = document
        db.add(existing)
        entry = existing
    else:
        entry = models.DTEDispatchQueue(
            document=document,
            document_id=document.id,
            status=models.DTEDispatchStatus.PENDING,
            attempts=0,
            last_error=error_message,
            scheduled_at=now,
        )
        db.add(entry)
    db.flush()
    db.refresh(entry)
    return entry


def mark_dte_dispatch_sent(
    db: Session,
    *,
    document: models.DTEDocument,
    error_message: str | None,
) -> models.DTEDispatchQueue:
    entry = db.scalar(
        select(models.DTEDispatchQueue).where(
            models.DTEDispatchQueue.document_id == document.id
        )
    )
    now = datetime.utcnow()
    if entry is None:
        entry = models.DTEDispatchQueue(
            document=document,
            document_id=document.id,
            status=models.DTEDispatchStatus.SENT,
            attempts=1,
            last_error=error_message,
            scheduled_at=now,
        )
    else:
        entry.status = models.DTEDispatchStatus.SENT
        entry.attempts = entry.attempts + 1
        entry.last_error = error_message
        entry.updated_at = now
    entry.document = document
    document.sent_at = now
    db.add(entry)
    db.add(document)
    db.flush()
    db.refresh(entry)
    db.refresh(document)
    return entry


def list_dte_dispatch_queue(
    db: Session,
    *,
    statuses: Iterable[models.DTEDispatchStatus] | None = None,
) -> list[models.DTEDispatchQueue]:
    statement = (
        select(models.DTEDispatchQueue)
        .options(joinedload(models.DTEDispatchQueue.document))
        .order_by(models.DTEDispatchQueue.created_at.desc())
    )
    if statuses:
        statement = statement.where(models.DTEDispatchQueue.status.in_(tuple(statuses)))
    return list(db.scalars(statement))


def create_support_feedback(
    db: Session, *, payload: schemas.FeedbackCreate, user_id: int | None = None
) -> models.SupportFeedback:
    entry = models.SupportFeedback(
        user_id=user_id,
        contact=payload.contact,
        module=payload.module,
        category=payload.category,
        priority=payload.priority,
        status=models.FeedbackStatus.ABIERTO,
        title=payload.title,
        description=payload.description,
        metadata_json=payload.metadata,
        usage_context=payload.usage_context,
    )
    flush_session(db, entry)
    return entry


def update_support_feedback_status(
    db: Session,
    *,
    tracking_id: str,
    status: models.FeedbackStatus,
    resolution_notes: str | None = None,
) -> models.SupportFeedback | None:
    entry = db.scalar(
        select(models.SupportFeedback).where(
            models.SupportFeedback.tracking_id == tracking_id
        )
    )
    if entry is None:
        return None

    entry.status = status
    entry.resolution_notes = resolution_notes
    entry.updated_at = datetime.utcnow()
    db.add(entry)
    db.flush()
    db.refresh(entry)
    return entry


def support_feedback_metrics(
    db: Session, *, days: int = 30
) -> schemas.FeedbackMetrics:
    def _group_count(column) -> dict[str, int]:
        results: dict[str, int] = {}
        rows = db.execute(
            select(column, func.count(models.SupportFeedback.id)).group_by(column)
        ).all()
        for value, count in rows:
            key = value.value if hasattr(value, "value") else str(value)
            results[key] = int(count)
        return results

    total_feedback = int(
        db.scalar(select(func.count(models.SupportFeedback.id))) or 0
    )
    by_category = _group_count(models.SupportFeedback.category)
    by_priority = _group_count(models.SupportFeedback.priority)
    by_status = _group_count(models.SupportFeedback.status)

    recent_feedback = [
        schemas.FeedbackSummary.model_validate(row)
        for row in db.scalars(
            select(models.SupportFeedback)
            .order_by(models.SupportFeedback.created_at.desc())
            .limit(10)
        )
    ]

    since = datetime.utcnow() - timedelta(days=days)
    usage_rows = db.execute(
        select(models.AuditUI.module, func.count(models.AuditUI.id))
        .where(models.AuditUI.ts >= since)
        .group_by(models.AuditUI.module)
    ).all()
    usage_map = {module: int(count) for module, count in usage_rows}

    open_rows = db.execute(
        select(models.SupportFeedback.module, func.count(models.SupportFeedback.id))
        .where(
            models.SupportFeedback.status.in_(
                (models.FeedbackStatus.ABIERTO, models.FeedbackStatus.EN_PROGRESO)
            )
        )
        .group_by(models.SupportFeedback.module)
    ).all()
    open_map = {module: int(count) for module, count in open_rows}

    priority_weights: dict[models.FeedbackPriority, float] = {
        models.FeedbackPriority.BAJA: 1.0,
        models.FeedbackPriority.MEDIA: 1.4,
        models.FeedbackPriority.ALTA: 2.0,
        models.FeedbackPriority.CRITICA: 3.2,
    }
    status_weights: dict[models.FeedbackStatus, float] = {
        models.FeedbackStatus.ABIERTO: 1.0,
        models.FeedbackStatus.EN_PROGRESO: 0.85,
        models.FeedbackStatus.RESUELTO: 0.3,
        models.FeedbackStatus.DESCARTADO: 0.05,
    }

    module_scores: dict[str, float] = {}
    for record in db.scalars(select(models.SupportFeedback)).all():
        base_score = priority_weights.get(record.priority, 1.0)
        status_multiplier = status_weights.get(record.status, 1.0)
        module_scores[record.module] = module_scores.get(record.module, 0.0) + (
            base_score * status_multiplier
        )

    hotspots = [
        schemas.FeedbackUsageHotspot(
            module=module,
            interactions_last_30d=usage_map.get(module, 0),
            open_feedback=open_map.get(module, 0),
            priority_score=round(
                score * (1 + math.log1p(usage_map.get(module, 0))), 2
            ),
        )
        for module, score in module_scores.items()
    ]
    hotspots.sort(key=lambda item: item.priority_score, reverse=True)

    return schemas.FeedbackMetrics(
        totals={"feedback": total_feedback},
        by_category={schemas.FeedbackCategory(key): value for key, value in by_category.items()},
        by_priority={
            schemas.FeedbackPriority(key): value for key, value in by_priority.items()
        },
        by_status={schemas.FeedbackStatus(key): value for key, value in by_status.items()},
        hotspots=hotspots,
        recent_feedback=recent_feedback,
    )
