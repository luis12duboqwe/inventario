"""Utilidades de seguridad y autenticación para la API."""
from __future__ import annotations

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

if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = types.SimpleNamespace(__version__=bcrypt.__version__)

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt_sha256", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
ALGORITHM = "HS256"

_ANONYMOUS_PATHS = frozenset(
    {
        "/",
        "/health",
        "/api/v1/health",
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
)


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
