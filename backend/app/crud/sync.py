"""Operaciones CRUD para la sincronización."""
from __future__ import annotations

import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..core.transactions import transactional_session

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
        return entry
