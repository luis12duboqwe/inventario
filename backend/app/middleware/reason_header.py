"""Validación centralizada para el encabezado corporativo ``X-Reason``."""
from __future__ import annotations

from typing import Awaitable, Callable, Iterable, Sequence

from fastapi import Request
from starlette.responses import JSONResponse, Response

DEFAULT_EXPORT_TOKENS: tuple[str, ...] = ("/csv", "/pdf", "/xlsx", "/export/")
DEFAULT_EXPORT_PREFIXES: tuple[str, ...] = (
    "/reports",
    "/purchases",
    "/sales",
    "/backups",
    "/users",
)
DEFAULT_SENSITIVE_GET_PREFIXES: tuple[str, ...] = ("/pos/receipt", "/pos/config")

CallNext = Callable[[Request], Awaitable[Response]]


def _normalize_collection(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))


def build_reason_header_middleware(
    *,
    sensitive_methods: Iterable[str],
    sensitive_prefixes: Sequence[str],
    export_tokens: Iterable[str] = DEFAULT_EXPORT_TOKENS,
    export_prefixes: Iterable[str] = DEFAULT_EXPORT_PREFIXES,
    read_sensitive_get_prefixes: Iterable[str] = DEFAULT_SENSITIVE_GET_PREFIXES,
) -> Callable[[Request, CallNext], Awaitable[Response]]:
    """Crea un middleware que exige ``X-Reason`` cuando aplica."""

    sensitive_methods_set = {method.upper() for method in sensitive_methods}
    sensitive_prefixes_tuple = _normalize_collection(sensitive_prefixes)
    export_tokens_tuple = _normalize_collection(export_tokens)
    export_prefixes_tuple = _normalize_collection(export_prefixes)
    read_sensitive_prefixes_tuple = _normalize_collection(read_sensitive_get_prefixes)

    def _requires_reason_get(path: str) -> bool:
        if any(token in path for token in export_tokens_tuple) and any(
            path.startswith(prefix) for prefix in export_prefixes_tuple
        ):
            return True
        if any(path.startswith(prefix) for prefix in read_sensitive_prefixes_tuple):
            return True
        return False

    async def _middleware(request: Request, call_next: CallNext) -> Response:
        method_upper = request.method.upper()
        path = request.url.path

        requires_reason = (
            method_upper in sensitive_methods_set
            and any(path.startswith(prefix) for prefix in sensitive_prefixes_tuple)
        ) or (method_upper == "GET" and _requires_reason_get(path))

        # Starlette provee cabeceras case-insensitive, por lo que un solo get es suficiente.
        reason = request.headers.get("X-Reason")
        if requires_reason:
            if not reason or len(reason.strip()) < 5:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Reason header requerido"},
                )
            request.state.x_reason = reason.strip()
        else:
            if reason is not None and len(reason.strip()) < 5:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Reason header requerido"},
                )
            if reason:
                request.state.x_reason = reason.strip()
        return await call_next(request)

    return _middleware


__all__ = [
    "DEFAULT_EXPORT_PREFIXES",
    "DEFAULT_EXPORT_TOKENS",
    "DEFAULT_SENSITIVE_GET_PREFIXES",
    "build_reason_header_middleware",
]
