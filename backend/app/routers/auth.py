"""Rutas de autenticación y alta inicial del sistema."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import ADMIN, GERENTE, normalize_roles
from ..database import get_db
from ..security import (
    create_access_token,
    decode_token,
    hash_password,
    require_active_user,
    verify_password,
    verify_totp,
)


def _authenticate_user(
    db: Session,
    *,
    username: str,
    password: str,
    otp: str,
):
    user = crud.get_user_by_username(db, username)
    if user is None:
        crud.log_unknown_login_attempt(db, username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    crud.clear_login_lock(db, user)
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cuenta bloqueada hasta {user.locked_until.isoformat()}",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo.",
        )
    if not verify_password(password, user.password_hash):
        crud.register_failed_login(db, user, reason="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    roles = {assignment.role.name for assignment in user.roles}
    secret = crud.get_totp_secret(db, user.id)
    requires_totp = (
        settings.enable_2fa
        and roles.intersection({ADMIN, GERENTE})
        and secret is not None
        and secret.is_active
    )
    if requires_totp and not otp:
        crud.register_failed_login(db, user, reason="missing_totp")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código TOTP requerido",
        )
    if requires_totp and not verify_totp(secret.secret, otp):
        crud.register_failed_login(db, user, reason="invalid_totp")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código TOTP inválido",
        )
    if requires_totp:
        crud.update_totp_last_verified(db, user.id)
    return user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/bootstrap/status", response_model=schemas.BootstrapStatusResponse)
def get_bootstrap_status(db: Session = Depends(get_db)):
    total_users = crud.count_users(db)
    return schemas.BootstrapStatusResponse(
        disponible=total_users == 0,
        usuarios_registrados=total_users,
    )


@router.post("/bootstrap", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.count_users(db) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El sistema ya cuenta con usuarios registrados.",
        )
    try:
        role_names = normalize_roles(payload.roles) | {ADMIN}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    user = crud.create_user(
        db,
        payload,
        password_hash=hash_password(payload.password),
        role_names=sorted(role_names),
    )
    return user


class OAuth2PasswordRequestFormWithOTP(OAuth2PasswordRequestForm):
    def __init__(
        self,
        *,
        username: str = Form(...),
        password: str = Form(...),
        scope: str = Form(""),
        client_id: str | None = Form(default=None),
        client_secret: str | None = Form(default=None),
        otp: str = Form(default=""),
    ) -> None:
        super().__init__(
            username=username,
            password=password,
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.otp = otp.strip()


@router.post("/token", response_model=schemas.TokenResponse)
def login(form_data: OAuth2PasswordRequestFormWithOTP = Depends(), db: Session = Depends(get_db)):
    user = _authenticate_user(
        db,
        username=form_data.username,
        password=form_data.password,
        otp=form_data.otp,
    )
    token, session_token, expires_at = create_access_token(subject=user.username)
    session = crud.create_active_session(
        db,
        user_id=user.id,
        session_token=session_token,
        expires_at=expires_at,
    )
    crud.register_successful_login(db, user, session_token=session.session_token)
    return schemas.TokenResponse(access_token=token, session_id=session.id)


@router.post("/session", response_model=schemas.SessionLoginResponse)
def login_with_session(
    response: Response,
    form_data: OAuth2PasswordRequestFormWithOTP = Depends(),
    db: Session = Depends(get_db),
):
    user = _authenticate_user(
        db,
        username=form_data.username,
        password=form_data.password,
        otp=form_data.otp,
    )
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.session_cookie_expire_minutes
    )
    session_token = secrets.token_urlsafe(48)
    session = crud.create_active_session(
        db,
        user_id=user.id,
        session_token=session_token,
        expires_at=expires_at,
    )
    crud.register_successful_login(db, user, session_token=session.session_token)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_cookie_expire_minutes * 60,
        expires=expires_at,
    )
    return schemas.SessionLoginResponse(
        session_id=session.id,
        detail="Sesión iniciada correctamente.",
    )


@router.post("/verify", response_model=schemas.TokenVerificationResponse)
def verify_access_token(
    payload: schemas.TokenVerificationRequest, db: Session = Depends(get_db)
):
    try:
        token_payload = decode_token(payload.token)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "Token inválido."
        return schemas.TokenVerificationResponse(is_valid=False, detail=detail)

    session = crud.mark_session_used(db, token_payload.jti)
    if session is None:
        return schemas.TokenVerificationResponse(
            is_valid=False,
            detail="Sesión inválida, expirada o revocada.",
        )

    user = session.user or crud.get_user_by_username(db, token_payload.sub)
    if user is None or not user.is_active:
        return schemas.TokenVerificationResponse(
            is_valid=False,
            detail="Usuario inactivo o inexistente para este token.",
        )

    return schemas.TokenVerificationResponse(
        is_valid=True,
        detail="Token válido.",
        session_id=session.id,
        expires_at=session.expires_at,
        user=user,
    )


@router.get("/me", response_model=schemas.UserResponse)
async def read_current_user(current_user=Depends(require_active_user)):
    return current_user


@router.post(
    "/password/request",
    response_model=schemas.PasswordResetResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_reset(
    payload: schemas.PasswordRecoveryRequest, db: Session = Depends(get_db)
):
    reset_token: str | None = None
    user = crud.get_user_by_username(db, payload.username)
    if user is not None:
        record = crud.create_password_reset_token(
            db,
            user.id,
            expires_minutes=settings.password_reset_token_minutes,
        )
        if settings.testing_mode:
            reset_token = record.token
    detail = "Si el usuario existe, se envió un enlace de recuperación."
    return schemas.PasswordResetResponse(detail=detail, reset_token=reset_token)


@router.post(
    "/password/reset",
    response_model=schemas.PasswordResetResponse,
    status_code=status.HTTP_200_OK,
)
def reset_password(payload: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    record = crud.get_password_reset_token(db, payload.token)
    if (
        record is None
        or record.used_at is not None
        or record.expires_at <= datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado.",
        )
    try:
        user = crud.get_user(db, record.user_id)
    except LookupError as exc:  # pragma: no cover - defensivo
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        ) from exc
    hashed = hash_password(payload.new_password)
    crud.reset_user_password(db, user, password_hash=hashed, performed_by_id=None)
    crud.mark_password_reset_token_used(db, record)
    active_sessions = crud.list_active_sessions(
        db,
        user_id=user.id,
        limit=200,
        offset=0,
    )
    for session in active_sessions:
        if session.revoked_at is None:
            crud.revoke_session(
                db,
                session.id,
                revoked_by_id=None,
                reason="password_reset",
            )
    detail = "Contraseña actualizada correctamente."
    response_payload = schemas.PasswordResetResponse(detail=detail)
    if settings.testing_mode:
        response_payload.reset_token = record.token
    return response_payload
