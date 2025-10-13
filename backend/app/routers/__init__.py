"""Colección de routers disponibles."""
from . import (
    auth,
    backups,
    health,
    inventory,
    reports,
    stores,
    sync,
    updates,
    users,
)  # noqa: F401

__all__ = [
    "auth",
    "backups",
    "health",
    "inventory",
    "reports",
    "stores",
    "sync",
    "updates",
    "users",
]
