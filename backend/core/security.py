"""Herramientas de seguridad para la autenticación basada en JWT."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Final

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, Field

SECRET_KEY: Final[str] = os.getenv(
    "SOFTMOBILE_SECRET_KEY",
    "softmobile-dev-secret-key-please-change",
)
ALGORITHM: Final[str] = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = int(
    os.getenv("SOFTMOBILE_ACCESS_TOKEN_EXPIRE", "60")
)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload(BaseModel):
    """Representa la carga útil de un token JWT emitido por el backend."""

    sub: str = Field(..., description="Identificador único del usuario autenticado")
    exp: int = Field(..., description="Marca de tiempo de expiración en segundos desde epoch")

    @property
    def expires_at(self) -> datetime:
        """Convierte el timestamp de expiración en un objeto ``datetime``."""

        return datetime.fromtimestamp(self.exp, tz=timezone.utc)


def get_password_hash(password: str) -> str:
    """Devuelve el hash seguro para la contraseña indicada."""

    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Comprueba que la contraseña sin cifrar coincida con el hash almacenado."""

    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(*, subject: str, expires_minutes: int | None = None) -> str:
    """Genera un token JWT firmado que identifica al usuario ``subject``."""

    expires_delta = timedelta(
        minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    )
    expire_at = datetime.now(tz=timezone.utc) + expires_delta
    payload = {"sub": subject, "exp": int(expire_at.timestamp())}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenPayload:
    """Valida y decodifica el token recibido devolviendo su carga útil."""

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:  # pragma: no cover - error específico
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha expirado.",
        ) from exc
    except jwt.PyJWTError as exc:  # pragma: no cover - error específico
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        ) from exc

    return TokenPayload.model_validate(payload)


__all__ = [
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "ALGORITHM",
    "SECRET_KEY",
    "TokenPayload",
    "create_access_token",
    "decode_access_token",
    "get_password_hash",
    "verify_password",
]
