"""Dependencias mínimas compatibles con ``fastapi-limiter`` real."""
from __future__ import annotations

import inspect
from typing import Any

from fastapi import Request

from . import FastAPILimiter


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
RateLimiter.__call__.__annotations__["request"] = Request
