"""Dependencias comunes para los routers corporativos.

Se agregan utilidades opcionales para permitir flujos iniciales (bootstrap) sin
romper compatibilidad con dependencias estrictas en rutas protegidas.
"""

from fastapi import Header, HTTPException, Request, status, Depends
from fastapi import HTTPException as FastAPIHTTPException
from typing import Any

try:
    # Importación perezosa para evitar ciclos si cambia la estructura.
    from ..security import get_current_user  # type: ignore
except Exception:  # pragma: no cover
    # NOTA: Captura amplia intencional. Permite arranque del módulo incluso si
    # hay problemas de importación circular durante refactorización. Degradación
    # segura a None permite que get_current_user_optional funcione sin romper.
    get_current_user = None  # type: ignore


def require_reason(request: Request, x_reason: str | None = Header(default=None)) -> str:
    """Exige que las peticiones sensibles indiquen un motivo corporativo."""

    if x_reason and len(x_reason.strip()) >= 5:
        return x_reason.strip()

    stored_reason = getattr(request.state, "x_reason", None)
    if stored_reason and len(stored_reason.strip()) >= 5:
        return stored_reason.strip()

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Reason header requerido",
    )


def require_reason_optional(request: Request, x_reason: str | None = Header(default=None)) -> str | None:
    """Obtiene el motivo si está presente sin forzar validación estricta."""

    if x_reason and len(x_reason.strip()) >= 5:
        return x_reason.strip()

    stored_reason = getattr(request.state, "x_reason", None)
    if stored_reason and len(stored_reason.strip()) >= 5:
        return stored_reason.strip()

    return None


async def get_current_user_optional(request: Request) -> Any | None:
    """Devuelve el usuario autenticado si existe, o ``None`` si la solicitud no presenta credenciales válidas.

    Esto permite que rutas como el *bootstrap* acepten llamadas sin autenticación antes
    de que exista el primer usuario, preservando al mismo tiempo la validación cuando
    el encabezado/cookie/token está presente.
    """
    if get_current_user is None:  # pragma: no cover - degradación segura
        return None
    try:
        # FastAPI soporta dependencias async/sync; envolvemos en await si es coroutine.
        maybe_user = get_current_user(request=request)  # type: ignore
        if hasattr(maybe_user, "__await__"):
            maybe_user = await maybe_user  # type: ignore
        return maybe_user
    except FastAPIHTTPException:
        return None
    except Exception:  # pragma: no cover
        # NOTA: Captura amplia intencional. Endpoint bootstrap debe poder llamarse
        # incluso con errores inesperados de autenticación (DB no disponible, token
        # malformado, etc.). Devolver None permite continuar sin autenticación.
        return None


__all__ = [
    "require_reason",
    "require_reason_optional",
    "get_current_user_optional",
]
