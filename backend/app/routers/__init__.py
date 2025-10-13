"""Colección de routers disponibles."""
from . import auth, health, inventory, reports, stores, sync, users  # noqa: F401

__all__ = ["auth", "health", "inventory", "reports", "stores", "sync", "users"]
