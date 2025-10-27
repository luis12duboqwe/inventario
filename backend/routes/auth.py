from __future__ import annotations

"""Rutas de autenticación para Softmobile 2025."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm

try:  # pragma: no cover - validado mediante pruebas cuando la dependencia existe
    from fastapi_limiter import FastAPILimiter  # type: ignore
    from fastapi_limiter.depends import RateLimiter as _RateLimiter
except ModuleNotFoundError:  # pragma: no cover - se activa en entornos mínimos
    FastAPILimiter = None  # type: ignore[assignment]

    class _RateLimiterStub:  # pragma: no cover - comportamiento trivial
        async def __call__(self, request: object) -> None:  # noqa: D401 - interfaz FastAPI
            return None

    def RateLimiter(*args, **kwargs):  # type: ignore
        return _RateLimiterStub()

    FakeRedis = None  # type: ignore[assignment]
    _HAS_RATE_LIMITER = False
else:
    try:
        from fakeredis.aioredis import FakeRedis  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover - redis opcional
        FakeRedis = None  # type: ignore[assignment]
    RateLimiter = _RateLimiter  # type: ignore
    _HAS_RATE_LIMITER = True
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.app.core.transactions import flush_session, transactional_session
from backend.core.logging import logger as core_logger
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_token,
    get_current_user,
    get_password_hash,
    verify_password,
    verify_token_expiry,
)
from backend.core.settings import settings
from backend.db import create_user, get_db, get_user_by_email, get_user_by_id, init_db
from backend.models import User
from backend.schemas.auth import (
    AuthMessage,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenPairResponse,
    UserRead,
    VerifyEmailRequest,
)

REGISTER_SUCCESS_MESSAGE = "Usuario registrado correctamente."

LOGGER = core_logger.bind(component="backend.routes.auth")

PASSWORD_RESET_TOKEN_MINUTES = 30
EMAIL_VERIFICATION_TOKEN_MINUTES = 60 * 24

router = APIRouter(prefix="/auth", tags=["auth"])
_auth_scheme = HTTPBearer(auto_error=False)

# Garantizamos que las tablas estén listas al cargar el módulo.
init_db()


@router.on_event("startup")
async def _configure_rate_limiter() -> None:
    """Inicializa el limitador de peticiones usando Redis en memoria."""

    if not _HAS_RATE_LIMITER or FastAPILimiter is None or FakeRedis is None:
        LOGGER.warning(
            "fastapi-limiter no disponible; las rutas funcionarán sin limitación de ritmo",
        )
        return

    if getattr(FastAPILimiter, "redis", None) is not None:
        return
    redis = FakeRedis()
    await FastAPILimiter.init(redis)


def _generate_subject(user_id: int) -> str:
    return f"{user_id}:{secrets.token_urlsafe(24)}"


def _extract_user_id(raw_subject: str) -> int:
    candidate = str(raw_subject).split(":", 1)[0]
    try:
        return int(candidate)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
        ) from exc


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


def _issue_tokens(user: User) -> TokenPairResponse:
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=_generate_subject(user.id))
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


def _build_password_reset_token(user: User) -> str:
    return create_access_token(
        subject=_generate_subject(user.id),
        expires_minutes=PASSWORD_RESET_TOKEN_MINUTES,
        token_type="password_reset",
    )


def _build_verification_token(user: User) -> str:
    return create_access_token(
        subject=_generate_subject(user.id),
        expires_minutes=EMAIL_VERIFICATION_TOKEN_MINUTES,
        token_type="email_verification",
    )


@router.get(
    "/status",
    response_model=AuthMessage,
    dependencies=[Depends(get_current_user)],
)
async def get_auth_status() -> AuthMessage:
    """Indica si el módulo de autenticación se encuentra operativo."""

    return AuthMessage(message="Autenticación lista y conectada a SQLite ✅")


@router.get(
    "/bootstrap/status",
    response_model=BootstrapStatusResponse,
    dependencies=[Depends(get_current_user)],
)
def read_bootstrap_status(db: Session = Depends(get_db)) -> BootstrapStatusResponse:
    """Devuelve si aún es posible registrar la cuenta inicial del sistema."""

    total_users = db.query(func.count(User.id)).scalar() or 0
    return BootstrapStatusResponse(
        message="Estado de bootstrap consultado correctamente.",
        disponible=total_users == 0,
        usuarios_registrados=int(total_users),
    )


@router.post(
    "/bootstrap",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
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
    verification_token = _build_verification_token(user)
    user_read = UserRead.model_validate(user)
    if settings.SMTP_HOST:
        LOGGER.info(
            f"Token de verificación para bootstrap preparado para envío SMTP a {user.email}"
        )
    else:
        LOGGER.info(
            f"Token de verificación para bootstrap de {user.email}: {verification_token}"
        )
    return RegisterResponse(
        message="Usuario inicial creado correctamente.",
        verification_token=verification_token,
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
    verification_token = _build_verification_token(user)
    user_read = UserRead.model_validate(user)
    if settings.SMTP_HOST:
        LOGGER.info(
            f"Token de verificación preparado para envío SMTP a {user.email}"
        )
    else:
        LOGGER.info(
            f"Token de verificación generado para {user.email}: {verification_token}"
        )
    return RegisterResponse(
        message=REGISTER_SUCCESS_MESSAGE,
        verification_token=verification_token,
        **user_read.model_dump(),
    )


@router.post("/login", response_model=TokenPairResponse)
async def login(
    credentials: LoginRequest = Depends(_login_form_or_json),
    db: Session = Depends(get_db),
) -> TokenPairResponse:
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

    return _issue_tokens(user)


@router.post(
    "/token",
    response_model=TokenPairResponse,
    dependencies=[Depends(RateLimiter(times=5, minutes=1))],
)
async def login_legacy(
    credentials: LoginRequest = Depends(_login_form_or_json),
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    """Alias de compatibilidad para clientes que aún usan ``/auth/token``."""

    return await login(credentials, db)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh_tokens(
    payload: RefreshTokenRequest, db: Session = Depends(get_db)
) -> TokenPairResponse:
    """Renueva el par de tokens utilizando un refresh válido."""

    token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    verify_token_expiry(token_payload)
    user = get_user_by_id(db, _extract_user_id(token_payload.sub))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido.",
        )
    return _issue_tokens(user)


@router.post(
    "/forgot",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> ForgotPasswordResponse:
    """Genera un token temporal para restablecer la contraseña."""

    normalized_email = _normalize_identifier(payload.email)
    user = get_user_by_email(db, normalized_email)
    if user is None:
        return ForgotPasswordResponse(
            message="Si el correo existe, recibirás instrucciones en breves.",
            reset_token=None,
        )

    token = _build_password_reset_token(user)
    if settings.SMTP_HOST:
        LOGGER.info(
            f"Solicitud de restablecimiento lista para envío SMTP a {user.email}"
        )
    else:
        LOGGER.info(
            f"Token de restablecimiento para {user.email}: {token}"
        )
    return ForgotPasswordResponse(
        message="Se enviaron las instrucciones de restablecimiento.",
        reset_token=token,
    )


@router.post("/reset", response_model=AuthMessage)
def reset_password(
    payload: ResetPasswordRequest, db: Session = Depends(get_db)
) -> AuthMessage:
    """Aplica una nueva contraseña usando un token válido."""

    token_payload = decode_token(payload.token, expected_type="password_reset")
    verify_token_expiry(token_payload)
    user = get_user_by_id(db, _extract_user_id(token_payload.sub))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado para el token proporcionado.",
        )

    with transactional_session(db):
        user.hashed_password = get_password_hash(payload.new_password)
        db.add(user)
        flush_session(db)
    LOGGER.info(f"Contraseña restablecida para el usuario {user.email}")
    return AuthMessage(message="Contraseña actualizada correctamente.")


@router.post("/verify", response_model=AuthMessage)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)) -> AuthMessage:
    """Marca una cuenta como verificada a partir del token enviado por correo."""

    token_payload = decode_token(payload.token, expected_type="email_verification")
    verify_token_expiry(token_payload)
    user = get_user_by_id(db, _extract_user_id(token_payload.sub))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado para la verificación.",
        )

    if not user.is_verified:
        with transactional_session(db):
            user.is_verified = True
            db.add(user)
            flush_session(db)
        LOGGER.info(f"Correo verificado para {user.email}")
    else:
        LOGGER.info(f"Correo ya verificado para {user.email}")

    return AuthMessage(message="Correo verificado correctamente.")


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
    verify_token_expiry(payload)
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
