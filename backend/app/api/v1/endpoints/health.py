"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Confirmar estado del servicio")
async def health() -> dict[str, str]:
    """Return basic service status."""

    return {"status": "ok"}
