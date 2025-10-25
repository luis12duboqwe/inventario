"""Router de trabajos asíncronos y observabilidad ligera."""
from __future__ import annotations

import os
import time
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, status

from backend.app.core.roles import GESTION_ROLES
from backend.app.routers.dependencies import require_reason
from backend.app.security import require_roles
from backend.core.logging import logger as core_logger
from backend.schemas.jobs import ExportJobRequest, ExportJobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

logger = core_logger.bind(component="backend.routes.jobs")


def _simulate_export(job_id: str, payload: ExportJobRequest) -> None:
    """Simula la generación de un archivo exportable en segundo plano."""

    logger.bind(job_id=job_id, format=payload.format).info("export.job.started")
    time.sleep(0.1)
    logger.bind(job_id=job_id).info("export.job.completed")


@router.post(
    "/export",
    response_model=ExportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_export_job(
    payload: ExportJobRequest,
    background: BackgroundTasks,
    reason: str = Depends(require_reason),
    current_user=Depends(require_roles(*GESTION_ROLES)),
) -> ExportJobResponse:
    """Encola un trabajo de exportación reutilizando BackgroundTasks."""

    del reason, current_user
    job_id = uuid4().hex
    redis_url = os.getenv("REDIS_URL")
    backend: str
    if redis_url:
        backend = "redis"
        logger.bind(job_id=job_id, redis_url=redis_url).info("export.job.enqueued.redis")
    else:
        backend = "local"
        background.add_task(_simulate_export, job_id, payload)
        logger.bind(job_id=job_id).info("export.job.enqueued.local")
    return ExportJobResponse(
        job_id=job_id,
        status="queued",
        backend=backend,
        requested_at=datetime.utcnow(),
    )


__all__ = ["router"]
