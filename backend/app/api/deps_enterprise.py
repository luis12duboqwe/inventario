"""Dependencias avanzadas para los módulos corporativos de Softmobile."""
from __future__ import annotations

from typing import Any, Iterable

from fastapi import Depends, Header, HTTPException, status

from ..config import settings
from ..utils.idempotency import (
    IDEMPOTENCY_HEADER,
    IdempotencyKey,
    IdempotencyKeyError,
    combine_keys,
    ensure_key,
    normalize_key,
)

_MIN_REASON_LENGTH = 5


def _sanitize_reason(value: str | None, required: bool) -> str | None:
    if value is None:
        if required:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Proporciona el encabezado X-Reason con al menos 5 caracteres.",
            )
        return None
    normalized = value.strip()
    if len(normalized) < _MIN_REASON_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El encabezado X-Reason debe contener al menos 5 caracteres significativos.",
        )
    return normalized


async def require_reason(x_reason: str | None = Header(default=None, alias="X-Reason")) -> str:
    """Exige un motivo corporativo válido."""

    sanitized = _sanitize_reason(x_reason, required=True)
    assert sanitized is not None
    return sanitized


async def optional_reason(x_reason: str | None = Header(default=None, alias="X-Reason")) -> str | None:
    """Permite motivos opcionales siempre que cumplan la longitud mínima."""

    return _sanitize_reason(x_reason, required=False)


def _normalize_idempotency(value: str | None, *, required: bool) -> IdempotencyKey | None:
    try:
        key = normalize_key(value)
    except IdempotencyKeyError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if key is None and required:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Define X-Idempotency-Key para evitar operaciones duplicadas.",
        )
    return key


async def optional_idempotency_key(
    header: str | None = Header(default=None, alias=IDEMPOTENCY_HEADER),
) -> IdempotencyKey | None:
    """Devuelve la clave de idempotencia enviada por el cliente, si existe."""

    return _normalize_idempotency(header, required=False)


async def require_idempotency_key(
    header: str | None = Header(default=None, alias=IDEMPOTENCY_HEADER),
) -> IdempotencyKey:
    """Obliga a utilizar idempotencia para operaciones críticas."""

    key = _normalize_idempotency(header, required=True)
    assert key is not None
    return key


def ensure_idempotency(parts: Iterable[Any], key: IdempotencyKey | None) -> IdempotencyKey:
    """Garantiza la existencia de una clave de idempotencia para el payload dado."""

    try:
        return ensure_key(None if key is None else key.value, *parts)
    except IdempotencyKeyError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


async def require_hybrid_mode() -> bool:
    """Valida que el modo híbrido se encuentre habilitado."""

    if not settings.enable_hybrid_prep:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El modo híbrido está deshabilitado para esta instalación.",
        )
    return True


async def require_catalog_pro() -> bool:
    """Valida que el catálogo profesional esté activo."""

    if not settings.enable_catalog_pro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El catálogo profesional se encuentra deshabilitado en esta instancia.",
        )
    return True


async def require_transfers_enabled() -> bool:
    """Valida que las transferencias estén activas."""

    if not settings.enable_transfers:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Las transferencias entre tiendas están deshabilitadas para esta instalación.",
        )
    return True


def merge_idempotency_keys(keys: Iterable[IdempotencyKey | str]) -> str:
    """Combina múltiples claves para auditoría o seguimiento."""

    raw_values = [key.value if isinstance(key, IdempotencyKey) else key for key in keys]
    return combine_keys(raw_values)


IdempotencyDependency = Depends(optional_idempotency_key)
ReasonDependency = Depends(require_reason)
