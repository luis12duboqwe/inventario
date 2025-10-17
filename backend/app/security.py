"""Utilidades de seguridad y autenticación para la API."""
from __future__ import annotations

from datetime import datetime, timedelta
import uuid

import jwt
import pyotp
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import crud, schemas
from .core.roles import ADMIN
from .config import settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(*, subject: str, expires_minutes: int | None = None) -> tuple[str, str]:
    expire_minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    session_id = uuid.uuid4().hex
    payload = {"sub": subject, "exp": int(expire.timestamp()), "jti": session_id}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, session_id


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
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    token_payload = decode_token(token)
    session = crud.get_active_session_by_token(db, token_payload.jti)
    if session is None or session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o revocada.")
    user = crud.get_user_by_username(db, token_payload.sub)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")
    crud.mark_session_used(db, token_payload.jti)
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
