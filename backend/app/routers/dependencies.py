"""Dependencias comunes para los routers corporativos."""

from fastapi import Header, HTTPException, Request, status

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


__all__ = ["require_reason", "require_reason_optional"]
