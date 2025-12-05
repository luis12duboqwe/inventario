from __future__ import annotations

import json
import logging
import traceback
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, Response

from .. import crud, security as security_core
from ..database import SessionLocal
from ..core.transactions import transactional_session
from ..core.constants import MODULE_PERMISSION_PREFIXES

logger = logging.getLogger(__name__)


def _resolve_module(path: str) -> str | None:
    for prefix, module in MODULE_PERMISSION_PREFIXES:
        if path.startswith(prefix):
            return module
    return None


def persist_system_error(request: Request, exc: Exception, *, status_code: int | None = None) -> None:
    if status_code is not None and status_code < 500:
        return
    module = _resolve_module(request.url.path) or "general"
    message = getattr(exc, "detail", str(exc))
    if not isinstance(message, str):
        try:
            message = json.dumps(message, ensure_ascii=False)
        except Exception:  # pragma: no cover - degradado seguro
            message = str(message)
    stack_trace = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    client_host = request.client.host if request.client else None
    try:
        with SessionLocal() as session:
            with transactional_session(session):
                username: str | None = None
                auth_header = request.headers.get("Authorization") or ""
                token_parts = auth_header.split(" ", 1)
                if len(token_parts) == 2 and token_parts[0].lower() == "bearer":
                    token = token_parts[1].strip()
                    try:
                        payload = security_core.decode_token(token)
                        user = crud.get_user_by_username(
                            session, payload.sub)
                        if user is not None:
                            username = user.username
                    except HTTPException:
                        username = None
                crud.register_system_error(
                    session,
                    mensaje=message,
                    stack_trace=stack_trace,
                    modulo=module,
                    usuario=username,
                    ip_origen=client_host,
                )
    except Exception:  # pragma: no cover - evitamos fallos en el logger
        logger.exception(
            "No se pudo registrar el error del sistema en la bitácora."
        )


async def capture_internal_errors(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        return await call_next(request)
    except HTTPException as exc:
        persist_system_error(request, exc, status_code=exc.status_code)
        raise
    except Exception as exc:  # pragma: no cover - errores inesperados
        persist_system_error(request, exc)
        raise
