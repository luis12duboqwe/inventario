"""Rutas de autenticación y alta inicial del sistema."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import ADMIN, normalize_roles
from ..database import get_db
from ..security import create_access_token, hash_password, require_active_user, verify_password

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


@router.post("/token", response_model=schemas.TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, form_data.username)
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    token = create_access_token(subject=user.username)
    return schemas.TokenResponse(access_token=token)


@router.get("/me", response_model=schemas.UserResponse)
async def read_current_user(current_user=Depends(require_active_user)):
    return current_user
