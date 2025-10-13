"""Colección de routers disponibles."""
from . import (  # noqa: F401
    auth,
    backups,
    health,
    inventory,
    reports,
    stores,
    sync,
    transfers,
    updates,
    users,
)

__all__ = [
    "auth",
    "backups",
    "health",
    "inventory",
    "reports",
    "stores",
    "sync",
    "transfers",
    "updates",
    "users",
]
