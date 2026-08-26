"""Puentes temporales para contratos de sincronización perdidos en la extracción CRUD."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from . import recovery_compat


def create_device(
    db: Session,
    store_id: int,
    payload: schemas.DeviceCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Device:
    """Crea el dispositivo y restaura su evento de replicación híbrida."""
    from . import devices as devices_crud
    from . import sync as sync_crud

    device = recovery_compat.create_device(
        db,
        store_id,
        payload,
        performed_by_id=performed_by_id,
    )
    sync_crud.enqueue_sync_outbox(
        db,
        entity_type="device",
        entity_id=str(device.id),
        operation="UPSERT",
        payload=devices_crud._device_sync_payload(device),
        store_id=device.store_id,
    )
    return device


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_store_sync_overview(
    db: Session,
    *,
    store_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    """Restaura el overview legacy normalizando timestamps de SQLite a UTC."""
    stores_stmt = (
        select(
            models.Store.id,
            models.Store.name,
            models.Store.code,
            models.Store.timezone,
            models.Store.inventory_value,
        )
        .where(models.Store.is_deleted.is_(False))
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

    latest_by_store: dict[int, models.SyncSession] = {}
    latest_global: models.SyncSession | None = None
    for session in db.scalars(session_stmt):
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
            data = json.loads(log.details or "{}") if log.details else {}
        except json.JSONDecodeError:
            data = {}
        for key in ("max", "min"):
            entries = data.get(key) or []
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                candidate = entry.get("store_id") or entry.get("sucursal_id")
                try:
                    candidate_id = int(candidate)
                except (TypeError, ValueError):
                    continue
                if store_id is not None and candidate_id != store_id:
                    continue
                conflict_counts[candidate_id] += 1

    results: list[dict[str, object]] = []
    now = datetime.now(timezone.utc)
    stale_threshold = timedelta(hours=12)
    for row in store_rows:
        key = int(row.id)
        session = latest_by_store.get(key) or latest_global
        last_status = session.status if session else None
        last_mode = session.mode if session else None
        last_timestamp = (session.finished_at or session.started_at) if session else None
        comparison_timestamp = _aware_utc(last_timestamp)

        health = schemas.SyncBranchHealth.UNKNOWN
        label = "Sin registros de sincronización"
        if session:
            timestamp_label = (
                comparison_timestamp.astimezone().strftime("%d/%m/%Y %H:%M")
                if comparison_timestamp
                else "sin hora"
            )
            if session.status is models.SyncStatus.FAILED:
                health = schemas.SyncBranchHealth.CRITICAL
                label = f"Fallo registrado el {timestamp_label}"
            else:
                health = schemas.SyncBranchHealth.OPERATIVE
                label = f"Actualizado el {timestamp_label}"
                if comparison_timestamp and now - comparison_timestamp > stale_threshold:
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


__all__ = ["create_device", "get_store_sync_overview"]
