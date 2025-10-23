from __future__ import annotations

"""Herramientas de seguridad y autenticación basadas en JWT."""

from datetime import datetime, timedelta, timezone
from typing import Final

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from backend.core.settings import settings
from backend.db import get_db, get_user_by_id
from backend.models.user import User


class TokenPayload(BaseModel):
    """Representa la carga útil de un token JWT emitido por el backend."""

    sub: str = Field(..., description="Identificador único del usuario autenticado")
    exp: int = Field(..., description="Marca de expiración expresada como timestamp")
    token_type: str = Field(
        default="access",
        description="Permite distinguir entre tokens de acceso, refresco y otros.",
    )

    @property
    def expires_at(self) -> datetime:
        """Devuelve el momento exacto de expiración como ``datetime`` UTC."""

        return datetime.fromtimestamp(self.exp, tz=timezone.utc)


SECRET_KEY: Final[str] = settings.SECRET_KEY
ALGORITHM: Final[str] = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = settings.REFRESH_TOKEN_EXPIRE_DAYS

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def _create_token(*, subject: str, expires_delta: timedelta, token_type: str) -> str:
    expire_at = datetime.now(tz=timezone.utc) + expires_delta
    payload = {"sub": subject, "exp": int(expire_at.timestamp()), "token_type": token_type}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_password_hash(password: str) -> str:
    """Devuelve el hash seguro para la contraseña indicada."""

    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Comprueba que la contraseña sin cifrar coincida con el hash almacenado."""

    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    *, subject: str, expires_minutes: int | None = None, token_type: str = "access"
) -> str:
    """Genera un token JWT firmado que identifica al usuario ``subject``."""

    expires_delta = timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(subject=subject, expires_delta=expires_delta, token_type=token_type)


def create_refresh_token(
    *, subject: str, expires_days: int | None = None, token_type: str = "refresh"
) -> str:
    """Genera un token JWT de larga duración para renovar sesiones."""

    expires_delta = timedelta(days=expires_days or REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(subject=subject, expires_delta=expires_delta, token_type=token_type)


def decode_token(token: str, *, expected_type: str | None = None) -> TokenPayload:
    """Valida y decodifica el token recibido devolviendo su carga útil."""

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    token_payload = TokenPayload.model_validate(payload)
    if expected_type and token_payload.token_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token no permitido para esta operación.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_payload


def decode_access_token(token: str) -> TokenPayload:
    """Atajo que valida específicamente tokens de acceso."""

    return decode_token(token, expected_type="access")


def verify_token_expiry(token_payload: TokenPayload) -> None:
    """Lanza un error si el token ya venció."""

    if token_payload.expires_at <= datetime.now(tz=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    db=Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """Obtiene al usuario autenticado a partir del token JWT recibido."""

    payload = decode_access_token(token)
    verify_token_expiry(payload)
    try:
        user_id = int(payload.sub)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token asociado a un usuario inexistente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


__all__ = [
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "ALGORITHM",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    "SECRET_KEY",
    "TokenPayload",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_token",
    "get_current_user",
    "get_password_hash",
    "oauth2_scheme",
    "verify_password",
    "verify_token_expiry",
]
