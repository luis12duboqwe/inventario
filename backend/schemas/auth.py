"""Esquemas Pydantic para las operaciones de autenticación."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRead(BaseModel):
    """Datos públicos que se exponen para los usuarios autenticados."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    is_active: bool
    created_at: datetime


class RegisterRequest(BaseModel):
    """Carga útil necesaria para registrar un nuevo usuario."""

    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Contraseña en texto plano que será hasheada con bcrypt.",
    )
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
        description="Opcional. Si no se especifica, se reutiliza el correo.",
    )


class RegisterResponse(UserRead):
    """Respuesta devuelta tras registrar un nuevo usuario."""

    message: str


class TokenResponse(BaseModel):
    """Representa el token generado tras un inicio de sesión correcto."""

    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Permite compatibilidad con clientes que envían JSON en lugar de formularios."""

    username: str
    password: str


class AuthMessage(BaseModel):
    """Modelo genérico para respuestas informativas de autenticación."""

    message: str


__all__ = [
    "AuthMessage",
    "LoginRequest",
    "RegisterRequest",
    "RegisterResponse",
    "TokenResponse",
    "UserRead",
]
