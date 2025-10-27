"""Rutas de ejemplo para validar la carga dinámica de routers."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.security import get_current_user

router = APIRouter(
    prefix="/ejemplo",
    tags=["ejemplo"],
    dependencies=[Depends(get_current_user)],
)


class ExampleResponse(BaseModel):
    """Modelo de respuesta genérico para pruebas de conectividad."""

    detail: str


@router.get(
    "/ping",
    response_model=ExampleResponse,
    dependencies=[Depends(get_current_user)],
)
async def get_example_ping() -> ExampleResponse:
    """Permite comprobar que las rutas de ejemplo están disponibles."""

    return ExampleResponse(detail="Ruta de ejemplo activa ✅")


__all__ = ["router"]

