"""Modelos ligeros de sucursales para el backend simplificado."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Store:
    """Representa una sucursal registrada en el backend ligero."""

    id: int
    name: str
    code: str
    address: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


@dataclass(slots=True)
class StoreMembership:
    """Asociación básica entre usuario y sucursal."""

    id: int
    store_id: int
    user_id: int
    can_create_transfer: bool = field(default=False)
    can_receive_transfer: bool = field(default=False)
    created_at: datetime | None = None


__all__ = ["Store", "StoreMembership"]
