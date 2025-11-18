"""Puente hacia la bitácora de auditoría de interfaz."""

from __future__ import annotations

from backend.app.routers import audit_ui as core_audit_ui

from ._core_bridge import mount_core_router

router = mount_core_router(core_audit_ui.router)

__all__ = ["router"]
