"""Utilidades de seguridad y autenticación para la API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
import uuid

import jwt
import pyotp
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import crud, schemas
from .core.roles import ADMIN
from .config import settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
ALGORITHM = "HS256"

_ANONYMOUS_PATHS = frozenset(
    {
        "/",
        "/health",
        "/api/v1/health",
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


def create_access_token(
    *, subject: str, expires_minutes: int | None = None
) -> tuple[str, str, datetime]:
    expire_minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    session_id = uuid.uuid4().hex
    payload = {"sub": subject, "exp": int(expire.timestamp()), "jti": session_id}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, session_id, expire


def decode_token(token: str) -> schemas.TokenPayload:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if "jti" not in payload:
            raise jwt.PyJWTError("missing jti")
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
    if normalized_path.startswith("/auth/bootstrap"):
        bootstrap_token = settings.bootstrap_token
        if bootstrap_token:
            provided_token = request.headers.get("X-Bootstrap-Token", "")
            if not secrets.compare_digest(provided_token, bootstrap_token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token de arranque inválido.",
                )
        return None
    has_session_cookie = bool(request.cookies.get(settings.session_cookie_name))
    if token is None and not has_session_cookie and normalized_path in _ANONYMOUS_PATHS:
        return None

    session_token: str | None = None
    if token:
        token_payload = decode_token(token)
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
