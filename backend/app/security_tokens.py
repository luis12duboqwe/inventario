"""Protección de tokens sensibles en repositorios persistentes."""

from __future__ import annotations

import hashlib
import hmac

from .config import settings


def _secret_key_bytes() -> bytes:
    return settings.secret_key.encode("utf-8")


def protect_token(token: str) -> str:
    """Devuelve una representación HMAC segura del token."""

    digest = hmac.new(_secret_key_bytes(), token.encode("utf-8"), hashlib.sha256)
    return f"sha256:{digest.hexdigest()}"


def matches_token(stored_value: str, candidate: str) -> bool:
    """Compara un token candidato contra su versión protegida o legada."""

    if stored_value.startswith("sha256:"):
        candidate_hash = protect_token(candidate).removeprefix("sha256:")
        return hmac.compare_digest(stored_value.removeprefix("sha256:"), candidate_hash)
    return hmac.compare_digest(stored_value, candidate)
