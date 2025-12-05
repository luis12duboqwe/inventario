"""Operaciones CRUD para el módulo de Auditoría."""
from __future__ import annotations

import copy
import csv
import json
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta, timezone
from io import StringIO

from sqlalchemy import func, or_, select, tuple_, case
from sqlalchemy.sql import Select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, telemetry
from ..core.transactions import flush_session, transactional_session
from ..utils import audit as audit_utils
from ..utils import audit_trail as audit_trail_utils
from ..utils.cache import TTLCache
from ..utils.misc_helpers import severity_weight
from .sync import get_sync_outbox_statistics


_PERSISTENT_ALERTS_CACHE: TTLCache[list[dict[str, object]]] = TTLCache(
    ttl_seconds=60.0
)


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


def create_system_log(
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
            fecha=datetime.now(timezone.utc),
            nivel=level,
            ip_origen=ip_address,
            audit_log=audit_log,
        )
        db.add(entry)
        flush_session(db)
    return entry


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
        create_system_log(
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
log_action = log_audit_event


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


def _normalize_date_range(
    date_from: date | datetime | None,
    date_to: date | datetime | None,
) -> tuple[datetime, datetime]:
    if date_from is None:
        start_dt = datetime.min
    elif isinstance(date_from, datetime):
        start_dt = date_from
    else:
        start_dt = datetime.combine(date_from, datetime.min.time())

    if date_to is None:
        end_dt = datetime.max
    elif isinstance(date_to, datetime):
        end_dt = date_to
    else:
        end_dt = datetime.combine(date_to, datetime.max.time())

    return start_dt, end_dt


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

    statement = select(models.AuditLog).order_by(
        models.AuditLog.created_at.desc())
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
            statement = statement.where(
                ~critical_condition, ~warning_condition)
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
            statement = statement.where(
                ~critical_condition, ~warning_condition)
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
    now = datetime.now(timezone.utc)

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

    now = datetime.now(timezone.utc)
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

    keys = {(str(alert["entity_type"]), str(alert["entity_id"]))
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
        entity_type = str(alert["entity_type"])
        entity_id = str(alert["entity_id"])
        last_seen = alert["last_seen"]

        if not isinstance(last_seen, datetime):
            continue

        key = (entity_type, entity_id)
        acknowledgement = acknowledgements.get(key)
        status = "pending"
        acknowledged_at = None
        acknowledged_by_id = None
        acknowledged_by_name = None
        acknowledged_note = None
        if acknowledgement:
            ack_at = acknowledgement.acknowledged_at
            if ack_at.tzinfo is None:
                ack_at = ack_at.replace(tzinfo=timezone.utc)
            else:
                ack_at = ack_at.astimezone(timezone.utc)

            last_seen_aware = last_seen
            if last_seen_aware.tzinfo is None:
                last_seen_aware = last_seen_aware.replace(tzinfo=timezone.utc)
            else:
                last_seen_aware = last_seen_aware.astimezone(timezone.utc)

            if ack_at >= last_seen_aware:
                status = "acknowledged"
                acknowledged_at = acknowledgement.acknowledged_at
                acknowledged_by_id = acknowledgement.acknowledged_by_id
                if acknowledgement.acknowledged_by is not None:
                    acknowledged_by_name = _user_display_name(
                        acknowledgement.acknowledged_by)
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
            fecha=datetime.now(timezone.utc),
            usuario=usuario,
        )
        db.add(error)
        flush_session(db)
        create_system_log(
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
    statement: Select,
    *,
    module: str | None = None,
    severity: models.SystemLogLevel | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Select:
    if module:
        statement = statement.where(models.SystemLog.modulo == module.lower())
    if severity:
        statement = statement.where(models.SystemLog.nivel == severity)
    if date_from:
        statement = statement.where(models.SystemLog.fecha >= date_from)
    if date_to:
        statement = statement.where(models.SystemLog.fecha <= date_to)
    return statement


def _apply_system_error_filters(
    statement: Select,
    *,
    module: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Select:
    if module:
        statement = statement.where(
            models.SystemError.modulo == module.lower())
    if date_from:
        statement = statement.where(models.SystemError.fecha >= date_from)
    if date_to:
        statement = statement.where(models.SystemError.fecha <= date_to)
    return statement


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
            if severity_weight(log.nivel) > severity_weight(existing.level):
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
        key=lambda alert: (severity_weight(alert.level),
                           alert.occurred_at or datetime.min),
        reverse=True,
    )

    recent_logs = [schemas.SystemLogEntry.model_validate(
        item) for item in logs]
    recent_errors = [schemas.SystemErrorEntry.model_validate(
        item) for item in errors]

    return schemas.GlobalReportOverview(
        generated_at=datetime.now(timezone.utc),
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
        generated_at=datetime.now(timezone.utc),
        filters=filters,
        activity_series=activity_series,
        module_distribution=module_distribution,
        severity_distribution=severity_distribution,
    )
