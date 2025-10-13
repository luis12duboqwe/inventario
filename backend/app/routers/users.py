"""Gestión de usuarios y roles."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import ADMIN, GERENTE, normalize_roles
from ..database import get_db
from ..security import hash_password, require_roles

router = APIRouter(prefix="/users", tags=["usuarios"])


@router.post("", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    if crud.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El usuario ya existe")
    try:
        role_names = normalize_roles(payload.roles)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not role_names:
        role_names = {GERENTE}
    user = crud.create_user(
        db,
        payload,
        password_hash=hash_password(payload.password),
        role_names=sorted(role_names),
    )
    return user


@router.get("", response_model=list[schemas.UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.list_users(db)


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    try:
        return crud.get_user(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado") from exc


@router.put("/{user_id}/roles", response_model=schemas.UserResponse)
def update_user_roles(
    payload: schemas.UserRolesUpdate,
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    try:
        user = crud.get_user(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado") from exc
    try:
        role_names = normalize_roles(payload.roles)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not role_names:
        role_names = {GERENTE}
    updated = crud.set_user_roles(db, user, sorted(role_names))
    return updated
