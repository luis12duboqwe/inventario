"""Servicio de sincronización periódica y cola híbrida."""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.logging import logger as core_logger

from .. import crud, models
from ..config import settings
from ..core.session_provider import SessionProvider
from ..database import SessionLocal
from ..core.transactions import transactional_session

logger = core_logger.bind(component=__name__)


def requeue_failed_outbox_entries(db: Session) -> list[models.SyncOutbox]:
    """Reagenda automáticamente eventos fallidos en la cola híbrida."""

    if not settings.enable_hybrid_prep:
        return []

    retry_after = timedelta(seconds=settings.sync_retry_interval_seconds)
    now = datetime.now(timezone.utc)
    candidates = crud.list_sync_outbox(
        db,
        statuses=(models.SyncOutboxStatus.FAILED, models.SyncOutboxStatus.PENDING),
        limit=200,
    )

    ready_ids: list[int] = []
    for entry in candidates:
        if entry.status == models.SyncOutboxStatus.SENT:
            continue
        if entry.attempt_count >= settings.sync_max_attempts:
            continue
        if entry.status == models.SyncOutboxStatus.PENDING and entry.attempt_count == 0:
            continue
        if entry.last_attempt_at and now - entry.last_attempt_at < retry_after:
            continue
        ready_ids.append(entry.id)

    if not ready_ids:
        return []

    logger.info(
        f"Reprogramando {len(ready_ids)} eventos híbridos para reintento"
    )
    return crud.reset_outbox_entries(
        db,
        ready_ids,
        reason="Reintento automático programado",
    )


def detect_inventory_discrepancies(db: Session) -> list[dict[str, object]]:
    """Compara cantidades por SKU entre sucursales y detecta diferencias."""

    stmt = (
        select(
            models.Device.sku.label("device_sku"),
            models.Device.id.label("device_id"),
            models.Device.name.label("device_name"),
            models.Device.store_id.label("store_id"),
            models.Store.name.label("store_name"),
            models.Device.quantity.label("quantity"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
        .order_by(models.Device.sku, models.Store.name)
    )
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in db.execute(stmt):
        mapping = row._mapping
        sku = mapping["device_sku"] or f"device-{mapping['device_id']}"
        grouped[sku].append(
            {
                "sku": sku,
                "device_id": mapping["device_id"],
                "product_name": mapping["device_name"],
                "store_id": mapping["store_id"],
                "store_name": mapping["store_name"],
                "quantity": int(mapping["quantity"] or 0),
            }
        )

    discrepancies: list[dict[str, object]] = []
    for sku, items in grouped.items():
        if len(items) < 2:
            continue
        quantities = [item["quantity"] for item in items]
        if not quantities:
            continue
        max_qty = max(quantities)
        min_qty = min(quantities)
        if max_qty == min_qty:
            continue
        max_stores = [
            {
                "store_id": item["store_id"],
                "store_name": item["store_name"],
                "quantity": item["quantity"],
            }
            for item in items
            if item["quantity"] == max_qty
        ]
        min_stores = [
            {
                "store_id": item["store_id"],
                "store_name": item["store_name"],
                "quantity": item["quantity"],
            }
            for item in items
            if item["quantity"] == min_qty
        ]
        discrepancies.append(
            {
                "sku": sku,
                "product_name": items[0]["product_name"],
                "diferencia": max_qty - min_qty,
                "max": max_stores,
                "min": min_stores,
            }
        )
    return discrepancies


def _entry_matches_store(entry: models.SyncOutbox, store_id: int | None) -> bool:
    if store_id is None:
        return True
    payload = entry.payload
    if not isinstance(payload, dict):
        try:
            raw_value = getattr(entry, "payload_raw", payload)
            payload = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            return False
    candidate: object | None = payload.get("store_id")
    if candidate is None:
        candidate = payload.get("origin_store_id")
    if candidate is None:
        candidate = payload.get("destination_store_id")
    if candidate is None:
        candidate = payload.get("sucursal_id")
    if candidate is None:
        return True
    try:
        return int(candidate) == int(store_id)
    except (TypeError, ValueError):
        return False


def run_sync_cycle(
    db: Session,
    *,
    store_id: int | None = None,
    performed_by_id: int | None = None,
    statuses: Iterable[models.SyncOutboxStatus] | None = None,
) -> dict[str, object]:
    """Procesa la cola híbrida marcando eventos enviados y registrando discrepancias."""

    selected_statuses = tuple(statuses) if statuses else (models.SyncOutboxStatus.PENDING,)
    pending_entries = crud.list_sync_outbox(db, statuses=selected_statuses, limit=500)
    filtered = [entry for entry in pending_entries if _entry_matches_store(entry, store_id)]
    processed: list[models.SyncOutbox] = []
    if filtered:
        processed = crud.mark_outbox_entries_sent(
            db,
            (entry.id for entry in filtered),
            performed_by_id=performed_by_id,
        )

    discrepancies = detect_inventory_discrepancies(db)
    if discrepancies:
        logger.warning(
            "Discrepancias de inventario detectadas tras sincronización",
            discrepancies=discrepancies,
            processed_entries=len(processed),
            store_filter=store_id,
        )
    crud.log_sync_discrepancies(db, discrepancies, performed_by_id=performed_by_id)
    return {"processed": len(processed), "discrepancies": discrepancies}


class SyncScheduler:
    """Ejecuta sincronizaciones automáticas cada intervalo configurado."""

    def __init__(
        self,
        interval_seconds: int,
        *,
        session_provider: SessionProvider | None = None,
    ) -> None:
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._session_provider: SessionProvider = session_provider or SessionLocal

    async def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:  # pragma: no cover - cancel path
                logger.debug("Ejecución automática de sincronización cancelada.")
            self._task = None

    async def _run(self) -> None:
        while self._running:
            await asyncio.sleep(self.interval_seconds)
            try:
                self._execute_sync()
            except Exception as exc:  # pragma: no cover - logged error path
                logger.exception(
                    f"Fallo al ejecutar la sincronización automática: {exc}"
                )

    def _execute_sync(self) -> None:
        with self._session_provider() as session:
            status = models.SyncStatus.SUCCESS
            processed_events = 0
            differences_count = 0
            error_message: str | None = None
            try:
                with transactional_session(session):
                    requeued = requeue_failed_outbox_entries(session)
                    if requeued:
                        logger.info(
                            f"Cola híbrida: {len(requeued)} eventos listos para reintentar"
                        )
                    result = run_sync_cycle(session, performed_by_id=None)
                    processed_events = int(result.get("processed", 0))
                    differences = result.get("discrepancies", [])
                    differences_count = (
                        len(differences) if isinstance(differences, list) else 0
                    )
            except Exception as exc:  # pragma: no cover - logged error path
                status = models.SyncStatus.FAILED
                error_message = str(exc)
                logger.exception(
                    f"Fallo al ejecutar la sincronización automática: {exc}"
                )
            finally:
                crud.record_sync_session(
                    session,
                    store_id=None,
                    mode=models.SyncMode.AUTOMATIC,
                    status=status,
                    triggered_by_id=None,
                    error_message=error_message,
                    processed_events=processed_events,
                    differences_detected=differences_count,
                )
