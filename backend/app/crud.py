"""Operaciones de base de datos para las entidades principales."""
from __future__ import annotations

import copy
import csv
import json
import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from io import StringIO

from sqlalchemy import case, func, or_, select, tuple_
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import ColumnElement

from . import models, schemas, telemetry
from .utils import audit as audit_utils
from .utils.cache import TTLCache


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
    if serial:
        statement = select(models.Device).where(models.Device.serial == serial)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
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
    elif isinstance(date_from, date):
        start_dt = datetime.combine(date_from, datetime.min.time())
    else:
        start_dt = now - timedelta(days=30)

    if isinstance(date_to, datetime):
        end_dt = date_to
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


def _resolve_outbox_priority(entity_type: str, priority: models.SyncOutboxPriority | None) -> models.SyncOutboxPriority:
    if priority is not None:
        return priority
    return _OUTBOX_PRIORITY_MAP.get(entity_type, models.SyncOutboxPriority.NORMAL)


def _priority_weight(priority: models.SyncOutboxPriority | None) -> int:
    if priority is None:
        return _OUTBOX_PRIORITY_ORDER[models.SyncOutboxPriority.NORMAL]
    return _OUTBOX_PRIORITY_ORDER.get(priority, 1)


def _recalculate_sale_price(device: models.Device) -> None:
    base_cost = _to_decimal(device.costo_unitario)
    margin = _to_decimal(device.margen_porcentaje)
    sale_factor = Decimal("1") + (margin / Decimal("100"))
    device.unit_price = (base_cost * sale_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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
    invalidate_persistent_audit_alerts_cache()
    return log


def _device_value(device: models.Device) -> Decimal:
    return Decimal(device.quantity) * (device.unit_price or Decimal("0"))


def _recalculate_store_inventory_value(
    db: Session, store: models.Store | int
) -> Decimal:
    if isinstance(store, models.Store):
        store_obj = store
    else:
        store_obj = get_store(db, int(store))
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
        "outstanding_debt": float(customer.outstanding_debt or Decimal("0")),
        "last_interaction_at": customer.last_interaction_at.isoformat() if customer.last_interaction_at else None,
        "updated_at": customer.updated_at.isoformat(),
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
    return list(db.scalars(statement))


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


def ensure_role(db: Session, name: str) -> models.Role:
    statement = select(models.Role).where(models.Role.name == name)
    role = db.scalars(statement).first()
    if role is None:
        role = models.Role(name=name)
        db.add(role)
        db.flush()
    return role


def list_roles(db: Session) -> list[models.Role]:
    statement = select(models.Role).order_by(models.Role.name.asc())
    return list(db.scalars(statement))


def get_user_by_username(db: Session, username: str) -> models.User | None:
    statement = select(models.User).options(joinedload(models.User.roles).joinedload(models.UserRole.role)).where(
        models.User.username == username
    )
    return db.scalars(statement).first()


def get_user(db: Session, user_id: int) -> models.User:
    statement = (
        select(models.User)
        .options(joinedload(models.User.roles).joinedload(models.UserRole.role))
        .where(models.User.id == user_id)
    )
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("user_not_found") from exc


def create_user(
    db: Session,
    payload: schemas.UserCreate,
    *,
    password_hash: str,
    role_names: Iterable[str],
) -> models.User:
    user = models.User(username=payload.username, full_name=payload.full_name, password_hash=password_hash)
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


def list_users(db: Session) -> list[models.User]:
    statement = select(models.User).options(joinedload(models.User.roles).joinedload(models.UserRole.role)).order_by(
        models.User.username.asc()
    )
    return list(db.scalars(statement))


def set_user_roles(db: Session, user: models.User, role_names: Iterable[str]) -> models.User:
    user.roles.clear()
    db.flush()
    for role_name in role_names:
        role = ensure_role(db, role_name)
        db.add(models.UserRole(user=user, role=role))

    db.commit()
    db.refresh(user)
    return user


def set_user_status(
    db: Session,
    user: models.User,
    *,
    is_active: bool,
    performed_by_id: int | None = None,
) -> models.User:
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    _log_action(
        db,
        action="user_status_changed",
        entity_type="user",
        entity_id=str(user.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"is_active": is_active}),
    )
    db.commit()
    db.refresh(user)
    return user


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


def create_active_session(db: Session, user_id: int, *, session_token: str) -> models.ActiveSession:
    session = models.ActiveSession(user_id=user_id, session_token=session_token)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_active_session_by_token(db: Session, session_token: str) -> models.ActiveSession | None:
    statement = select(models.ActiveSession).where(models.ActiveSession.session_token == session_token)
    return db.scalars(statement).first()


def mark_session_used(db: Session, session_token: str) -> models.ActiveSession | None:
    session = get_active_session_by_token(db, session_token)
    if session is None or session.revoked_at is not None:
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


def create_store(db: Session, payload: schemas.StoreCreate, *, performed_by_id: int | None = None) -> models.Store:
    store = models.Store(**payload.model_dump())
    db.add(store)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
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
) -> list[models.Customer]:
    statement = select(models.Customer).order_by(models.Customer.name.asc()).limit(limit)
    if query:
        normalized = f"%{query.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.Customer.name).like(normalized),
                func.lower(models.Customer.contact_name).like(normalized),
                func.lower(models.Customer.email).like(normalized),
            )
        )
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
    customer = models.Customer(
        name=payload.name,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        notes=payload.notes,
        history=history,
        outstanding_debt=_to_decimal(payload.outstanding_debt),
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
    updated_fields: dict[str, object] = {}
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
    if payload.notes is not None:
        customer.notes = payload.notes
        updated_fields["notes"] = payload.notes
    if payload.outstanding_debt is not None:
        customer.outstanding_debt = _to_decimal(payload.outstanding_debt)
        updated_fields["outstanding_debt"] = float(customer.outstanding_debt)
    if payload.history is not None:
        history = _history_to_json(payload.history)
        customer.history = history
        customer.last_interaction_at = _last_history_timestamp(history)
        updated_fields["history"] = history
    db.add(customer)
    db.commit()
    db.refresh(customer)

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
) -> str:
    customers = list_customers(db, query=query, limit=5000)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ID",
            "Nombre",
            "Contacto",
            "Correo",
            "Teléfono",
            "Dirección",
            "Deuda",
            "Última interacción",
        ]
    )
    for customer in customers:
        writer.writerow(
            [
                customer.id,
                customer.name,
                customer.contact_name or "",
                customer.email or "",
                customer.phone or "",
                customer.address or "",
                float(customer.outstanding_debt),
                customer.last_interaction_at.isoformat()
                if customer.last_interaction_at
                else "",
            ]
        )
    return buffer.getvalue()


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
    unit_price = payload_data.get("unit_price") if "unit_price" in provided_fields else None
    if unit_price is None:
        payload_data.setdefault("unit_price", Decimal("0"))
    if payload_data.get("costo_unitario") is None:
        payload_data["costo_unitario"] = Decimal("0")
    if payload_data.get("margen_porcentaje") is None:
        payload_data["margen_porcentaje"] = Decimal("0")
    if payload_data.get("estado_comercial") is None:
        payload_data["estado_comercial"] = models.CommercialState.NUEVO
    if payload_data.get("garantia_meses") is None:
        payload_data["garantia_meses"] = 0
    device = models.Device(store_id=store_id, **payload_data)
    if unit_price is None:
        _recalculate_sale_price(device)
    else:
        device.unit_price = unit_price
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
    elif {"costo_unitario", "margen_porcentaje"}.intersection(updated_fields):
        _recalculate_sale_price(device)
    db.commit()
    db.refresh(device)

    fields_changed = list(updated_fields.keys())
    if manual_price is not None:
        fields_changed.append("unit_price")
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
    return device


def list_devices(
    db: Session,
    store_id: int,
    *,
    search: str | None = None,
    estado: models.CommercialState | None = None,
) -> list[models.Device]:
    get_store(db, store_id)
    statement = select(models.Device).where(models.Device.store_id == store_id)
    if estado is not None:
        statement = statement.where(models.Device.estado_comercial == estado)
    if search:
        normalized = f"%{search.lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.Device.sku).like(normalized),
                func.lower(models.Device.name).like(normalized),
                func.lower(models.Device.modelo).like(normalized),
                func.lower(models.Device.marca).like(normalized),
                func.lower(models.Device.color).like(normalized),
                func.lower(models.Device.serial).like(normalized),
                func.lower(models.Device.imei).like(normalized),
                func.lower(models.Device.estado_comercial).like(normalized),
            )
        )
    statement = statement.order_by(models.Device.sku.asc())
    return list(db.scalars(statement))


def search_devices(db: Session, filters: schemas.DeviceSearchFilters) -> list[models.Device]:
    statement = (
        select(models.Device)
        .options(joinedload(models.Device.store))
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
    device = get_device(db, store_id, payload.device_id)

    if payload.movement_type == models.MovementType.OUT and device.quantity < payload.quantity:
        raise ValueError("insufficient_stock")

    if payload.movement_type == models.MovementType.IN:
        device.quantity += payload.quantity
        if payload.unit_cost is not None:
            current_total_cost = _to_decimal(device.costo_unitario) * _to_decimal(device.quantity - payload.quantity)
            incoming_cost_total = _to_decimal(payload.unit_cost) * _to_decimal(payload.quantity)
            divisor = _to_decimal(device.quantity or 1)
            average_cost = (current_total_cost + incoming_cost_total) / divisor
            device.costo_unitario = average_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            _recalculate_sale_price(device)
    elif payload.movement_type == models.MovementType.OUT:
        device.quantity -= payload.quantity
    elif payload.movement_type == models.MovementType.ADJUST:
        device.quantity = payload.quantity

    movement = models.InventoryMovement(
        store=store,
        device=device,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        reason=payload.reason,
        unit_cost=_to_decimal(payload.unit_cost) if payload.unit_cost is not None else None,
        performed_by_id=performed_by_id,
    )
    db.add(movement)
    db.commit()
    db.refresh(device)
    db.refresh(movement)

    _log_action(
        db,
        action="inventory_movement",
        entity_type="device",
        entity_id=str(device.id),
        performed_by_id=performed_by_id,
        details=f"tipo={payload.movement_type.value}, cantidad={payload.quantity}",
    )
    db.commit()
    db.refresh(movement)
    total_value = _recalculate_store_inventory_value(db, store_id)
    setattr(movement, "store_inventory_value", total_value)
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
        details=f"estado={status.value}; modo={mode.value}",
    )
    db.commit()
    db.refresh(session)
    return session


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

    _require_store_permission(
        db,
        user_id=requested_by_id,
        store_id=origin_store.id,
        permission="create",
    )

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
    limit: int = 50,
) -> list[models.TransferOrder]:
    statement = (
        select(models.TransferOrder)
        .options(joinedload(models.TransferOrder.items))
        .order_by(models.TransferOrder.created_at.desc())
        .limit(limit)
    )
    if store_id is not None:
        statement = statement.where(
            (models.TransferOrder.origin_store_id == store_id)
            | (models.TransferOrder.destination_store_id == store_id)
        )
    return list(db.scalars(statement).unique())


def count_users(db: Session) -> int:
    return db.scalar(select(func.count(models.User.id))) or 0


def create_backup_job(
    db: Session,
    *,
    mode: models.BackupMode,
    pdf_path: str,
    archive_path: str,
    total_size_bytes: int,
    notes: str | None,
    triggered_by_id: int | None,
) -> models.BackupJob:
    job = models.BackupJob(
        mode=mode,
        pdf_path=pdf_path,
        archive_path=archive_path,
        total_size_bytes=total_size_bytes,
        notes=notes,
        triggered_by_id=triggered_by_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _log_action(
        db,
        action="backup_generated",
        entity_type="backup",
        entity_id=str(job.id),
        performed_by_id=triggered_by_id,
        details=f"modo={mode.value}; tamaño={total_size_bytes}",
    )
    db.commit()
    db.refresh(job)
    return job


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
    return order


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
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=receive_item.quantity,
                reason=reason,
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
    return order


def cancel_purchase_order(
    db: Session,
    order_id: int,
    *,
    cancelled_by_id: int,
    reason: str | None = None,
) -> models.PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order.status in {models.PurchaseStatus.CANCELADA, models.PurchaseStatus.COMPLETADA}:
        raise ValueError("purchase_not_cancellable")

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
        details=json.dumps({"status": order.status.value, "reason": reason}),
    )
    db.commit()
    db.refresh(order)
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

    db.add(
        models.InventoryMovement(
            store_id=order.store_id,
            device_id=device.id,
            movement_type=models.MovementType.OUT,
            quantity=payload.quantity,
            reason=payload.reason or reason,
            performed_by_id=processed_by_id,
        )
    )

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
                    device_id=device.id,
                    movement_type=models.MovementType.OUT,
                    quantity=delta,
                    reason=reason or f"Reparación #{order.id}",
                    performed_by_id=performed_by_id,
                )
            )
        elif delta < 0:
            device.quantity += abs(delta)
            db.add(
                models.InventoryMovement(
                    store_id=order.store_id,
                    device_id=device.id,
                    movement_type=models.MovementType.IN,
                    quantity=abs(delta),
                    reason=reason or f"Ajuste reparación #{order.id}",
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
                    device_id=device.id,
                    movement_type=models.MovementType.IN,
                    quantity=part.quantity,
                    reason=reason or f"Reverso reparación #{order.id}",
                    performed_by_id=performed_by_id,
                )
            )
            db.delete(part)

    order.parts_cost = total_cost
    order.parts_snapshot = snapshot
    order.inventory_adjusted = bool(processed_devices)
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
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=part.quantity,
                reason=reason or f"Cancelación reparación #{order.id}",
                performed_by_id=performed_by_id,
            )
        )
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


def list_sales(db: Session, *, store_id: int | None = None, limit: int = 50) -> list[models.Sale]:
    statement = (
        select(models.Sale)
        .options(
            joinedload(models.Sale.items),
            joinedload(models.Sale.returns),
            joinedload(models.Sale.customer),
            joinedload(models.Sale.cash_session),
        )
        .order_by(models.Sale.created_at.desc())
        .limit(limit)
    )
    if store_id is not None:
        statement = statement.where(models.Sale.store_id == store_id)
    return list(db.scalars(statement).unique())


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
        )
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("sale_not_found") from exc


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
    sale = models.Sale(
        store_id=payload.store_id,
        customer_id=customer.id if customer else None,
        customer_name=customer_name,
        payment_method=models.PaymentMethod(payload.payment_method),
        discount_percent=sale_discount_percent.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        notes=payload.notes,
        performed_by_id=performed_by_id,
    )
    db.add(sale)
    db.flush()

    gross_total = Decimal("0")
    total_discount = Decimal("0")
    for item in payload.items:
        if item.quantity <= 0:
            raise ValueError("sale_invalid_quantity")
        device = get_device(db, payload.store_id, item.device_id)
        if device.quantity < item.quantity:
            raise ValueError("sale_insufficient_stock")

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

        sale_item = models.SaleItem(
            sale_id=sale.id,
            device_id=device.id,
            quantity=item.quantity,
            unit_price=line_unit_price,
            discount_amount=line_discount_amount,
            total_line=net_line_total,
        )
        db.add(sale_item)

        db.add(
            models.InventoryMovement(
                store_id=payload.store_id,
                device_id=device.id,
                movement_type=models.MovementType.OUT,
                quantity=item.quantity,
                reason=reason,
                performed_by_id=performed_by_id,
            )
        )

    subtotal = (gross_total - total_discount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    sale.subtotal_amount = subtotal

    tax_value = _to_decimal(tax_rate)
    if tax_value < Decimal("0"):
        tax_value = Decimal("0")
    tax_fraction = tax_value / Decimal("100") if tax_value else Decimal("0")
    tax_amount = (subtotal * tax_fraction).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sale.tax_amount = tax_amount
    sale.total_amount = (subtotal + tax_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if customer:
        if sale.payment_method == models.PaymentMethod.CREDITO:
            customer.outstanding_debt = (
                _to_decimal(customer.outstanding_debt) + sale.total_amount
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        _append_customer_history(
            customer,
            f"Venta #{sale.id} registrada ({sale.payment_method.value})",
        )
        db.add(customer)

    db.commit()
    db.refresh(sale)

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
                device_id=item.device_id,
                movement_type=models.MovementType.IN,
                quantity=item.quantity,
                reason=item.reason or reason,
                performed_by_id=processed_by_id,
            )
        )

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

    snapshot = {
        "stores": [
            {
                "id": store.id,
                "name": store.name,
                "location": store.location,
                "timezone": store.timezone,
                "devices": [
                    {
                        "id": device.id,
                        "sku": device.sku,
                        "name": device.name,
                        "quantity": device.quantity,
                        "store_id": device.store_id,
                        "unit_price": float(device.unit_price or Decimal("0")),
                        "inventory_value": float(_device_value(device)),
                    }
                    for device in store.devices
                ],
            }
            for store in stores
        ],
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
                "store_id": movement.store_id,
                "device_id": movement.device_id,
                "movement_type": movement.movement_type.value,
                "quantity": movement.quantity,
                "reason": movement.reason,
                "performed_by_id": movement.performed_by_id,
                "created_at": movement.created_at.isoformat(),
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
    }
    return snapshot
