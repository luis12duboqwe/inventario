"""Compatibilidad mínima con ``fastapi-limiter`` real o stub local."""
from __future__ import annotations

from typing import Any

from ._resolver import load_real_module


_REAL_MODULE = load_real_module("fastapi_limiter")


if _REAL_MODULE is not None and hasattr(_REAL_MODULE, "FastAPILimiter"):
    FastAPILimiter = _REAL_MODULE.FastAPILimiter  # type: ignore[assignment]
    __all__ = list(getattr(_REAL_MODULE, "__all__", ["FastAPILimiter"]))
else:

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

