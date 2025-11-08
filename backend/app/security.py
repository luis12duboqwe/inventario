"""Utilidades de seguridad y autenticación para la API."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
import types
import uuid
from typing import Any, Mapping

import jwt
import pyotp
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
import bcrypt
from sqlalchemy.orm import Session

from . import crud, schemas
from .core.roles import ADMIN
from .config import settings
from .database import get_db

logger = logging.getLogger(__name__)

try:  # pragma: no cover - import defensivo
    from fastapi_limiter import FastAPILimiter  # type: ignore
    from fastapi_limiter.depends import RateLimiter as _RateLimiter  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - degradación controlada
    FastAPILimiter = None  # type: ignore[assignment]
    _RateLimiter = None  # type: ignore[assignment]
    FakeRedis = None  # type: ignore[assignment]
else:  # pragma: no cover - import defensivo
    try:
        from fakeredis.aioredis import FakeRedis  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover - fakeredis opcional
        FakeRedis = None  # type: ignore[assignment]


def _is_stub_rate_limiter() -> bool:
    """Detecta si se está utilizando la implementación stub del limitador."""

    if FastAPILimiter is None:
        return False
    doc = getattr(FastAPILimiter, "__doc__", "") or ""
    return "Stub compatible" in doc and "pruebas" in doc.lower()


class _MemoryLimiterRedis:
    """Almacén mínimo en memoria para satisfacer la interfaz del stub."""

    async def close(self) -> None:  # pragma: no cover - comportamiento trivial
        return None


if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = types.SimpleNamespace(__version__=bcrypt.__version__)

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt_sha256", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
ALGORITHM = "HS256"

_rate_limiter_configured = False
_use_rate_limiter_stub = False

_BASE_ANONYMOUS_PATHS = {
    "/",
    "/health",
    "/auth/bootstrap",
    "/auth/bootstrap/status",
    "/auth/token",
    "/auth/session",
    "/auth/verify",
    "/auth/password/request",
    "/auth/password/reset",
    "/auth/register",
    "/auth/login",
    "/auth/refresh",
    "/auth/forgot",
    "/auth/reset",
}


def _build_anonymous_paths() -> frozenset[str]:
    paths = set(_BASE_ANONYMOUS_PATHS)

    def _normalize(prefix: str) -> str | None:
        cleaned = prefix.strip()
        if not cleaned or cleaned == "/":
            return None
        return cleaned if cleaned.startswith("/") else f"/{cleaned}"

    main_prefix = _normalize(settings.api_v1_prefix)
    if main_prefix:
        paths.add(f"{main_prefix}/health")

    for alias in settings.api_alias_prefixes:
        alias_prefix = _normalize(alias)
        if alias_prefix:
            paths.add(f"{alias_prefix}/health")

    return frozenset(paths)


_ANONYMOUS_PATHS = _build_anonymous_paths()


class _RateLimiterStub:  # pragma: no cover - comportamiento trivial
    """Satisface la interfaz esperada cuando el limitador no está disponible."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - interfaz FastAPI
        self.args = args
        self.kwargs = kwargs

    async def __call__(self, _request: Request) -> None:
        return None


def rate_limit(*, times: int, minutes: int) -> Any:
    """Devuelve una dependencia de limitación de peticiones.

    Cuando fastapi-limiter no está disponible, se devuelve un stub inofensivo que
    mantiene la firma esperada por FastAPI sin aplicar restricciones reales.
    """

    if _RateLimiter is None or _use_rate_limiter_stub:
        return _RateLimiterStub(times=times, minutes=minutes)
    return _RateLimiter(times=times, minutes=minutes)


def _default_rate_limit_identifier(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded
    client = request.client
    if client and client.host:
        return client.host
    return "anonymous"


async def ensure_rate_limiter(
    identifier: Callable[[Request], str | Awaitable[str]] | None = None,
) -> None:
    """Inicializa el limitador de ritmo con Redis en memoria cuando es posible."""

    global _rate_limiter_configured, _use_rate_limiter_stub
    if _rate_limiter_configured:
        if identifier and FastAPILimiter is not None:
            FastAPILimiter.identifier = identifier
        return

    if FastAPILimiter is None:
        logger.warning(
            "fastapi-limiter no disponible; las rutas funcionarán sin límite de peticiones",
        )
        _use_rate_limiter_stub = True
        _rate_limiter_configured = True
        return

    if getattr(FastAPILimiter, "redis", None) is None:
        redis_instance: Any | None = None
        if FakeRedis is not None:
            redis_instance = FakeRedis()
        elif _is_stub_rate_limiter():
            redis_instance = _MemoryLimiterRedis()
        if redis_instance is None:
            logger.warning(
                "fakeredis no está instalado; no se aplicará limitación de peticiones en memoria",
            )
            FastAPILimiter.redis = _MemoryLimiterRedis()
            _use_rate_limiter_stub = True
            _rate_limiter_configured = True
            if identifier is not None:
                FastAPILimiter.identifier = identifier
            elif getattr(FastAPILimiter, "identifier", None) is None:
                FastAPILimiter.identifier = _default_rate_limit_identifier
            return
        await FastAPILimiter.init(redis_instance)
        _use_rate_limiter_stub = False

    if identifier is not None:
        FastAPILimiter.identifier = identifier
    elif getattr(FastAPILimiter, "identifier", None) is None:
        FastAPILimiter.identifier = _default_rate_limit_identifier

    _rate_limiter_configured = True


async def reset_rate_limiter() -> None:
    """Libera los recursos asociados al limitador de ritmo."""

    global _rate_limiter_configured, _use_rate_limiter_stub
    if FastAPILimiter is None:
        _rate_limiter_configured = False
        _use_rate_limiter_stub = False
        return

    close = getattr(FastAPILimiter, "close", None)
    if close is not None:
        await close()
    else:  # pragma: no cover - degradación defensiva
        FastAPILimiter.redis = None  # type: ignore[attr-defined]
    FastAPILimiter.identifier = None
    _rate_limiter_configured = False
    _use_rate_limiter_stub = False


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


# // [PACK28-tokens]
def _build_token_payload(
    *,
    subject: str,
    session_token: str,
    expires_at: datetime,
    issued_at: datetime,
    token_type: str,
    extra_claims: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": int(expires_at.timestamp()),
        "iat": int(issued_at.timestamp()),
        "jti": session_token,
        "token_type": token_type,
    }
    if token_type == "access":  # // [PACK28-tokens]
        payload["nonce"] = uuid.uuid4().hex
    if extra_claims:
        payload.update({key: value for key, value in extra_claims.items() if value is not None})
    return payload


# // [PACK28-tokens]
def create_access_token(
    *,
    subject: str,
    expires_minutes: int | None = None,
    session_token: str | None = None,
    claims: Mapping[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    expire_minutes = expires_minutes or settings.access_token_expire_minutes
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=expire_minutes)
    session_id = session_token or uuid.uuid4().hex
    payload = _build_token_payload(
        subject=subject,
        session_token=session_id,
        expires_at=expires_at,
        issued_at=issued_at,
        token_type="access",
        extra_claims=claims,
    )
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, session_id, expires_at


# // [PACK28-tokens]
def create_refresh_token(
    *,
    subject: str,
    session_token: str,
    expires_days: int | None = None,
    claims: Mapping[str, Any] | None = None,
) -> tuple[str, datetime]:
    expire_days = expires_days or settings.refresh_token_expire_days
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(days=expire_days)
    refresh_payload = _build_token_payload(
        subject=subject,
        session_token=uuid.uuid4().hex,
        expires_at=expires_at,
        issued_at=issued_at,
        token_type="refresh",
        extra_claims={"sid": session_token, **(claims or {})},
    )
    token = jwt.encode(refresh_payload, settings.secret_key, algorithm=ALGORITHM)
    return token, expires_at


def decode_token(token: str) -> schemas.TokenPayload:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if "jti" not in payload:
            raise jwt.PyJWTError("missing jti")
        if "exp" not in payload:
            raise jwt.PyJWTError("missing exp")
        if "iat" not in payload:
            raise jwt.PyJWTError("missing iat")
        return schemas.TokenPayload(**payload)
    except jwt.ExpiredSignatureError as exc:  # pragma: no cover - error path
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado.",
        ) from exc
    except jwt.PyJWTError as exc:  # pragma: no cover - error path
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        ) from exc


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    normalized_path = request.url.path.rstrip("/") or "/"
    has_session_cookie = bool(request.cookies.get(settings.session_cookie_name))
    if token is None and not has_session_cookie and normalized_path in _ANONYMOUS_PATHS:
        return None

    session_token: str | None = None
    if token:
        token_payload = decode_token(token)
        if token_payload.token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tipo de token inválido.",
            )
        session_token = token_payload.jti
        session = crud.get_active_session_by_token(db, session_token)
        if session is None or session.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión inválida o revocada.",
            )
        if crud.is_session_expired(session.expires_at):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión expirada.",
            )
        user = crud.get_user_by_username(db, token_payload.sub)
    else:
        session_token = request.cookies.get(settings.session_cookie_name)
        if not session_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticación requerida.",
            )
        session = crud.get_active_session_by_token(db, session_token)
        if session is None or session.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión inválida o revocada.",
            )
        if crud.is_session_expired(session.expires_at):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión expirada.",
            )
        user = session.user
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")
    if session_token:
        crud.mark_session_used(db, session_token)
    return user


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def require_roles(*roles: str):
    async def dependency(current_user=Depends(get_current_user)):
        user_roles = {assignment.role.name for assignment in current_user.roles}
        if ADMIN in user_roles:
            return current_user
        if roles and user_roles.isdisjoint(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No cuenta con permisos para realizar esta acción.",
            )
        return current_user

    return dependency


async def require_active_user(current_user=Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")
    return current_user
