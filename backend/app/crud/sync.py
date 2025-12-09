"""Operaciones CRUD para la sincronización."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from .. import models
from ..core.transactions import transactional_session
from ..utils.sync_helpers import priority_weight

_OUTBOX_PRIORITY_MAP: dict[str, models.SyncOutboxPriority] = {
    "sale": models.SyncOutboxPriority.HIGH,
    "inventory_movement": models.SyncOutboxPriority.HIGH,
    "customer": models.SyncOutboxPriority.NORMAL,
    "supplier": models.SyncOutboxPriority.NORMAL,
    "purchase_order": models.SyncOutboxPriority.NORMAL,
    "transfer_order": models.SyncOutboxPriority.NORMAL,
    "user": models.SyncOutboxPriority.HIGH,
    "role": models.SyncOutboxPriority.HIGH,
    "permission": models.SyncOutboxPriority.HIGH,
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
    normalized = (entity_type or "").lower()
    return _OUTBOX_PRIORITY_MAP.get(normalized, models.SyncOutboxPriority.NORMAL)


def enqueue_sync_outbox(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    operation: str,
    payload: dict[str, object],
    store_id: int | None = None,
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
            previous_payload = entry.payload if isinstance(
                entry.payload, dict) else {}
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
            entry.priority = resolved_priority
            if conflict_flag:
                entry.conflict_flag = True
                entry.version += 1
        db.add(entry)

        if conflict_flag:
            # Registrar alerta de posible conflicto para auditoría del sincronizador.
            log_entry = models.SystemLog(
                usuario=None,
                modulo="inventario",
                accion="sync_conflict_potential",
                descripcion=f"Conflicto detectado en {entity_type}:{entity_id}",
                fecha=datetime.now(timezone.utc),
                nivel=models.SystemLogLevel.WARNING,
                audit_log=None,
            )
            db.add(log_entry)
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
            ).label("failed_count"),
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
                    (models.SyncOutbox.conflict_flag.is_(
                        True), models.SyncOutbox.updated_at),
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
                    int(row.failed or 0), int(
                        getattr(row, "failed_attempts", 0) or 0)
                ),
                "conflicts": max(int(row.conflicts or 0), 0),
                "latest_update": row.latest_update,
                "oldest_pending": row.oldest_pending,
                "last_conflict_at": row.last_conflict_at,
            }
        )
    results.sort(key=lambda item: (priority_weight(
        item["priority"]), item["entity_type"]))
    if limit is None:
        return results[offset:]
    return results[offset: offset + limit]


__all__ = [
    "enqueue_sync_outbox",
    "get_sync_outbox_statistics",
]
