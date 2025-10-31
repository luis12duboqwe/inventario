"""Puente hacia las rutas de actualizaciones del núcleo Softmobile."""

from __future__ import annotations

from backend.app.routers import updates as core_updates

from ._core_bridge import mount_core_router

router = mount_core_router(core_updates.router)

__all__ = ["router"]
