"""Puente hacia las rutas de sincronización del núcleo Softmobile."""

from __future__ import annotations

from backend.app.routers import sync as core_sync

from ._core_bridge import mount_core_router

router = mount_core_router(core_sync.router)

__all__ = ["router"]
