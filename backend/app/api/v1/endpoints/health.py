"""Health check endpoints."""
from fastapi import APIRouter

from .... import schemas

router = APIRouter()


@router.get(
    "/health",
    summary="Confirmar estado del servicio",
    response_model=schemas.HealthStatusResponse,
)
async def health() -> schemas.HealthStatusResponse:
    """Return basic service status."""

    return schemas.HealthStatusResponse(status="ok")
