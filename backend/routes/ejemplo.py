"""Rutas de ejemplo para validar la carga dinámica de routers."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/ejemplo", tags=["ejemplo"])


class ExampleResponse(BaseModel):
    """Modelo de respuesta genérico para pruebas de conectividad."""

    detail: str


@router.get("/ping", response_model=ExampleResponse)
async def get_example_ping() -> ExampleResponse:
    """Permite comprobar que las rutas de ejemplo están disponibles."""

    return ExampleResponse(detail="Ruta de ejemplo activa ✅")


__all__ = ["router"]

