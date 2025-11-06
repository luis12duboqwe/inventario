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
    is_verified: bool
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
    def _ensure_email(self) -> "RegisterRequest":
        email_source = self.email or self.username
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
            raise ValueError(
                "Debe proporcionar un correo electrónico válido.") from exc
        self.email = validated_email
        if self.username is None:
            self.username = str(validated_email)
        return self


class RegisterResponse(UserRead):
    """Respuesta devuelta tras registrar un nuevo usuario."""

    message: str
    verification_token: str | None = Field(
        default=None,
        description="Token temporal para verificar el correo electrónico.",
    )


class TokenPairResponse(BaseModel):
    """Devuelve el par de tokens emitidos tras autenticar o refrescar."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Solicitud para obtener un nuevo par de tokens usando el refresh."""

    refresh_token: str


class LoginRequest(BaseModel):
    """Permite compatibilidad con clientes que envían JSON en lugar de formularios."""

    username: str
    password: str


class AuthMessage(BaseModel):
    """Modelo genérico para respuestas informativas de autenticación."""

    message: str


class ForgotPasswordRequest(BaseModel):
    """Modelo para solicitar el restablecimiento de contraseña."""

    email: EmailStr


class ForgotPasswordResponse(AuthMessage):
    """Confirma la solicitud de restablecimiento e incluye el token generado."""

    reset_token: str | None = Field(
        default=None,
        description="Token temporal retornado para entornos de prueba.",
    )


class ResetPasswordRequest(BaseModel):
    """Datos necesarios para definir una nueva contraseña."""

    token: str = Field(..., description="Token temporal de restablecimiento")
    new_password: str = Field(
        ..., min_length=6, max_length=128, description="Nueva contraseña segura"
    )


class VerifyEmailRequest(BaseModel):
    """Carga útil para confirmar la verificación de correo."""

    token: str = Field(...,
                       description="Token temporal de verificación de correo")


__all__ = [
    "AuthMessage",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "LoginRequest",
    "RefreshTokenRequest",
    "RegisterRequest",
    "RegisterResponse",
    "ResetPasswordRequest",
    "TokenPairResponse",
    "UserRead",
    "VerifyEmailRequest",
]
