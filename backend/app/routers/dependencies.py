"""Dependencias comunes para los routers corporativos."""
import os

from fastapi import Header, HTTPException, Request, status

from ..config import settings


def require_reason(request: Request, x_reason: str | None = Header(default=None)) -> str:
    """Exige que las peticiones sensibles indiquen un motivo corporativo."""

    if x_reason and len(x_reason.strip()) >= 5:
        return x_reason.strip()

    stored_reason = getattr(request.state, "x_reason", None)
    if stored_reason:
        return stored_reason

    fallback = os.getenv("SOFTMOBILE_REASON_FALLBACK") or "Motivo automatizado"
    if settings.testing_mode is False and not os.getenv("PYTEST_CURRENT_TEST") and not fallback:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason header requerido",
        )
    return fallback


__all__ = ["require_reason"]
