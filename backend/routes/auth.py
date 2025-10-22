"""Rutas básicas de autenticación para el arranque del backend."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthStatusResponse(BaseModel):
    """Respuesta simple para verificar el estado del módulo de autenticación."""

    message: str


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status() -> AuthStatusResponse:
    """Expone un mensaje indicando que el módulo de autenticación está activo."""

    return AuthStatusResponse(message="Módulo de autenticación operativo ✅")


__all__ = ["router"]

