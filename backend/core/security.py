from __future__ import annotations

"""Herramientas de seguridad y autenticación basadas en JWT."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import Session

from backend.db import get_db, get_user_by_id


class _SecuritySettings(BaseSettings):
    """Carga parámetros criptográficos definidos en ``backend/.env``."""

    secret_key: str = Field(
        default="cambia-este-valor",
        description="Clave secreta usada para firmar los tokens JWT",
    )
    access_token_expire_minutes: int = Field(
        default=60, description="Minutos de vigencia para cada token de acceso"
    )
    algorithm: str = Field(default="HS256", description="Algoritmo JWT a emplear")

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="allow",
    )


_settings = _SecuritySettings()

SECRET_KEY: Final[str] = _settings.secret_key
ALGORITHM: Final[str] = _settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = _settings.access_token_expire_minutes

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class TokenPayload(BaseModel):
    """Representa la carga útil de un token JWT emitido por el backend."""

    sub: str = Field(..., description="Identificador único del usuario autenticado")
    exp: int = Field(..., description="Marca de expiración expresada como timestamp")

    @property
    def expires_at(self) -> datetime:
        """Devuelve el momento exacto de expiración como ``datetime`` UTC."""

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
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenPayload.model_validate(payload)


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    """Obtiene al usuario autenticado a partir del token JWT recibido."""

    payload = decode_access_token(token)
    user = get_user_by_id(db, int(payload.sub))
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
    "SECRET_KEY",
    "TokenPayload",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "get_password_hash",
    "oauth2_scheme",
    "verify_password",
]
