"""Rutas de autenticación y alta inicial del sistema."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..core.roles import ADMIN, GERENTE, normalize_roles
from ..database import get_db
from ..security import (
    create_access_token,
    hash_password,
    require_active_user,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
    user = crud.get_user_by_username(db, form_data.username)
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    roles = {assignment.role.name for assignment in user.roles}
    secret = crud.get_totp_secret(db, user.id)
    requires_totp = (
        settings.enable_2fa
        and roles.intersection({ADMIN, GERENTE})
        and secret is not None
        and secret.is_active
    )
    if requires_totp:
        if not form_data.otp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código TOTP requerido")
        if not verify_totp(secret.secret, form_data.otp):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código TOTP inválido")
        crud.update_totp_last_verified(db, user.id)
    token, session_token = create_access_token(subject=user.username)
    session = crud.create_active_session(db, user_id=user.id, session_token=session_token)
    return schemas.TokenResponse(access_token=token, session_id=session.id)


@router.get("/me", response_model=schemas.UserResponse)
async def read_current_user(current_user=Depends(require_active_user)):
    return current_user
