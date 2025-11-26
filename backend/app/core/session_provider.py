"""Contratos reutilizables para obtener sesiones de base de datos."""
from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session


class SessionProvider(Protocol):
    """Callable que retorna una sesión SQLAlchemy lista para usarse."""

    def __call__(self) -> Session:
        """Crea y retorna una sesión vinculada al motor configurado."""
