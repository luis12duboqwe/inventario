"""Puente hacia las rutas de inventario del núcleo Softmobile."""

from __future__ import annotations

from backend.app.routers import inventory as core_inventory

from ._core_bridge import mount_core_router

router = mount_core_router(core_inventory.router)

__all__ = ["router"]
