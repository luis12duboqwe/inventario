"""Gestión de usuarios y roles."""
from __future__ import annotations

from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import ADMIN, GERENTE, normalize_roles
from ..database import get_db
from ..routers.dependencies import require_reason
from ..security import enforce_password_policy, hash_password, require_roles
from ..services import audit_logger, user_reports

router = APIRouter(prefix="/users", tags=["usuarios"])


def _serialize_user(user_obj, audit):
    if audit is not None:
        setattr(user_obj, "ultima_accion", audit)
    elif not hasattr(user_obj, "ultima_accion"):
        setattr(user_obj, "ultima_accion", None)
    return schemas.UserResponse.model_validate(user_obj, from_attributes=True)


def _user_with_audit(db: Session, user_obj) -> schemas.UserResponse:
    user_id = getattr(user_obj, "id", None)
    audit = None
    if user_id is not None:
        audit_map = audit_logger.get_last_audit_trails(
            db,
            entity_type="user",
            entity_ids=[user_id],
        )
        audit = audit_map.get(str(user_id))
    return _serialize_user(user_obj, audit)


@router.get(
    "/roles",
    response_model=list[schemas.RoleResponse],
    dependencies=[Depends(require_roles(ADMIN))],
)
def list_roles(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.list_roles(db, limit=limit, offset=offset)


@router.get(
    "/permissions",
    response_model=list[schemas.RolePermissionMatrix],
    dependencies=[Depends(require_roles(ADMIN))],
)
def list_role_permissions(
    role: str | None = Query(default=None, min_length=1, max_length=60),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    try:
        return crud.list_role_permissions(
            db, role_name=role, limit=limit, offset=offset
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rol no encontrado") from exc


@router.put(
    "/roles/{role_name}/permissions",
    response_model=schemas.RolePermissionMatrix,
    dependencies=[Depends(require_roles(ADMIN))],
)
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


@router.post(
    "",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(ADMIN))],
)
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
    enforce_password_policy(payload.password, username=payload.username)
    try:
        user = crud.create_user(
            db,
            payload,
            password_hash=hash_password(payload.password),
            role_names=sorted(role_names),
            performed_by_id=current_user.id,
        )
    except ValueError as exc:
        if str(exc) == "store_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La sucursal asignada no existe") from exc
        raise
    return _user_with_audit(db, user)


@router.get(
    "",
    response_model=list[schemas.UserResponse],
    dependencies=[Depends(require_roles(ADMIN))],
)
def list_users(
    search: str | None = Query(default=None, min_length=1, max_length=120),
    role: str | None = Query(default=None, min_length=1, max_length=60),
    status_filter: Literal["all", "active", "inactive", "locked"] = Query(
        default="all", alias="status"
    ),
    store_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    users = crud.list_users(
        db,
        search=search,
        role=role,
        status=status_filter,
        store_id=store_id,
        limit=limit,
        offset=offset,
    )
    audit_map = audit_logger.get_last_audit_trails(
        db,
        entity_type="user",
        entity_ids=[user.id for user in users if getattr(user, "id", None) is not None],
    )
    return [
        _serialize_user(user, audit_map.get(str(user.id)))
        for user in users
    ]


@router.get(
    "/dashboard",
    response_model=schemas.UserDashboardMetrics,
    dependencies=[Depends(require_roles(ADMIN))],
)
def user_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    return crud.get_user_dashboard_metrics(db)


@router.get(
    "/export",
    response_model=schemas.BinaryFileResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
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
        metadata = schemas.BinaryFileResponse(
            filename="usuarios_softmobile.pdf",
            media_type="application/pdf",
        )
        return StreamingResponse(
            buffer,
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )
    if format == "xlsx":
        workbook = user_reports.render_user_directory_xlsx(report)
        metadata = schemas.BinaryFileResponse(
            filename="usuarios_softmobile.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return StreamingResponse(
            workbook,
            media_type=metadata.media_type,
            headers=metadata.content_disposition(),
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Formato de exportación no soportado",
    )


@router.get(
    "/{user_id}",
    response_model=schemas.UserResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
def get_user(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
):
    try:
        user = crud.get_user(db, user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado") from exc
    return _user_with_audit(db, user)


@router.put(
    "/{user_id}/roles",
    response_model=schemas.UserResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
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
    return _user_with_audit(db, updated)


@router.put(
    "/{user_id}",
    response_model=schemas.UserResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
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
        enforce_password_policy(password_value, username=user.username)
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
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="El identificador de sucursal es inválido",
            ) from exc
        raise

    return _user_with_audit(db, updated)


@router.patch(
    "/{user_id}",
    response_model=schemas.UserResponse,
    dependencies=[Depends(require_roles(ADMIN))],
)
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
    updated = crud.set_user_status(
        db,
        user,
        is_active=payload.is_active,
        performed_by_id=current_user.id,
        reason=reason,
    )
    return _user_with_audit(db, updated)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(ADMIN))],
)
def delete_user(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),
    reason: str = Depends(require_reason),
) -> Response:
    try:
        crud.soft_delete_user(
            db,
            user_id,
            performed_by_id=current_user.id if current_user else None,
            reason=reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
