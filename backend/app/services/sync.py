"""Servicio de sincronización periódica y cola híbrida."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .. import crud, models
from ..config import settings
from ..database import SessionLocal

logger = logging.getLogger(__name__)


def requeue_failed_outbox_entries(db: Session) -> list[models.SyncOutbox]:
    """Reagenda automáticamente eventos fallidos en la cola híbrida."""

    if not settings.enable_hybrid_prep:
        return []

    retry_after = timedelta(seconds=settings.sync_retry_interval_seconds)
    now = datetime.utcnow()
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

    logger.info("Reprogramando %s eventos híbridos para reintento", len(ready_ids))
    return crud.reset_outbox_entries(
        db,
        ready_ids,
        reason="Reintento automático programado",
    )


class SyncScheduler:
    """Ejecuta sincronizaciones automáticas cada intervalo configurado."""

    def __init__(self, interval_seconds: int) -> None:
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._running = False

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
                pass
            self._task = None

    async def _run(self) -> None:
        while self._running:
            await asyncio.sleep(self.interval_seconds)
            try:
                self._execute_sync()
            except Exception as exc:  # pragma: no cover - logged error path
                logger.exception("Fallo al ejecutar la sincronización automática: %s", exc)

    def _execute_sync(self) -> None:
        with SessionLocal() as session:
            crud.record_sync_session(
                session,
                store_id=None,
                mode=models.SyncMode.AUTOMATIC,
                status=models.SyncStatus.SUCCESS,
                triggered_by_id=None,
            )
            try:
                requeued = requeue_failed_outbox_entries(session)
                if requeued:
                    logger.info("Cola híbrida: %s eventos listos para reintentar", len(requeued))
            except Exception as exc:  # pragma: no cover - logging de cola
                logger.exception("No fue posible reagendar la cola híbrida: %s", exc)
