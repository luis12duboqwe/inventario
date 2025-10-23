"""Utilidades para exponer routers principales en la capa simplificada."""

from __future__ import annotations

from fastapi import APIRouter


def mount_core_router(core_router: APIRouter) -> APIRouter:
    """Genera un ``APIRouter`` que incluye el router del núcleo."""

    bridge = APIRouter()
    bridge.include_router(core_router)
    return bridge


# ``backend/main.py`` espera encontrar un objeto ``router`` en cada módulo.
# Definimos uno vacío para evitar advertencias al cargar utilidades internas.
router = APIRouter()


__all__ = ["mount_core_router", "router"]
