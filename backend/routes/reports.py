"""Puente hacia las rutas de reportes del núcleo Softmobile."""

from __future__ import annotations

from backend.app.routers import reports as core_reports

from ._core_bridge import mount_core_router

router = mount_core_router(core_reports.router)

__all__ = ["router"]
