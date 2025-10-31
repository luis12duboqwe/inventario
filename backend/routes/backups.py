"""Puente hacia las rutas de respaldos del núcleo Softmobile."""

from __future__ import annotations

from backend.app.routers import backups as core_backups

from ._core_bridge import mount_core_router

router = mount_core_router(core_backups.router)

__all__ = ["router"]
