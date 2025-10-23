"""Puente hacia las rutas de compras del núcleo Softmobile."""

from __future__ import annotations

from backend.app.routers import purchases as core_purchases

from ._core_bridge import mount_core_router

router = mount_core_router(core_purchases.router)

__all__ = ["router"]
