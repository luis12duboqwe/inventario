"""Endpoint de salud de la API."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["monitoring"])


@router.get("/health", summary="Verificar el estado de la API")
def read_health() -> dict[str, str]:
    return {"status": "ok"}
