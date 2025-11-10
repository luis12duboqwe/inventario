"""Orquestador de tareas periódicas para sincronización y respaldos."""
from __future__ import annotations

import asyncio
from functools import partial
from typing import Callable

from backend.core.logging import logger as core_logger

from .. import crud, models
from ..config import settings
from ..core.session_provider import SessionProvider
from ..database import SessionLocal
from ..core.transactions import transactional_session
from . import customer_segments, sync as sync_service
from .backups import generate_backup

logger = core_logger.bind(component=__name__)


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
                logger.debug(
                    f"Tarea periódica {self.name} cancelada limpiamente."
                )
            self._task = None

    async def _run(self) -> None:
        while self._running:
            await asyncio.sleep(self.interval_seconds)
            try:
                await asyncio.to_thread(self._callback)
            except Exception as exc:  # pragma: no cover - logueamos pero no detenemos la app
                logger.exception(
                    f"Error en tarea periódica {self.name}: {exc}"
                )


class BackgroundScheduler:
    """Coordina los jobs periódicos configurados por el sistema."""

    def __init__(self, *, session_provider: SessionProvider | None = None) -> None:
        self._jobs: list[_PeriodicJob] = []
        self._session_provider: SessionProvider = session_provider or SessionLocal

        sync_interval = settings.sync_interval_seconds
        if sync_interval > 0:
            self._jobs.append(
                _PeriodicJob(
                    name="sincronizacion",
                    interval_seconds=sync_interval,
                    callback=partial(_sync_job, self._session_provider),
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

        reservations_interval = settings.reservations_expiration_interval_seconds
        if reservations_interval > 0:
            self._jobs.append(
                _PeriodicJob(
                    name="reservas_inventario",
                    interval_seconds=reservations_interval,
                    callback=_reservation_cleanup_job,
                )
            )

        segments_interval = settings.customer_segmentation_interval_seconds
        if segments_interval > 0:
            self._jobs.append(
                _PeriodicJob(
                    name="segmentos_clientes",
                    interval_seconds=segments_interval,
                    callback=partial(
                        _customer_segments_job, self._session_provider
                    ),
                )
            )

    async def start(self) -> None:
        for job in self._jobs:
            await job.start()

    async def stop(self) -> None:
        for job in self._jobs:
            await job.stop()


def _sync_job(session_provider: SessionProvider | None = None) -> None:
    provider = session_provider or SessionLocal
    with provider() as session:
        status = models.SyncStatus.SUCCESS
        processed_events = 0
        differences_count = 0
        error_message: str | None = None
        try:
            with transactional_session(session):
                requeued = sync_service.requeue_failed_outbox_entries(session)
                if requeued:
                    logger.info(
                        f"Cola híbrida: {len(requeued)} eventos listos para reintentar"
                    )
                result = sync_service.run_sync_cycle(session, performed_by_id=None)
                processed_events = int(result.get("processed", 0))
                discrepancies = result.get("discrepancies", [])
                differences_count = (
                    len(discrepancies) if isinstance(discrepancies, list) else 0
                )
        except Exception as exc:  # pragma: no cover - logged error path
            status = models.SyncStatus.FAILED
            error_message = str(exc)
            logger.exception(
                f"Fallo durante el job automático de sincronización: {exc}"
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


def _backup_job() -> None:
    with SessionLocal() as session:
        with transactional_session(session):
            generate_backup(
                session,
                base_dir=settings.backup_directory,
                mode=models.BackupMode.AUTOMATIC,
                triggered_by_id=None,
                notes="Respaldo automático programado",
            )


def _reservation_cleanup_job() -> None:
    with SessionLocal() as session:
        with transactional_session(session):
            expired = crud.expire_reservations(session)
            if expired:
                logger.info(
                    "Reservas vencidas liberadas automáticamente",
                    extra={"reservations_expired": expired},
                )


def _customer_segments_job(session_provider: SessionProvider | None = None) -> None:
    provider = session_provider or SessionLocal
    with provider() as session:
        try:
            result = customer_segments.refresh_customer_segments(session)
            logger.info(
                "Segmentos de clientes actualizados",
                extra={
                    "customers_processed": result.updated_customers,
                    "segments": {
                        key: len(value)
                        for key, value in result.segments.items()
                    },
                },
            )
        except Exception as exc:  # pragma: no cover - ruta de error
            logger.exception(
                "Fallo durante el job automático de segmentos de clientes",
                extra={"error": str(exc)},
            )
