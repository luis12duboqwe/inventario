"""Modelos ligeros para la capa simplificada del backend."""
from __future__ import annotations

from .store import Store, StoreMembership
from .user import User

__all__ = ["Store", "StoreMembership", "User"]
