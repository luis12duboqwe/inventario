"""Puente hacia las rutas de auditoría del núcleo Softmobile."""

from __future__ import annotations

from backend.app.routers import audit as core_audit

from ._core_bridge import mount_core_router

router = mount_core_router(core_audit.router)

__all__ = ["router"]
