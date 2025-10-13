"""Servicio de sincronización periódica."""
from __future__ import annotations

import asyncio
import logging

from .. import crud, models
from ..database import SessionLocal

logger = logging.getLogger(__name__)


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
