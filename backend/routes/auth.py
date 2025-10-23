from __future__ import annotations

"""Rutas de autenticación para Softmobile 2025."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.core.security import (
    create_access_token,
    decode_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from backend.db import create_user, get_db, get_user_by_email, get_user_by_id, init_db
from backend.models import User
from backend.schemas.auth import (
    AuthMessage,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserRead,
)

REGISTER_SUCCESS_MESSAGE = "Usuario registrado correctamente."

router = APIRouter(prefix="/auth", tags=["auth"])
_auth_scheme = HTTPBearer(auto_error=False)

# Garantizamos que las tablas estén listas al cargar el módulo.
init_db()


class BootstrapStatusResponse(AuthMessage):
    """Expone el estado del proceso de bootstrap del sistema."""

    disponible: bool
    usuarios_registrados: int


class BootstrapRequest(RegisterRequest):
    """Datos mínimos para crear la cuenta inicial del sistema."""

    full_name: str | None = None


class VerificationResponse(AuthMessage):
    """Confirma la validez del token y devuelve el usuario asociado."""

    valid: bool
    user: UserRead | None = None


async def _login_form_or_json(request: Request) -> LoginRequest:
    """Permite recibir credenciales via formulario OAuth2 o JSON."""

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        return LoginRequest(**payload)

    form = await request.form()
    form_data = OAuth2PasswordRequestForm(
        grant_type=form.get("grant_type"),
        username=str(form.get("username") or form.get("email") or "").strip(),
        password=str(form.get("password") or ""),
        scope=form.get("scope") or "",
        client_id=form.get("client_id"),
        client_secret=form.get("client_secret"),
    )
    if not form_data.username or not form_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar nombre de usuario y contraseña.",
        )
    return LoginRequest(username=form_data.username, password=form_data.password)


def _normalize_identifier(value: str) -> str:
    return value.strip().lower()


def _get_user_by_identifier(db: Session, identifier: str) -> User | None:
    normalized = _normalize_identifier(identifier)
    return (
        db.query(User)
        .filter(
            or_(
                func.lower(User.username) == normalized,
                func.lower(User.email) == normalized,
            )
        )
        .first()
    )


def _issue_token(user: User) -> TokenResponse:
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/status", response_model=AuthMessage)
async def get_auth_status() -> AuthMessage:
    """Indica si el módulo de autenticación se encuentra operativo."""

    return AuthMessage(message="Autenticación lista y conectada a SQLite ✅")


@router.get("/bootstrap/status", response_model=BootstrapStatusResponse)
def read_bootstrap_status(db: Session = Depends(get_db)) -> BootstrapStatusResponse:
    """Devuelve si aún es posible registrar la cuenta inicial del sistema."""

    total_users = db.query(func.count(User.id)).scalar() or 0
    return BootstrapStatusResponse(
        message="Estado de bootstrap consultado correctamente.",
        disponible=total_users == 0,
        usuarios_registrados=int(total_users),
    )


@router.post("/bootstrap", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_user(payload: BootstrapRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """Crea el usuario inicial siempre que no existan registros previos."""

    total_users = db.query(func.count(User.id)).scalar() or 0
    if total_users > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El sistema ya cuenta con usuarios registrados.",
        )

    email_value = str(payload.email)
    username = payload.username or email_value

    existing_user = _get_user_by_identifier(db, username) or get_user_by_email(db, email_value)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario inicial ya fue configurado previamente.",
        )

    hashed = get_password_hash(payload.password)
    user = create_user(db, email=email_value, hashed_password=hashed, username=username)
    user_read = UserRead.model_validate(user)
    return RegisterResponse(
        message="Usuario inicial creado correctamente.",
        **user_read.model_dump(),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_200_OK)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """Crea un nuevo usuario siempre que el correo o usuario no existan."""

    email_value = str(payload.email)
    username_value = payload.username or email_value
    normalized_username = _normalize_identifier(username_value)
    normalized_email = _normalize_identifier(email_value)

    existing_user = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.username) == normalized_username,
                func.lower(User.email) == normalized_email,
            )
        )
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario o correo ya están registrados.",
        )

    hashed = get_password_hash(payload.password)
    user = create_user(
        db,
        email=normalized_email,
        hashed_password=hashed,
        username=normalized_username,
    )
    user_read = UserRead.model_validate(user)
    return RegisterResponse(
        message=REGISTER_SUCCESS_MESSAGE,
        **user_read.model_dump(),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest = Depends(_login_form_or_json),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Valida las credenciales del usuario y emite un token JWT."""

    user = _get_user_by_identifier(db, credentials.username)
    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo.",
        )

    return _issue_token(user)


@router.post("/token", response_model=TokenResponse)
async def login_legacy(
    credentials: LoginRequest = Depends(_login_form_or_json),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Alias de compatibilidad para clientes que aún usan ``/auth/token``."""

    return await login(credentials, db)


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> UserRead:
    """Devuelve la información del usuario autenticado."""

    return UserRead.model_validate(current_user)


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
    user = get_user_by_id(db, int(payload.sub))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token asociado a un usuario inexistente.",
        )

    return VerificationResponse(
        message="Token verificado correctamente.",
        valid=True,
        user=UserRead.model_validate(user),
    )


__all__ = ["router"]
