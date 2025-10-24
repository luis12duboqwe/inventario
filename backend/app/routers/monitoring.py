"""Rutas de monitoreo y métricas Prometheus."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .. import schemas
from ..core.roles import ADMIN
from ..security import require_roles
from ..telemetry import REGISTRY

router = APIRouter(prefix="/monitoring", tags=["monitoreo"])


@router.get("/metrics", response_model=schemas.BinaryFileResponse)
def prometheus_metrics(current_user=Depends(require_roles(ADMIN))):  # noqa: ANN001
    """Expone las métricas internas en formato Prometheus."""

    data = generate_latest(REGISTRY)
    metadata = schemas.BinaryFileResponse(
        filename="metrics.prom",
        media_type=CONTENT_TYPE_LATEST,
    )
    return Response(content=data, media_type=metadata.media_type)


__all__ = ["router"]
