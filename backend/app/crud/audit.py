"""Operaciones CRUD para el módulo de Auditoría."""
from __future__ import annotations

import copy
import csv
import json
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta
from io import StringIO

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, telemetry
from ..core.transactions import flush_session, transactional_session
from ..utils import audit as audit_utils
from ..utils import audit_trail as audit_trail_utils
from ..utils.cache import TTLCache


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
        if acknowledgement and acknowledgement.acknowledged_at >= last_seen:
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
