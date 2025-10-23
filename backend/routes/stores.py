"""Puente hacia las rutas de sucursales del núcleo Softmobile."""

from __future__ import annotations

from backend.app.routers import stores as core_stores

from ._core_bridge import mount_core_router

router = mount_core_router(core_stores.router)

__all__ = ["router"]
