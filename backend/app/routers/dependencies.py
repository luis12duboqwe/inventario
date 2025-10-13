"""Dependencias comunes para los routers corporativos."""
from fastapi import Header, HTTPException, status


def require_reason(x_reason: str | None = Header(default=None)) -> str:
    """Exige que las peticiones sensibles indiquen un motivo corporativo."""

    if not x_reason or len(x_reason.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason header requerido",
        )
    return x_reason.strip()


__all__ = ["require_reason"]
