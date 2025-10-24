"""Compatibilidad con ``fastapi-limiter.depends`` real o stub local."""
from __future__ import annotations

import inspect
from typing import Any

from fastapi import Request

from . import FastAPILimiter
from ._resolver import load_real_module


_REAL_DEPENDS = load_real_module("fastapi_limiter.depends")


if _REAL_DEPENDS is not None and hasattr(_REAL_DEPENDS, "RateLimiter"):
    RateLimiter = _REAL_DEPENDS.RateLimiter  # type: ignore[assignment]
    __all__ = list(getattr(_REAL_DEPENDS, "__all__", ["RateLimiter"]))
else:

    class RateLimiter:
        """Stub que satisface la firma esperada por FastAPI y las pruebas."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.times = kwargs.get("times", args[0] if args else None)
            self.minutes = kwargs.get("minutes")

        async def __call__(self, request: Request) -> None:  # pragma: no cover - comportamiento trivial
            identifier = FastAPILimiter.identifier
            if identifier is None:
                return None
            result = identifier(request)
            if inspect.isawaitable(result):
                await result
            return None

    __all__ = ["RateLimiter"]

# Garantiza que FastAPI resuelva la anotación aun con ``from __future__ import annotations``.
if "request" not in RateLimiter.__call__.__annotations__:
    RateLimiter.__call__.__annotations__["request"] = Request

