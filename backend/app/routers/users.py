"""Gestión de usuarios y roles."""
from __future__ import annotations

from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import ADMIN, GERENTE, normalize_roles
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import hash_password, require_roles
from ..services import user_reports

router = APIRouter(prefix="/users", tags=["usuarios"])


@router.get("/roles", response_model=list[schemas.RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.list_roles(db)


@router.get("/permissions", response_model=list[schemas.RolePermissionMatrix])
def list_role_permissions(
    role: str | None = Query(default=None, min_length=1, max_length=60),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    try:
        return crud.list_role_permissions(db, role_name=role)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado") from exc


@router.put("/roles/{role_name}/permissions", response_model=schemas.RolePermissionMatrix)
def update_role_permissions(
    role_name: str,
    payload: schemas.RolePermissionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    reason: str = Depends(require_reason),
):
    try:
        return crud.update_role_permissions(
            db,
            role_name,
            payload.permissions,
            performed_by_id=current_user.id,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado") from exc


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
    try:
        user = crud.create_user(
            db,
            payload,
            password_hash=hash_password(payload.password),
            role_names=sorted(role_names),
        )
    except ValueError as exc:
        if str(exc) == "store_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La sucursal asignada no existe") from exc
        raise
    return user


@router.get("", response_model=list[schemas.UserResponse])
def list_users(
    search: str | None = Query(default=None, min_length=1, max_length=120),
    role: str | None = Query(default=None, min_length=1, max_length=60),
    status_filter: Literal["all", "active", "inactive", "locked"] = Query(
        default="all", alias="status"
    ),
    store_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.list_users(
        db,
        search=search,
        role=role,
        status=status_filter,
        store_id=store_id,
    )


@router.get("/dashboard", response_model=schemas.UserDashboardMetrics)
def user_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.get_user_dashboard_metrics(db)


@router.get("/export")
def export_users(
    format: Literal["pdf", "xlsx"] = Query(default="pdf"),
    search: str | None = Query(default=None, min_length=1, max_length=120),
    role: str | None = Query(default=None, min_length=1, max_length=60),
    status_filter: Literal["all", "active", "inactive", "locked"] = Query(
        default="all", alias="status"
    ),
    store_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    reason: str = Depends(require_reason),
):
    report = crud.build_user_directory(
        db,
        search=search,
        role=role,
        status=status_filter,
        store_id=store_id,
    )

    if format == "pdf":
        pdf_bytes = user_reports.render_user_directory_pdf(report)
        buffer = BytesIO(pdf_bytes)
        headers = {"Content-Disposition": "attachment; filename=usuarios_softmobile.pdf"}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
    if format == "xlsx":
        workbook = user_reports.render_user_directory_xlsx(report)
        headers = {
            "Content-Disposition": "attachment; filename=usuarios_softmobile.xlsx"
        }
        return StreamingResponse(
            workbook,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Formato de exportación no soportado",
    )


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
    reason: str = Depends(require_reason),
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
    updated = crud.set_user_roles(
        db,
        user,
        sorted(role_names),
        performed_by_id=current_user.id,
        reason=reason,
    )
    return updated


@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(
    payload: schemas.UserUpdate,
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    reason: str = Depends(require_reason),
):
    try:
        user = crud.get_user(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado") from exc

    updates = payload.model_dump(exclude_unset=True)
    password_value = updates.pop("password", None)
    password_hash = None
    if isinstance(password_value, str) and password_value:
        password_hash = hash_password(password_value)

    try:
        updated = crud.update_user(
            db,
            user,
            updates,
            password_hash=password_hash,
            performed_by_id=current_user.id,
            reason=reason,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "store_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La sucursal asignada no existe",
            ) from exc
        if message == "invalid_store_id":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El identificador de sucursal es inválido",
            ) from exc
        raise

    return updated


@router.patch("/{user_id}", response_model=schemas.UserResponse)
def update_user_status(
    payload: schemas.UserStatusUpdate,
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    reason: str = Depends(require_reason),
):
    try:
        user = crud.get_user(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado") from exc
    return crud.set_user_status(
        db,
        user,
        is_active=payload.is_active,
        performed_by_id=current_user.id,
        reason=reason,
    )
