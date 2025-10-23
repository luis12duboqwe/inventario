"""Endpoint de salud de la API."""
from __future__ import annotations

from fastapi import APIRouter

from ..config import settings

router = APIRouter(tags=["monitoring"])


@router.get("/health", summary="Verificar el estado de la API")
def read_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/", include_in_schema=False, summary="Mensaje de bienvenida")
def read_root() -> dict[str, str]:
    return {
        "message": "Inventario Softmobile operativo",
        "service": settings.title,
    }
