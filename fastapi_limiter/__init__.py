"""Implementación mínima de ``fastapi-limiter`` para entornos sin la dependencia real."""
from __future__ import annotations

from typing import Any


class FastAPILimiter:
    """Stub compatible con la interfaz pública usada en las pruebas."""

    redis: Any = None
    identifier: Any = None

    @classmethod
    async def init(cls, redis: Any) -> None:
        cls.redis = redis

    @classmethod
    async def close(cls) -> None:
        cls.redis = None
        cls.identifier = None


__all__ = ["FastAPILimiter"]
