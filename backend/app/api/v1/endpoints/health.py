"""Health check endpoints."""
from fastapi import APIRouter, Depends

from .... import schemas
from ....security import get_current_user

router = APIRouter()


@router.get(
    "/health",
    summary="Confirmar estado del servicio",
    response_model=schemas.HealthStatusResponse,
    dependencies=[Depends(get_current_user)],
)
async def health() -> schemas.HealthStatusResponse:
    """Return basic service status."""

    return schemas.HealthStatusResponse(status="ok")
