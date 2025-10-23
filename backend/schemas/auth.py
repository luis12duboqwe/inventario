"""Esquemas Pydantic para las operaciones de autenticación."""
from __future__ import annotations

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)


_email_adapter = TypeAdapter(EmailStr)


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

    email: EmailStr | None = None
    password: str = Field(
        min_length=6,
        max_length=128,
        description="Contraseña en texto plano que será hasheada con bcrypt.",
    )
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
        description="Opcional. Si no se especifica, se reutiliza el correo.",
    )

    @field_validator("username", mode="before")
    @classmethod
    def _strip_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

    @model_validator(mode="after")
    def _ensure_email(cls, model: "RegisterRequest") -> "RegisterRequest":
        email_source = model.email or model.username
        if email_source is None:
            raise ValueError(
                "Debe proporcionar un correo electrónico o un nombre de usuario válido."
            )
        normalized_email = str(email_source).strip()
        if not normalized_email:
            raise ValueError(
                "Debe proporcionar un correo electrónico o un nombre de usuario válido."
            )
        try:
            validated_email = _email_adapter.validate_python(normalized_email)
        except ValueError as exc:
            raise ValueError("Debe proporcionar un correo electrónico válido.") from exc
        model.email = validated_email
        if model.username is None:
            model.username = str(validated_email)
        return model


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
