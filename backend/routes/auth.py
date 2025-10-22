"""Rutas de autenticación con persistencia en SQLite y JWT."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from backend.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from backend.database import get_db, init_db
from backend.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
_auth_scheme = HTTPBearer(auto_error=False)

# Garantizamos que las tablas estén listas al cargar el módulo.
init_db()


class AuthStatusResponse(BaseModel):
    """Respuesta simple para verificar el estado del módulo de autenticación."""

    message: str


class RegisterRequest(BaseModel):
    """Datos necesarios para crear un nuevo usuario autenticable."""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Correo electrónico inválido.")
        return normalized


class BootstrapStatusResponse(BaseModel):
    """Expone el estado del proceso de bootstrap del sistema."""

    disponible: bool
    usuarios_registrados: int


class BootstrapRequest(BaseModel):
    """Datos mínimos para crear la cuenta inicial del sistema."""

    model_config = ConfigDict(extra="ignore")

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Correo electrónico inválido.")
        return normalized


class UserResponse(BaseModel):
    """Información pública del usuario que se devolverá en las respuestas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    """Credenciales que el usuario debe proporcionar para iniciar sesión."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """Representa el token generado tras un inicio de sesión correcto."""

    access_token: str
    token_type: str = "bearer"


class VerificationResponse(BaseModel):
    """Confirma la validez del token y devuelve el usuario asociado."""

    valid: bool
    user: UserResponse | None = None


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status() -> AuthStatusResponse:
    """Indica si el módulo de autenticación se encuentra operativo."""

    return AuthStatusResponse(message="Autenticación lista y conectada a SQLite ✅")


@router.get("/bootstrap/status", response_model=BootstrapStatusResponse)
def read_bootstrap_status(db: Session = Depends(get_db)) -> BootstrapStatusResponse:
    """Devuelve si aún es posible registrar la cuenta inicial del sistema."""

    total_users = db.query(func.count(User.id)).scalar() or 0
    return BootstrapStatusResponse(
        disponible=total_users == 0,
        usuarios_registrados=int(total_users),
    )


@router.post("/bootstrap", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_user(payload: BootstrapRequest, db: Session = Depends(get_db)) -> UserResponse:
    """Crea el usuario inicial siempre que no existan registros previos."""

    try:
        db.execute(text("BEGIN IMMEDIATE"))
    except OperationalError as exc:  # pragma: no cover - se mantiene por robustez
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible asegurar el bloqueo para el bootstrap inicial.",
        ) from exc

    try:
        total_users = db.query(func.count(User.id)).scalar() or 0
        if total_users > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El sistema ya cuenta con usuarios registrados.",
            )

        normalized_username = payload.username.strip()
        email_value = payload.email or (
            normalized_username
            if "@" in normalized_username
            else f"{normalized_username}@bootstrap.local"
        )
        existing_user = (
            db.query(User)
            .filter(or_(User.username == normalized_username, User.email == email_value))
            .first()
        )
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario inicial ya fue configurado previamente.",
            )

        user = User(
            username=normalized_username,
            email=email_value,
            hashed_password=get_password_hash(payload.password),
        )
        db.add(user)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario inicial ya fue configurado previamente.",
        ) from exc
    else:
        db.refresh(user)
        return UserResponse.model_validate(user)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    """Crea un nuevo usuario siempre que el correo o usuario no existan."""

    existing_user = (
        db.query(User)
        .filter(or_(User.username == payload.username, User.email == payload.email))
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario o correo ya están registrados.",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Valida las credenciales del usuario y emite un token JWT."""

    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo.",
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/verify", response_model=VerificationResponse)
def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_auth_scheme),
    db: Session = Depends(get_db),
) -> VerificationResponse:
    """Confirma que el token recibido pertenece a un usuario válido."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autorización requerida.",
        )

    payload = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == int(payload.sub)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token asociado a un usuario inexistente.",
        )

    return VerificationResponse(valid=True, user=UserResponse.model_validate(user))


__all__ = ["router"]
