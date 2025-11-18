"""Puente hacia los reportes diarios de ventas del núcleo Softmobile."""

from __future__ import annotations

from backend.app.routers import reports_sales as core_reports_sales

from ._core_bridge import mount_core_router

router = mount_core_router(core_reports_sales.router)

__all__ = ["router"]
