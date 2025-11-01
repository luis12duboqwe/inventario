"""Utilidades para trabajar con claves de idempotencia corporativas."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import blake2b
from typing import Any, Iterable, Mapping, Sequence

IDEMPOTENCY_HEADER = "X-Idempotency-Key"
MAX_IDEMPOTENCY_KEY_LENGTH = 120


class IdempotencyKeyError(ValueError):
    """Error de validación al procesar una clave de idempotencia."""


@dataclass(slots=True)
class IdempotencyKey:
    """Representa una clave de idempotencia normalizada."""

    value: str
    generated: bool = False

    def __str__(self) -> str:  # pragma: no cover - representación sencilla
        return self.value


def _normalize_raw_value(raw: str) -> str:
    normalized = raw.strip()
    if not normalized:
        msg = "El encabezado X-Idempotency-Key no puede estar vacío."
        raise IdempotencyKeyError(msg)
    if len(normalized) > MAX_IDEMPOTENCY_KEY_LENGTH:
        msg = "El encabezado X-Idempotency-Key no puede exceder 120 caracteres."
        raise IdempotencyKeyError(msg)
    return normalized


def normalize_key(raw: str | None) -> IdempotencyKey | None:
    """Normaliza una clave proporcionada por el cliente."""

    if raw is None:
        return None
    return IdempotencyKey(value=_normalize_raw_value(raw), generated=False)


def _serialize_part(part: Any) -> str:
    if part is None:
        return "null"
    if isinstance(part, (str, int, float, bool)):
        return json.dumps(part, ensure_ascii=False, separators=(",", ":"))
    if isinstance(part, (Sequence, set, frozenset)) and not isinstance(part, (str, bytes, bytearray)):
        return json.dumps(sorted([_serialize_part(item) for item in part]), ensure_ascii=False)
    if isinstance(part, Mapping):
        normalized = {str(key): _serialize_part(value) for key, value in part.items()}
        return json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    return json.dumps(str(part), ensure_ascii=False)


def generate_from_parts(*parts: Any) -> IdempotencyKey:
    """Genera una clave determinística a partir de partes relevantes."""

    serialized = "|".join(_serialize_part(part) for part in parts)
    digest = blake2b(serialized.encode("utf-8"), digest_size=16).hexdigest()
    return IdempotencyKey(value=digest, generated=True)


def ensure_key(value: str | None, *parts: Any) -> IdempotencyKey:
    """Devuelve una clave válida, generándola si es necesario."""

    key = normalize_key(value)
    if key is not None:
        return key
    if not parts:
        msg = "No se proporcionó X-Idempotency-Key y no hay datos para generarla."
        raise IdempotencyKeyError(msg)
    return generate_from_parts(*parts)


def timestamp() -> str:
    """Devuelve una marca de tiempo ISO 8601 con zona UTC."""

    return datetime.now(tz=timezone.utc).isoformat()


def fingerprint_payload(payload: Mapping[str, Any]) -> str:
    """Genera una huella determinística de un payload JSON."""

    normalized = json.dumps(payload, sort_keys=True, separators=",")
    return blake2b(normalized.encode("utf-8"), digest_size=16).hexdigest()


def combine_keys(keys: Iterable[str]) -> str:
    """Permite combinar múltiples claves para auditorías o registros."""

    chain = "|".join(sorted({_normalize_raw_value(key) for key in keys}))
    return blake2b(chain.encode("utf-8"), digest_size=16).hexdigest()
