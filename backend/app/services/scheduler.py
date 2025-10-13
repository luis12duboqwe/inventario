"""Orquestador de tareas periódicas para sincronización y respaldos."""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from .. import crud, models
from ..config import settings
from ..database import SessionLocal
from .backups import generate_backup

logger = logging.getLogger(__name__)


class _PeriodicJob:
    """Ejecuta una función en segundo plano cada cierto intervalo."""

    def __init__(self, name: str, interval_seconds: int, callback: Callable[[], None]) -> None:
        self.name = name
        self.interval_seconds = interval_seconds
        self._callback = callback
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
            except asyncio.CancelledError:  # pragma: no cover
                pass
            self._task = None

    async def _run(self) -> None:
        while self._running:
            await asyncio.sleep(self.interval_seconds)
            try:
                await asyncio.to_thread(self._callback)
            except Exception as exc:  # pragma: no cover - logueamos pero no detenemos la app
                logger.exception("Error en tarea periódica %s: %s", self.name, exc)


class BackgroundScheduler:
    """Coordina los jobs periódicos configurados por el sistema."""

    def __init__(self) -> None:
        self._jobs: list[_PeriodicJob] = []

        sync_interval = settings.sync_interval_seconds
        if sync_interval > 0:
            self._jobs.append(
                _PeriodicJob(
                    name="sincronizacion",
                    interval_seconds=sync_interval,
                    callback=_sync_job,
                )
            )

        if settings.enable_backup_scheduler and settings.backup_interval_seconds > 0:
            self._jobs.append(
                _PeriodicJob(
                    name="respaldos",
                    interval_seconds=settings.backup_interval_seconds,
                    callback=_backup_job,
                )
            )

    async def start(self) -> None:
        for job in self._jobs:
            await job.start()

    async def stop(self) -> None:
        for job in self._jobs:
            await job.stop()


def _sync_job() -> None:
    with SessionLocal() as session:
        crud.record_sync_session(
            session,
            store_id=None,
            mode=models.SyncMode.AUTOMATIC,
            status=models.SyncStatus.SUCCESS,
            triggered_by_id=None,
        )


def _backup_job() -> None:
    with SessionLocal() as session:
        generate_backup(
            session,
            base_dir=settings.backup_directory,
            mode=models.BackupMode.AUTOMATIC,
            triggered_by_id=None,
            notes="Respaldo automático programado",
        )
