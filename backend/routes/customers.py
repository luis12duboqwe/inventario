"""Puente hacia las rutas de clientes del núcleo Softmobile."""

from __future__ import annotations

from backend.app.routers import customers as core_customers

from ._core_bridge import mount_core_router

router = mount_core_router(core_customers.router)

__all__ = ["router"]
