"""Operaciones CRUD para usuarios, roles y autenticación."""
from __future__ import annotations

import json
import secrets
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Literal, cast

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, joinedload

from backend.app import models, schemas
from backend.app.config import settings
from backend.app.core.roles import ADMIN, GERENTE, INVITADO, OPERADOR
from backend.app.core.constants import ROLE_MODULE_PERMISSION_MATRIX
from backend.app.core.transactions import flush_session, transactional_session
from backend.app import security_tokens as token_protection
from backend.app.utils import audit as audit_utils
from backend.app.utils import audit_trail as audit_trail_utils
from backend.app.utils.sql_helpers import token_filter

from .audit import log_audit_event as log_action, get_last_audit_entries, get_persistent_audit_alerts
from .stores import get_store


ROLE_PRIORITY: dict[str, int] = {
    ADMIN: 0,
    GERENTE: 1,
    OPERADOR: 2,
    INVITADO: 3,
}


def user_display_name(user: models.User | None) -> str | None:
    if user is None:
        return None
    candidates = [
        getattr(user, "full_name", None),
        getattr(user, "nombre", None),
        getattr(user, "username", None),
        getattr(user, "correo", None),
    ]
    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = candidate.strip()
            if normalized:
                return normalized
    return None


def ensure_role_permissions(db: Session, role_name: str) -> None:
    defaults = ROLE_MODULE_PERMISSION_MATRIX.get(role_name)
    if not defaults:
        return
    with transactional_session(db):
        for module, flags in defaults.items():
            statement = (
                select(models.Permission)
                .where(models.Permission.role_name == role_name)
                .where(models.Permission.module == module)
            )
            permission = db.scalars(statement).first()
            if permission is None:
                permission = models.Permission(
                    role_name=role_name, module=module)
                permission.can_view = bool(flags.get("can_view", False))
                permission.can_edit = bool(flags.get("can_edit", False))
                permission.can_delete = bool(flags.get("can_delete", False))
                db.add(permission)
            else:
                if permission.can_view is None:
                    permission.can_view = bool(flags.get("can_view", False))
                if permission.can_edit is None:
                    permission.can_edit = bool(flags.get("can_edit", False))
                if permission.can_delete is None:
                    permission.can_delete = bool(
                        flags.get("can_delete", False))
        flush_session(db)


def ensure_role(db: Session, name: str) -> models.Role:
    statement = select(models.Role).where(models.Role.name == name)
    role = db.scalars(statement).first()
    if role is None:
        role = models.Role(name=name)
        db.add(role)
        flush_session(db)
    ensure_role_permissions(db, name)
    return role


def list_roles(
    db: Session, *, limit: int = 50, offset: int = 0
) -> list[models.Role]:
    statement = (
        select(models.Role)
        .order_by(models.Role.name.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).unique())


def user_has_module_permission(
    db: Session, user: models.User, module: str, action: Literal["view", "edit", "delete"]
) -> bool:
    normalized_module = module.strip().lower()
    if not normalized_module:
        return False
    roles = {assignment.role.name for assignment in user.roles}
    roles.add(user.rol)
    if ADMIN in roles:
        return True
    field_name = {
        "view": "can_view",
        "edit": "can_edit",
        "delete": "can_delete",
    }[action]
    statement = (
        select(models.Permission)
        .where(models.Permission.role_name.in_(roles))
        .where(models.Permission.module == normalized_module)
    )
    for permission in db.scalars(statement):
        if bool(getattr(permission, field_name)):
            return True
    return False


def get_user_by_username(db: Session, username: str) -> models.User | None:
    statement = (
        select(models.User)
        .options(
            joinedload(models.User.roles).joinedload(models.UserRole.role),
            joinedload(models.User.store),
        )
        .where(
            models.User.username == username,
            models.User.is_deleted.is_(False),
        )
    )
    return db.scalars(statement).first()


def get_user(db: Session, user_id: int) -> models.User:
    statement = (
        select(models.User)
        .options(
            joinedload(models.User.roles).joinedload(models.UserRole.role),
            joinedload(models.User.store),
        )
        .where(
            models.User.id == user_id,
            models.User.is_deleted.is_(False),
        )
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("user_not_found") from exc


def _select_primary_role(role_names: Iterable[str]) -> str:
    """Determina el rol primario a persistir en la tabla de usuarios."""

    ordered_roles = [role for role in role_names if role in ROLE_PRIORITY]
    if not ordered_roles:
        return OPERADOR
    return min(ordered_roles, key=ROLE_PRIORITY.__getitem__)


def _normalize_role_names(role_names: Iterable[str]) -> list[str]:
    """Normaliza la colección de roles removiendo duplicados y espacios."""

    unique_roles: list[str] = []
    seen: set[str] = set()
    for role_name in role_names:
        normalized = role_name.strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_roles.append(normalized)
    return unique_roles


def _build_role_assignments(
    db: Session, role_names: Iterable[str]
) -> list[models.UserRole]:
    """Crea las asociaciones de roles a partir de los nombres únicos provistos."""

    assignments: list[models.UserRole] = []
    for role_name in role_names:
        role = ensure_role(db, role_name)
        # role.id puede ser None antes de flush aunque el tipo ORM sea int; garantizar persistencia
        if getattr(role, "id", None) is None:
            flush_session(db)
        assignments.append(models.UserRole(role_id=role.id))
    return assignments


def create_user(
    db: Session,
    payload: schemas.UserCreate,
    *,
    password_hash: str,
    role_names: Iterable[str],
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.User:
    normalized_roles = _normalize_role_names(role_names)
    primary_role = _select_primary_role(normalized_roles)
    if primary_role not in normalized_roles:
        normalized_roles.append(primary_role)
    store_id: int | None = None
    if payload.store_id is not None:
        try:
            store = get_store(db, payload.store_id)
        except LookupError as exc:
            raise ValueError("store_not_found") from exc
        store_id = store.id
    user = models.User(
        username=payload.username,
        full_name=payload.full_name,
        telefono=payload.telefono,
        rol=primary_role,
        estado="ACTIVO",
        password_hash=password_hash,
        store_id=store_id,
    )
    with transactional_session(db):
        db.add(user)
        try:
            flush_session(db)
        except IntegrityError as exc:
            raise ValueError("user_already_exists") from exc

        assignments = _build_role_assignments(db, normalized_roles)
        user.roles.extend(assignments)

        metadata: dict[str, object] = {
            "roles": sorted(normalized_roles),
        }
        if store_id is not None:
            metadata["store_id"] = store_id
        if reason:
            metadata["reason"] = reason.strip()

        log_details: dict[str, object] = {
            "description": f"Usuario creado: {user.username}",
            "metadata": metadata,
        }

        log_action(
            db,
            action="user_created",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
            details=log_details,
        )

        flush_session(db)
        db.refresh(user)
    return user


def list_users(
    db: Session,
    *,
    search: str | None = None,
    role: str | None = None,
    status: Literal["all", "active", "inactive", "locked"] = "all",
    store_id: int | None = None,
    limit: int | None = 50,
    offset: int = 0,
) -> list[models.User]:
    statement = (
        select(models.User)
        .options(
            joinedload(models.User.roles).joinedload(models.UserRole.role),
            joinedload(models.User.store),
        )
        .where(models.User.is_deleted.is_(False))
        .order_by(models.User.username.asc())
    )

    if search:
        normalized = f"%{search.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.User.username).like(normalized),
                func.lower(models.User.full_name).like(normalized),
            )
        )

    if role:
        normalized_role = role.strip().upper()
        statement = statement.where(
            or_(
                func.upper(models.User.rol) == normalized_role,
                models.User.roles.any(
                    models.UserRole.role.has(
                        func.upper(models.Role.name) == normalized_role
                    )
                ),
            )
        )

    status_normalized = (status or "all").lower()
    if status_normalized == "active":
        statement = statement.where(models.User.is_active.is_(True))
    elif status_normalized == "inactive":
        statement = statement.where(models.User.is_active.is_(False))

    if store_id is not None:
        statement = statement.where(models.User.store_id == store_id)

    if status_normalized == "locked":
        users = list(db.scalars(statement).unique())
        locked_users = [user for user in users if _user_is_locked(user)]
        end = offset + limit if limit is not None else None
        return locked_users[offset:end]

    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def count_users(
    db: Session,
    *,
    include_inactive: bool = True,
) -> int:
    statement = select(func.count()).select_from(models.User).where(
        models.User.is_deleted.is_(False)
    )
    if not include_inactive:
        statement = statement.where(models.User.is_active.is_(True))
    total = db.scalar(statement)
    return int(total or 0)


def soft_delete_user(
    db: Session,
    user_id: int,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.User:
    user = get_user(db, user_id)
    if user.is_deleted:
        return user

    with transactional_session(db):
        user.is_deleted = True
        user.is_active = False
        user.estado = "DESACTIVADO"
        user.locked_until = None
        db.add(user)

        metadata: dict[str, object] = {"user_id": int(user.id)}
        if reason:
            metadata["reason"] = reason.strip()

        details: dict[str, object] = {
            "description": f"Usuario desactivado: {user.username}",
            "metadata": metadata,
        }

        log_action(
            db,
            action="user_soft_deleted",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
            details=details,
        )
        flush_session(db)
        db.refresh(user)
    return user


def set_user_roles(
    db: Session,
    user: models.User,
    role_names: Iterable[str],
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.User:
    normalized_roles = _normalize_role_names(role_names)
    primary_role = _select_primary_role(normalized_roles)
    if primary_role not in normalized_roles:
        normalized_roles.append(primary_role)
    log_payload: dict[str, object] = {"roles": sorted(normalized_roles)}
    if reason:
        log_payload["reason"] = reason

    with transactional_session(db):
        user.roles.clear()
        flush_session(db)
        assignments = _build_role_assignments(db, normalized_roles)
        user.roles.extend(assignments)

        user.rol = primary_role

        log_action(
            db,
            action="user_roles_updated",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
            details=json.dumps(log_payload, ensure_ascii=False),
        )

        flush_session(db)
        db.refresh(user)
    return user


def set_user_status(
    db: Session,
    user: models.User,
    *,
    is_active: bool,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.User:
    estado_value: str = "ACTIVO" if is_active else "INACTIVO"
    log_payload: dict[str, object] = {
        "is_active": is_active,
        "estado": estado_value,
    }
    if reason:
        log_payload["reason"] = reason

    with transactional_session(db):
        user.is_active = is_active
        user.estado = estado_value

        log_action(
            db,
            action="user_status_changed",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
            details=json.dumps(log_payload, ensure_ascii=False),
        )

        flush_session(db)
        db.refresh(user)
    return user


def get_role(db: Session, name: str) -> models.Role:
    statement = select(models.Role).where(
        func.upper(models.Role.name) == name.strip().upper())
    role = db.scalars(statement).first()
    if role is None:
        raise LookupError("role_not_found")
    return role


def update_user(
    db: Session,
    user: models.User,
    updates: dict[str, object],
    *,
    password_hash: str | None = None,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.User:
    was_inactive = not user.is_active
    changes: dict[str, object] = {}

    if "full_name" in updates:
        raw_name = updates.get("full_name")
        normalized_name = raw_name.strip() if isinstance(
            raw_name, str) and raw_name.strip() else None
        if user.full_name != normalized_name:
            user.full_name = normalized_name
            changes["full_name"] = normalized_name

    if "telefono" in updates:
        raw_phone = updates.get("telefono")
        normalized_phone = raw_phone.strip() if isinstance(
            raw_phone, str) and raw_phone.strip() else None
        if user.telefono != normalized_phone:
            user.telefono = normalized_phone
            changes["telefono"] = normalized_phone

    if "store_id" in updates:
        store_value = updates.get("store_id")
        if store_value is None:
            if user.store_id is not None:
                user.store_id = None
                changes["store_id"] = None
        else:
            # Validar tipos aceptados para conversión (int directo o str numérica)
            if isinstance(store_value, int):
                store_id = store_value
            elif isinstance(store_value, str):
                raw = store_value.strip()
                if not raw or not raw.isdigit():
                    raise ValueError("invalid_store_id")
                store_id = int(raw)
            else:
                raise ValueError("invalid_store_id")
            try:
                store = get_store(db, store_id)
            except LookupError as exc:
                raise ValueError("store_not_found") from exc
            if user.store_id != store.id:
                user.store_id = store.id
                changes["store_id"] = store.id

    if password_hash:
        user.password_hash = password_hash
        user.failed_login_attempts = 0
        user.locked_until = None
        changes["password_changed"] = True
        if was_inactive:
            user.is_active = True
            user.estado = "ACTIVO"
            changes["is_active"] = True
            changes["estado"] = "ACTIVO"

    if not changes:
        return user

    log_payload: dict[str, object] = {"changes": changes}
    if reason:
        log_payload["reason"] = reason

    with transactional_session(db):
        flush_session(db)

        log_action(
            db,
            action="user_updated",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
            details=json.dumps(log_payload, ensure_ascii=False),
        )

        flush_session(db)
        db.refresh(user)
    return user


def list_role_permissions(
    db: Session,
    *,
    role_name: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[schemas.RolePermissionMatrix]:
    role_names: list[str]
    if role_name:
        role = get_role(db, role_name)
        role_names = [role.name]
    else:
        role_names = [role.name for role in list_roles(
            db, limit=limit, offset=offset)]

    if not role_names:
        return []

    with transactional_session(db):
        for name in role_names:
            ensure_role_permissions(db, name)

        flush_session(db)

        statement = (
            select(models.Permission)
            .where(models.Permission.role_name.in_(role_names))
            .order_by(models.Permission.role_name.asc(), models.Permission.module.asc())
        )
        records = list(db.scalars(statement))

    grouped: dict[str, list[schemas.RoleModulePermission]] = {
        name: [] for name in role_names}
    for permission in records:
        grouped.setdefault(permission.role_name, []).append(
            schemas.RoleModulePermission(
                module=permission.module,
                can_view=permission.can_view,
                can_edit=permission.can_edit,
                can_delete=permission.can_delete,
            )
        )

    matrices: list[schemas.RolePermissionMatrix] = []
    for name in role_names:
        permissions = sorted(grouped.get(name, []),
                             key=lambda item: item.module)
        matrices.append(schemas.RolePermissionMatrix(
            role=name, permissions=permissions))
    return matrices


def update_role_permissions(
    db: Session,
    role_name: str,
    permissions: Sequence[schemas.RoleModulePermission],
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> schemas.RolePermissionMatrix:
    role = get_role(db, role_name)
    with transactional_session(db):
        ensure_role_permissions(db, role.name)
        flush_session(db)

        updated_modules: list[dict[str, object]] = []
        for entry in permissions:
            module_key = entry.module.strip().lower()
            statement = (
                select(models.Permission)
                .where(models.Permission.role_name == role.name)
                .where(models.Permission.module == module_key)
            )
            permission = db.scalars(statement).first()
            if permission is None:
                permission = models.Permission(
                    role_name=role.name, module=module_key)
                db.add(permission)
            permission.can_view = bool(entry.can_view)
            permission.can_edit = bool(entry.can_edit)
            permission.can_delete = bool(entry.can_delete)
            updated_modules.append(
                {
                    "module": module_key,
                    "can_view": permission.can_view,
                    "can_edit": permission.can_edit,
                    "can_delete": permission.can_delete,
                }
            )

        flush_session(db)

        log_payload: dict[str, object] = {"permissions": updated_modules}
        if reason:
            log_payload["reason"] = reason
        log_action(
            db,
            action="role_permissions_updated",
            entity_type="role",
            entity_id=role.name,
            performed_by_id=performed_by_id,
            details=json.dumps(log_payload, ensure_ascii=False),
        )

        flush_session(db)

    return list_role_permissions(db, role_name=role.name)[0]


def _user_is_locked(user: models.User) -> bool:
    locked_until = user.locked_until
    if locked_until is None:
        return False
    # Normaliza a consciente de zona horaria (UTC) si viene ingenuo
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return locked_until > datetime.now(timezone.utc)


def build_user_directory(
    db: Session,
    *,
    search: str | None = None,
    role: str | None = None,
    status: Literal["all", "active", "inactive", "locked"] = "all",
    store_id: int | None = None,
) -> schemas.UserDirectoryReport:
    users = list_users(
        db,
        search=search,
        role=role,
        status=status,
        store_id=store_id,
        limit=None,
        offset=0,
    )

    user_ids = [user.id for user in users if getattr(
        user, "id", None) is not None]
    audit_logs = get_last_audit_entries(
        db,
        entity_type="user",
        entity_ids=user_ids,
    )
    audit_trails = {
        key: audit_trail_utils.to_audit_trail(log)
        for key, log in audit_logs.items()
    }

    active_count = sum(1 for user in users if user.is_active)
    inactive_count = sum(1 for user in users if not user.is_active)
    locked_count = sum(1 for user in users if _user_is_locked(user))

    items = [
        schemas.UserDirectoryEntry(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            telefono=user.telefono,
            rol=user.rol,
            estado=user.estado,
            is_active=user.is_active,
            roles=sorted({assignment.role.name for assignment in user.roles}),
            store_id=user.store_id,
            store_name=user.store.name if user.store else None,
            last_login_at=user.last_login_attempt_at,
            ultima_accion=audit_trails.get(str(user.id)),
        )
        for user in users
    ]

    report = schemas.UserDirectoryReport(
        generated_at=datetime.now(timezone.utc),
        filters=schemas.UserDirectoryFilters(
            search=search,
            role=role,
            status=status,
            store_id=store_id,
        ),
        totals=schemas.UserDirectoryTotals(
            total=len(users),
            active=active_count,
            inactive=inactive_count,
            locked=locked_count,
        ),
        items=items,
    )
    return report


def is_session_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


def list_active_sessions(
    db: Session,
    *,
    user_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.ActiveSession]:
    statement = (
        select(models.ActiveSession)
        .order_by(models.ActiveSession.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if user_id is not None:
        statement = statement.where(models.ActiveSession.user_id == user_id)
    return list(db.scalars(statement))


def get_user_dashboard_metrics(
    db: Session,
    *,
    activity_limit: int = 12,
    session_limit: int = 8,
    lookback_hours: int = 48,
) -> schemas.UserDashboardMetrics:
    activity_limit = max(1, min(activity_limit, 50))
    session_limit = max(1, min(session_limit, 25))

    directory = build_user_directory(db)

    activity_statement = (
        select(models.AuditLog)
        .options(joinedload(models.AuditLog.performed_by))
        .where(
            or_(
                models.AuditLog.entity_type.in_(
                    ["user", "usuarios", "security"]),
                models.AuditLog.action.ilike("auth_%"),
                models.AuditLog.action.ilike("user_%"),
            )
        )
        .order_by(models.AuditLog.created_at.desc())
        .limit(activity_limit)
    )
    logs = list(db.scalars(activity_statement))

    target_ids = {
        int(log.entity_id)
        for log in logs
        if log.entity_type in {"user", "usuarios"} and str(log.entity_id).isdigit()
    }
    user_lookup: dict[int, models.User] = {}
    if target_ids:
        lookup_statement = (
            select(models.User)
            .options(joinedload(models.User.store))
            .where(models.User.id.in_(target_ids))
        )
        user_lookup = {user.id: user for user in db.scalars(lookup_statement)}

    recent_activity: list[schemas.UserDashboardActivity] = []
    for log in logs:
        details: dict[str, object] | None = None
        if log.details:
            try:
                parsed = json.loads(log.details)
                if isinstance(parsed, dict):
                    details = cast(dict[str, object], parsed)
                else:
                    details = {"raw": log.details}
            except json.JSONDecodeError:
                details = {"raw": log.details}

        target_user_id: int | None = None
        target_username: str | None = None
        if log.entity_type in {"user", "usuarios"} and str(log.entity_id).isdigit():
            target_user_id = int(log.entity_id)
            target = user_lookup.get(target_user_id)
            if target is not None:
                target_username = user_display_name(target)

        recent_activity.append(
            schemas.UserDashboardActivity(
                id=log.id,
                action=log.action,
                created_at=log.created_at,
                severity=audit_utils.classify_severity(
                    log.action or "", log.details),
                performed_by_id=log.performed_by_id,
                performed_by_name=user_display_name(log.performed_by),
                target_user_id=target_user_id,
                target_username=target_username,
                details=details,
            )
        )

    sessions = list_active_sessions(db)[:session_limit]
    session_entries: list[schemas.UserSessionSummary] = []
    for session in sessions:
        status = "activa"
        if session.revoked_at is not None:
            status = "revocada"
        elif is_session_expired(session.expires_at):
            status = "expirada"
        session_entries.append(
            schemas.UserSessionSummary(
                session_id=session.id,
                user_id=session.user_id,
                username=user_display_name(
                    session.user) or f"Usuario {session.user_id}",
                created_at=session.created_at,
                last_used_at=session.last_used_at,
                expires_at=session.expires_at,
                status=status,
                revoke_reason=session.revoke_reason,
            )
        )

    persistent_alerts = [
        alert
        for alert in get_persistent_audit_alerts(
            db,
            threshold_minutes=60,
            min_occurrences=1,
            lookback_hours=lookback_hours,
            limit=10,
        )
        if str(alert.get("entity_type", "")).lower()
        in {"user", "usuarios", "security"}
    ]
    persistent_map = {
        (str(alert["entity_type"]), str(alert["entity_id"])): alert
        for alert in persistent_alerts
    }

    alert_logs_statement = (
        select(models.AuditLog)
        .where(models.AuditLog.entity_type.in_(["user", "usuarios", "security"]))
        .order_by(models.AuditLog.created_at.desc())
        .limit(100)
    )
    alert_logs = list(db.scalars(alert_logs_statement))
    summary = audit_utils.summarize_alerts(alert_logs, max_highlights=5)

    highlights: list[schemas.AuditHighlight] = []
    acknowledged_entities: dict[tuple[str, str],
                                schemas.AuditAcknowledgedEntity] = {}
    for highlight in summary.highlights:
        entity_type = highlight.get("entity_type", "")
        entity_id = highlight.get("entity_id", "")
        key = (entity_type, entity_id)
        alert_data = persistent_map.get(key)
        raw_status = str(alert_data.get("status", "pending")
                         ) if alert_data else "pending"
        status = "acknowledged" if raw_status.lower() == "acknowledged" else "pending"
        acknowledged_at = cast(datetime | None, alert_data.get(
            "acknowledged_at")) if alert_data else None
        acknowledged_by_id = cast(int | None, alert_data.get(
            "acknowledged_by_id")) if alert_data else None
        acknowledged_by_name = cast(str | None, alert_data.get(
            "acknowledged_by_name")) if alert_data else None
        acknowledged_note = cast(str | None, alert_data.get(
            "acknowledged_note")) if alert_data else None

        if status == "acknowledged" and acknowledged_at is not None:
            acknowledged_entities[key] = schemas.AuditAcknowledgedEntity(
                entity_type=entity_type,
                entity_id=entity_id,
                acknowledged_at=acknowledged_at,
                acknowledged_by_id=acknowledged_by_id,
                acknowledged_by_name=acknowledged_by_name,
                note=acknowledged_note,
            )

        highlights.append(
            schemas.AuditHighlight(
                id=highlight.get("id", 0),
                action=highlight.get("action", ""),
                created_at=highlight.get(
                    "created_at", datetime.now(timezone.utc)),
                severity=highlight.get("severity", "info"),
                entity_type=entity_type,
                entity_id=entity_id,
                status=status,
                acknowledged_at=acknowledged_at,
                acknowledged_by_id=acknowledged_by_id,
                acknowledged_by_name=acknowledged_by_name,
                acknowledged_note=acknowledged_note,
            )
        )

    pending_count = len(
        [item for item in highlights if item.status != "acknowledged"])
    acknowledged_list = list(acknowledged_entities.values())

    audit_alerts = schemas.DashboardAuditAlerts(
        total=summary.total,
        critical=summary.critical,
        warning=summary.warning,
        info=summary.info,
        pending_count=pending_count,
        acknowledged_count=len(acknowledged_list),
        highlights=highlights,
        acknowledged_entities=acknowledged_list,
    )

    return schemas.UserDashboardMetrics(
        generated_at=datetime.now(timezone.utc),
        totals=directory.totals,
        recent_activity=recent_activity,
        active_sessions=session_entries,
        audit_alerts=audit_alerts,
    )


def get_totp_secret(db: Session, user_id: int) -> models.UserTOTPSecret | None:
    statement = select(models.UserTOTPSecret).where(
        models.UserTOTPSecret.user_id == user_id)
    return db.scalars(statement).first()


def provision_totp_secret(
    db: Session,
    user_id: int,
    secret: str,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.UserTOTPSecret:
    details = json.dumps({"reason": reason},
                         ensure_ascii=False) if reason else None
    with transactional_session(db):
        record = get_totp_secret(db, user_id)
        if record is None:
            record = models.UserTOTPSecret(
                user_id=user_id, secret=secret, is_active=False)
            db.add(record)
        else:
            record.secret = secret
            record.is_active = False
            record.activated_at = None
            record.last_verified_at = None
        flush_session(db)
        log_action(
            db,
            action="totp_provisioned",
            entity_type="user",
            entity_id=str(user_id),
            performed_by_id=performed_by_id,
            details=details,
        )
    db.refresh(record)
    return record


def activate_totp_secret(
    db: Session,
    user_id: int,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> models.UserTOTPSecret:
    details = json.dumps({"reason": reason},
                         ensure_ascii=False) if reason else None
    with transactional_session(db):
        record = get_totp_secret(db, user_id)
        if record is None:
            raise LookupError("totp_not_provisioned")
        record.is_active = True
        now = datetime.now(timezone.utc)
        record.activated_at = now
        record.last_verified_at = now
        flush_session(db)
        log_action(
            db,
            action="totp_activated",
            entity_type="user",
            entity_id=str(user_id),
            performed_by_id=performed_by_id,
            details=details,
        )
    db.refresh(record)
    return record


def deactivate_totp_secret(
    db: Session,
    user_id: int,
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> None:
    details = json.dumps({"reason": reason},
                         ensure_ascii=False) if reason else None
    with transactional_session(db):
        record = get_totp_secret(db, user_id)
        if record is None:
            return
        record.is_active = False
        flush_session(db)
        log_action(
            db,
            action="totp_deactivated",
            entity_type="user",
            entity_id=str(user_id),
            performed_by_id=performed_by_id,
            details=details,
        )


def update_totp_last_verified(db: Session, user_id: int) -> None:
    with transactional_session(db):
        record = get_totp_secret(db, user_id)
        if record is None:
            return
        record.last_verified_at = datetime.now(timezone.utc)
        flush_session(db)


def clear_login_lock(db: Session, user: models.User) -> models.User:
    if user.locked_until:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until <= datetime.now(timezone.utc):
            with transactional_session(db):
                user.locked_until = None
                user.failed_login_attempts = 0
                flush_session(db)
            db.refresh(user)
    return user


def register_failed_login(
    db: Session, user: models.User, *, reason: str | None = None
) -> models.User:
    locked_until: datetime | None = None
    with transactional_session(db):
        now = datetime.now(timezone.utc)
        user.failed_login_attempts += 1
        user.last_login_attempt_at = now
        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            locked_until = now + \
                timedelta(minutes=settings.account_lock_minutes)
            user.locked_until = locked_until
        details_payload: dict[str, object] = {
            "attempts": user.failed_login_attempts,
            "locked_until": locked_until.isoformat() if locked_until else None,
        }
        if reason:
            details_payload["reason"] = reason
        details = json.dumps(details_payload, ensure_ascii=False)
        flush_session(db)
        log_action(
            db,
            action="auth_login_failed",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=user.id,
            details=details,
        )
    db.refresh(user)
    return user


def register_successful_login(
    db: Session, user: models.User, *, session_token: str | None = None
) -> models.User:
    with transactional_session(db):
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_attempt_at = datetime.now(timezone.utc)
        details_payload = (
            {"session_hint": session_token[-6:]} if session_token else None
        )
        details = (
            json.dumps(details_payload, ensure_ascii=False)
            if details_payload is not None
            else None
        )
        flush_session(db)
        log_action(
            db,
            action="auth_login_success",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=user.id,
            details=details,
        )
    db.refresh(user)
    return user


def log_unknown_login_attempt(db: Session, username: str) -> None:
    log_action(
        db,
        action="auth_login_failed",
        entity_type="auth",
        entity_id=username,
        performed_by_id=None,
    )


def create_password_reset_token(
    db: Session, user_id: int, *, expires_minutes: int
) -> models.PasswordResetToken:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + \
        timedelta(minutes=expires_minutes)
    protected_token = token_protection.protect_token(token)
    record = models.PasswordResetToken(
        user_id=user_id,
        token=protected_token,
        expires_at=expires_at,
    )
    record.plaintext_token = token  # type: ignore[attr-defined]
    details = json.dumps(
        {"expires_at": record.expires_at.isoformat()}, ensure_ascii=False
    )
    with transactional_session(db):
        db.add(record)
        flush_session(db)
        log_action(
            db,
            action="password_reset_requested",
            entity_type="user",
            entity_id=str(user_id),
            performed_by_id=None,
            details=details,
        )
    db.refresh(record)
    return record


def get_password_reset_token(
    db: Session, token: str
) -> models.PasswordResetToken | None:
    protected_token = token_protection.protect_token(token)
    statement = select(models.PasswordResetToken).where(
        models.PasswordResetToken.token == protected_token
    )
    return db.scalars(statement).first()


def mark_password_reset_token_used(
    db: Session, token_record: models.PasswordResetToken
) -> models.PasswordResetToken:
    with transactional_session(db):
        token_record.used_at = datetime.now(timezone.utc)
        flush_session(db)
    db.refresh(token_record)
    return token_record


def reset_user_password(
    db: Session,
    user: models.User,
    *,
    password_hash: str,
    performed_by_id: int | None = None,
) -> models.User:
    with transactional_session(db):
        user.password_hash = password_hash
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_attempt_at = datetime.now(timezone.utc)
        flush_session(db)
        log_action(
            db,
            action="password_reset_completed",
            entity_type="user",
            entity_id=str(user.id),
            performed_by_id=performed_by_id,
        )
    db.refresh(user)
    return user


def create_active_session(
    db: Session,
    user_id: int,
    *,
    session_token: str,
    expires_at: datetime | None = None,
) -> models.ActiveSession:
    stored_token = token_protection.protect_token(session_token)
    session = models.ActiveSession(
        user_id=user_id, session_token=stored_token, expires_at=expires_at
    )
    with transactional_session(db):
        db.add(session)
        flush_session(db)
    db.refresh(session)
    return session


def update_active_session_token(
    db: Session, session: models.ActiveSession, new_token_plaintext: str
) -> models.ActiveSession:
    protected_token = token_protection.protect_token(new_token_plaintext)
    with transactional_session(db):
        session.session_token = protected_token
        flush_session(db)
    db.refresh(session)
    return session


def get_active_session_by_token(db: Session, session_token: str) -> models.ActiveSession | None:
    protected_token = token_protection.protect_token(session_token)
    statement = (
        select(models.ActiveSession)
        .options(
            joinedload(models.ActiveSession.user)
            .joinedload(models.User.roles)
            .joinedload(models.UserRole.role)
        )
        .where(models.ActiveSession.session_token == protected_token)
    )
    return db.scalars(statement).first()


def mark_session_used(db: Session, session_token: str) -> models.ActiveSession | None:
    session = get_active_session_by_token(db, session_token)
    if session is None or session.revoked_at is not None:
        return None
    if is_session_expired(session.expires_at):
        if session.revoked_at is None:
            with transactional_session(db):
                session.revoked_at = datetime.now(timezone.utc)
                session.revoke_reason = session.revoke_reason or "expired"
                flush_session(db)
            db.refresh(session)
        return None
    with transactional_session(db):
        session.last_used_at = datetime.now(timezone.utc)
        flush_session(db)
    db.refresh(session)
    return session


def add_jwt_to_blacklist(
    db: Session,
    *,
    jti: str,
    token_type: str,
    expires_at: datetime,
    revoked_by_id: int | None = None,
    reason: str | None = None,
) -> models.JWTBlacklist:
    record = models.JWTBlacklist(
        jti=jti,
        token_type=token_type,
        expires_at=expires_at,
        revoked_by_id=revoked_by_id,
        reason=reason,
    )
    with transactional_session(db):
        db.add(record)
        flush_session(db)
    db.refresh(record)
    return record


def is_jwt_blacklisted(db: Session, jti: str) -> bool:
    statement = select(models.JWTBlacklist).where(
        models.JWTBlacklist.jti == jti)
    record = db.scalars(statement).first()
    if record is None:
        return False
    if record.expires_at and is_session_expired(record.expires_at):
        with transactional_session(db):
            db.delete(record)
            flush_session(db)
        return False
    return True


def revoke_session(
    db: Session,
    session_id: int,
    *,
    revoked_by_id: int | None,
    reason: str,
) -> models.ActiveSession:
    statement = select(models.ActiveSession).where(
        models.ActiveSession.id == session_id)
    session = db.scalars(statement).first()
    if session is None:
        raise LookupError("session_not_found")
    if session.revoked_at is not None:
        return session
    with transactional_session(db):
        session.revoked_at = datetime.now(timezone.utc)
        session.revoked_by_id = revoked_by_id
        session.revoke_reason = reason
        flush_session(db)
    db.refresh(session)
    return session


def list_role_permissions(
    db: Session,
    *,
    role_name: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[schemas.RolePermissionMatrix]:
    role_names: list[str]
    if role_name:
        role = get_role(db, role_name)
        role_names = [role.name]
    else:
        role_names = [role.name for role in list_roles(
            db, limit=limit, offset=offset)]

    if not role_names:
        return []

    with transactional_session(db):
        for name in role_names:
            ensure_role_permissions(db, name)

        flush_session(db)

        statement = (
            select(models.Permission)
            .where(models.Permission.role_name.in_(role_names))
            .order_by(models.Permission.role_name.asc(), models.Permission.module.asc())
        )
        records = list(db.scalars(statement))

    grouped: dict[str, list[schemas.RoleModulePermission]] = {
        name: [] for name in role_names}
    for permission in records:
        grouped.setdefault(permission.role_name, []).append(
            schemas.RoleModulePermission(
                module=permission.module,
                can_view=permission.can_view,
                can_edit=permission.can_edit,
                can_delete=permission.can_delete,
            )
        )

    matrices: list[schemas.RolePermissionMatrix] = []
    for name in role_names:
        permissions = sorted(grouped.get(name, []),
                             key=lambda item: item.module)
        matrices.append(schemas.RolePermissionMatrix(
            role=name, permissions=permissions))
    return matrices


def update_role_permissions(
    db: Session,
    role_name: str,
    permissions: Sequence[schemas.RoleModulePermission],
    *,
    performed_by_id: int | None = None,
    reason: str | None = None,
) -> schemas.RolePermissionMatrix:
    role = get_role(db, role_name)
    with transactional_session(db):
        ensure_role_permissions(db, role.name)
        flush_session(db)

        updated_modules: list[dict[str, object]] = []
        for entry in permissions:
            module_key = entry.module.strip().lower()
            statement = (
                select(models.Permission)
                .where(models.Permission.role_name == role.name)
                .where(models.Permission.module == module_key)
            )
            permission = db.scalars(statement).first()
            if permission is None:
                permission = models.Permission(
                    role_name=role.name, module=module_key)
                db.add(permission)
            permission.can_view = bool(entry.can_view)
            permission.can_edit = bool(entry.can_edit)
            permission.can_delete = bool(entry.can_delete)
            updated_modules.append(
                {
                    "module": module_key,
                    "can_view": permission.can_view,
                    "can_edit": permission.can_edit,
                    "can_delete": permission.can_delete,
                }
            )

        flush_session(db)

        log_payload: dict[str, object] = {"permissions": updated_modules}
        if reason:
            log_payload["reason"] = reason
        log_action(
            db,
            action="role_permissions_updated",
            entity_type="role",
            entity_id=role.name,
            performed_by_id=performed_by_id,
            details=json.dumps(log_payload, ensure_ascii=False),
        )

        flush_session(db)

    return list_role_permissions(db, role_name=role.name)[0]


def _user_is_locked(user: models.User) -> bool:
    locked_until = user.locked_until
    if locked_until is None:
        return False
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return locked_until > datetime.now(timezone.utc)


def build_user_directory(
    db: Session,
    *,
    search: str | None = None,
    role: str | None = None,
    status: Literal["all", "active", "inactive", "locked"] = "all",
    store_id: int | None = None,
) -> schemas.UserDirectoryReport:
    users = list_users(
        db,
        search=search,
        role=role,
        status=status,
        store_id=store_id,
        limit=None,
        offset=0,
    )

    user_ids = [user.id for user in users if getattr(
        user, "id", None) is not None]
    audit_logs = get_last_audit_entries(
        db,
        entity_type="user",
        entity_ids=user_ids,
    )
    audit_trails = {
        key: audit_trail_utils.to_audit_trail(log)
        for key, log in audit_logs.items()
    }

    active_count = sum(1 for user in users if user.is_active)
    inactive_count = sum(1 for user in users if not user.is_active)
    locked_count = sum(1 for user in users if _user_is_locked(user))

    items = [
        schemas.UserDirectoryEntry(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            telefono=user.telefono,
            rol=user.rol,
            estado=user.estado,
            is_active=user.is_active,
            roles=sorted({assignment.role.name for assignment in user.roles}),
            store_id=user.store_id,
            store_name=user.store.name if user.store else None,
            last_login_at=user.last_login_attempt_at,
            ultima_accion=audit_trails.get(str(user.id)),
        )
        for user in users
    ]

    report = schemas.UserDirectoryReport(
        generated_at=datetime.now(timezone.utc),
        filters=schemas.UserDirectoryFilters(
            search=search,
            role=role,
            status=status,
            store_id=store_id,
        ),
        totals=schemas.UserDirectoryTotals(
            total=len(users),
            active=active_count,
            inactive=inactive_count,
            locked=locked_count,
        ),
        items=items,
    )
    return report


def get_user_dashboard_metrics(
    db: Session,
    *,
    activity_limit: int = 12,
    session_limit: int = 8,
    lookback_hours: int = 48,
) -> schemas.UserDashboardMetrics:
    activity_limit = max(1, min(activity_limit, 50))
    session_limit = max(1, min(session_limit, 25))

    directory = build_user_directory(db)

    activity_statement = (
        select(models.AuditLog)
        .options(joinedload(models.AuditLog.performed_by))
        .where(
            or_(
                models.AuditLog.entity_type.in_(
                    ["user", "usuarios", "security"]),
                models.AuditLog.action.ilike("auth_%"),
                models.AuditLog.action.ilike("user_%"),
            )
        )
        .order_by(models.AuditLog.created_at.desc())
        .limit(activity_limit)
    )
    logs = list(db.scalars(activity_statement))

    target_ids = {
        int(log.entity_id)
        for log in logs
        if log.entity_type in {"user", "usuarios"} and str(log.entity_id).isdigit()
    }
    user_lookup: dict[int, models.User] = {}
    if target_ids:
        lookup_statement = (
            select(models.User)
            .options(joinedload(models.User.store))
            .where(models.User.id.in_(target_ids))
        )
        user_lookup = {user.id: user for user in db.scalars(lookup_statement)}

    recent_activity: list[schemas.UserDashboardActivity] = []
    for log in logs:
        details: dict[str, object] | None = None
        if log.details:
            try:
                parsed = json.loads(log.details)
                if isinstance(parsed, dict):
                    details = parsed
                else:
                    details = {"raw": log.details}
            except json.JSONDecodeError:
                details = {"raw": log.details}

        target_user_id: int | None = None
        target_username: str | None = None
        if log.entity_type in {"user", "usuarios"} and str(log.entity_id).isdigit():
            target_user_id = int(log.entity_id)
            target = user_lookup.get(target_user_id)
            if target is not None:
                target_username = user_display_name(target)

        recent_activity.append(
            schemas.UserDashboardActivity(
                id=log.id,
                action=log.action,
                created_at=log.created_at,
                severity=audit_utils.classify_severity(
                    log.action or "", log.details),
                performed_by_id=log.performed_by_id,
                performed_by_name=user_display_name(log.performed_by),
                target_user_id=target_user_id,
                target_username=target_username,
                details=details,
            )
        )

    sessions = list_active_sessions(db)[:session_limit]
    session_entries: list[schemas.UserSessionSummary] = []
    for session in sessions:
        status = "activa"
        if session.revoked_at is not None:
            status = "revocada"
        elif is_session_expired(session.expires_at):
            status = "expirada"
        session_entries.append(
            schemas.UserSessionSummary(
                session_id=session.id,
                user_id=session.user_id,
                username=user_display_name(
                    session.user) or f"Usuario {session.user_id}",
                created_at=session.created_at,
                last_used_at=session.last_used_at,
                expires_at=session.expires_at,
                status=status,
                revoke_reason=session.revoke_reason,
            )
        )

    persistent_alerts = [
        alert
        for alert in get_persistent_audit_alerts(
            db,
            threshold_minutes=60,
            min_occurrences=1,
            lookback_hours=lookback_hours,
            limit=10,
        )
        if str(alert.get("entity_type", "")).lower()
        in {"user", "usuarios", "security"}
    ]
    persistent_map = {
        (str(alert["entity_type"]), str(alert["entity_id"])): alert
        for alert in persistent_alerts
    }

    alert_logs_statement = (
        select(models.AuditLog)
        .where(models.AuditLog.entity_type.in_(["user", "usuarios", "security"]))
        .order_by(models.AuditLog.created_at.desc())
        .limit(100)
    )
    alert_logs = list(db.scalars(alert_logs_statement))
    summary = audit_utils.summarize_alerts(alert_logs, max_highlights=5)

    highlights: list[schemas.AuditHighlight] = []
    acknowledged_entities: dict[tuple[str, str],
                                schemas.AuditAcknowledgedEntity] = {}
    for highlight in summary.highlights:
        key = (highlight["entity_type"], highlight["entity_id"])
        alert_data = persistent_map.get(key)
        raw_status = str(alert_data.get("status", "pending")
                         ) if alert_data else "pending"
        status = "acknowledged" if raw_status.lower() == "acknowledged" else "pending"
        acknowledged_at = alert_data.get(
            "acknowledged_at") if alert_data else None
        acknowledged_by_id = alert_data.get(
            "acknowledged_by_id") if alert_data else None
        acknowledged_by_name = alert_data.get(
            "acknowledged_by_name") if alert_data else None
        acknowledged_note = alert_data.get(
            "acknowledged_note") if alert_data else None

        if status == "acknowledged" and acknowledged_at is not None:
            acknowledged_entities[key] = schemas.AuditAcknowledgedEntity(
                entity_type=highlight["entity_type"],
                entity_id=highlight["entity_id"],
                acknowledged_at=acknowledged_at,
                acknowledged_by_id=acknowledged_by_id,
                acknowledged_by_name=acknowledged_by_name,
                note=acknowledged_note,
            )

        highlights.append(
            schemas.AuditHighlight(
                id=highlight["id"],
                action=highlight["action"],
                created_at=highlight["created_at"],
                severity=highlight["severity"],
                entity_type=highlight["entity_type"],
                entity_id=highlight["entity_id"],
                status=status,
                acknowledged_at=acknowledged_at,
                acknowledged_by_id=acknowledged_by_id,
                acknowledged_by_name=acknowledged_by_name,
                acknowledged_note=acknowledged_note,
            )
        )

    pending_count = len(
        [item for item in highlights if item.status != "acknowledged"])
    acknowledged_list = list(acknowledged_entities.values())

    audit_alerts = schemas.DashboardAuditAlerts(
        total=summary.total,
        critical=summary.critical,
        warning=summary.warning,
        info=summary.info,
        pending_count=pending_count,
        acknowledged_count=len(acknowledged_list),
        highlights=highlights,
        acknowledged_entities=acknowledged_list,
    )

    return schemas.UserDashboardMetrics(
        generated_at=datetime.now(timezone.utc),
        totals=directory.totals,
        recent_activity=recent_activity,
        active_sessions=session_entries,
        audit_alerts=audit_alerts,
    )


__all__ = [
    "activate_totp_secret",
    "add_jwt_to_blacklist",
    "build_user_directory",
    "clear_login_lock",
    "count_users",
    "create_active_session",
    "create_password_reset_token",
    "create_user",
    "deactivate_totp_secret",
    "ensure_role",
    "ensure_role_permissions",
    "get_active_session_by_token",
    "get_password_reset_token",
    "get_role",
    "get_totp_secret",
    "get_user",
    "get_user_by_username",
    "get_user_dashboard_metrics",
    "is_jwt_blacklisted",
    "is_session_expired",
    "list_active_sessions",
    "list_role_permissions",
    "list_roles",
    "list_users",
    "log_unknown_login_attempt",
    "mark_password_reset_token_used",
    "mark_session_used",
    "provision_totp_secret",
    "register_failed_login",
    "register_successful_login",
    "reset_user_password",
    "revoke_session",
    "set_user_roles",
    "set_user_status",
    "soft_delete_user",
    "update_active_session_token",
    "update_role_permissions",
    "update_totp_last_verified",
    "update_user",
    "user_display_name",
    "user_has_module_permission",
]
