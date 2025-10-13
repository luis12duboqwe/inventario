"""Operaciones de base de datos para las entidades principales."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, joinedload

from . import models, schemas


def _log_action(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    performed_by_id: int | None,
    details: str | None = None,
) -> models.AuditLog:
    log = models.AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by_id=performed_by_id,
        details=details,
    )
    db.add(log)
    db.flush()
    return log


def ensure_role(db: Session, name: str) -> models.Role:
    statement = select(models.Role).where(models.Role.name == name)
    role = db.scalars(statement).first()
    if role is None:
        role = models.Role(name=name)
        db.add(role)
        db.flush()
    return role


def get_user_by_username(db: Session, username: str) -> models.User | None:
    statement = select(models.User).options(joinedload(models.User.roles).joinedload(models.UserRole.role)).where(
        models.User.username == username
    )
    return db.scalars(statement).first()


def get_user(db: Session, user_id: int) -> models.User:
    statement = (
        select(models.User)
        .options(joinedload(models.User.roles).joinedload(models.UserRole.role))
        .where(models.User.id == user_id)
    )
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("user_not_found") from exc


def create_user(
    db: Session,
    payload: schemas.UserCreate,
    *,
    password_hash: str,
    role_names: Iterable[str],
) -> models.User:
    user = models.User(username=payload.username, full_name=payload.full_name, password_hash=password_hash)
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("user_already_exists") from exc

    assigned_roles: list[models.UserRole] = []
    for role_name in role_names:
        role = ensure_role(db, role_name)
        assigned_roles.append(models.UserRole(user=user, role=role))
    if assigned_roles:
        db.add_all(assigned_roles)

    _log_action(
        db,
        action="user_created",
        entity_type="user",
        entity_id=str(user.id),
        performed_by_id=None,
    )

    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[models.User]:
    statement = select(models.User).options(joinedload(models.User.roles).joinedload(models.UserRole.role)).order_by(
        models.User.username.asc()
    )
    return list(db.scalars(statement))


def set_user_roles(db: Session, user: models.User, role_names: Iterable[str]) -> models.User:
    user.roles.clear()
    db.flush()
    for role_name in role_names:
        role = ensure_role(db, role_name)
        db.add(models.UserRole(user=user, role=role))

    db.commit()
    db.refresh(user)
    return user


def create_store(db: Session, payload: schemas.StoreCreate, *, performed_by_id: int | None = None) -> models.Store:
    store = models.Store(**payload.dict())
    db.add(store)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("store_already_exists") from exc
    db.refresh(store)

    _log_action(
        db,
        action="store_created",
        entity_type="store",
        entity_id=str(store.id),
        performed_by_id=performed_by_id,
    )
    db.commit()
    db.refresh(store)
    return store


def list_stores(db: Session) -> list[models.Store]:
    statement = select(models.Store).order_by(models.Store.name.asc())
    return list(db.scalars(statement))


def get_store(db: Session, store_id: int) -> models.Store:
    statement = select(models.Store).where(models.Store.id == store_id)
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("store_not_found") from exc


def create_device(
    db: Session,
    store_id: int,
    payload: schemas.DeviceCreate,
    *,
    performed_by_id: int | None = None,
) -> models.Device:
    get_store(db, store_id)
    device = models.Device(store_id=store_id, **payload.dict())
    db.add(device)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("device_already_exists") from exc
    db.refresh(device)

    _log_action(
        db,
        action="device_created",
        entity_type="device",
        entity_id=str(device.id),
        performed_by_id=performed_by_id,
        details=f"SKU={device.sku}",
    )
    db.commit()
    db.refresh(device)
    return device


def get_device(db: Session, store_id: int, device_id: int) -> models.Device:
    statement = select(models.Device).where(
        models.Device.id == device_id,
        models.Device.store_id == store_id,
    )
    try:
        return db.scalars(statement).one()
    except NoResultFound as exc:
        raise LookupError("device_not_found") from exc


def update_device(
    db: Session,
    store_id: int,
    device_id: int,
    payload: schemas.DeviceUpdate,
    *,
    performed_by_id: int | None = None,
) -> models.Device:
    device = get_device(db, store_id, device_id)
    updated_fields = payload.dict(exclude_unset=True)
    for key, value in updated_fields.items():
        setattr(device, key, value)
    db.commit()
    db.refresh(device)

    if updated_fields:
        _log_action(
            db,
            action="device_updated",
            entity_type="device",
            entity_id=str(device.id),
            performed_by_id=performed_by_id,
            details=str(updated_fields),
        )
        db.commit()
        db.refresh(device)
    return device


def list_devices(db: Session, store_id: int) -> list[models.Device]:
    get_store(db, store_id)
    statement = (
        select(models.Device)
        .where(models.Device.store_id == store_id)
        .order_by(models.Device.sku.asc())
    )
    return list(db.scalars(statement))


def create_inventory_movement(
    db: Session,
    store_id: int,
    payload: schemas.MovementCreate,
    *,
    performed_by_id: int | None = None,
) -> models.InventoryMovement:
    store = get_store(db, store_id)
    device = get_device(db, store_id, payload.device_id)

    if payload.movement_type == models.MovementType.OUT and device.quantity < payload.quantity:
        raise ValueError("insufficient_stock")

    if payload.movement_type == models.MovementType.IN:
        device.quantity += payload.quantity
    elif payload.movement_type == models.MovementType.OUT:
        device.quantity -= payload.quantity
    elif payload.movement_type == models.MovementType.ADJUST:
        device.quantity = payload.quantity

    movement = models.InventoryMovement(
        store=store,
        device=device,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        reason=payload.reason,
        performed_by_id=performed_by_id,
    )
    db.add(movement)
    db.commit()
    db.refresh(device)
    db.refresh(movement)

    _log_action(
        db,
        action="inventory_movement",
        entity_type="device",
        entity_id=str(device.id),
        performed_by_id=performed_by_id,
        details=f"tipo={payload.movement_type.value}, cantidad={payload.quantity}",
    )
    db.commit()
    db.refresh(movement)
    return movement


def list_inventory_summary(db: Session) -> list[models.Store]:
    statement = select(models.Store).options(joinedload(models.Store.devices)).order_by(models.Store.name.asc())
    return list(db.scalars(statement).unique())


def record_sync_session(
    db: Session,
    *,
    store_id: int | None,
    mode: models.SyncMode,
    status: models.SyncStatus,
    triggered_by_id: int | None,
    error_message: str | None = None,
) -> models.SyncSession:
    session = models.SyncSession(
        store_id=store_id,
        mode=mode,
        status=status,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
        error_message=error_message,
        triggered_by_id=triggered_by_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    _log_action(
        db,
        action="sync_session",
        entity_type="store" if store_id else "global",
        entity_id=str(store_id or 0),
        performed_by_id=triggered_by_id,
        details=f"estado={status.value}; modo={mode.value}",
    )
    db.commit()
    db.refresh(session)
    return session


def list_sync_sessions(db: Session, limit: int = 50) -> list[models.SyncSession]:
    statement = (
        select(models.SyncSession)
        .order_by(models.SyncSession.started_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def list_audit_logs(db: Session, limit: int = 100) -> list[models.AuditLog]:
    statement = (
        select(models.AuditLog)
        .order_by(models.AuditLog.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def count_users(db: Session) -> int:
    return db.scalar(select(func.count(models.User.id))) or 0


def create_backup_job(
    db: Session,
    *,
    mode: models.BackupMode,
    pdf_path: str,
    archive_path: str,
    total_size_bytes: int,
    notes: str | None,
    triggered_by_id: int | None,
) -> models.BackupJob:
    job = models.BackupJob(
        mode=mode,
        pdf_path=pdf_path,
        archive_path=archive_path,
        total_size_bytes=total_size_bytes,
        notes=notes,
        triggered_by_id=triggered_by_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _log_action(
        db,
        action="backup_generated",
        entity_type="backup",
        entity_id=str(job.id),
        performed_by_id=triggered_by_id,
        details=f"modo={mode.value}; tamaño={total_size_bytes}",
    )
    db.commit()
    db.refresh(job)
    return job


def list_backup_jobs(db: Session, limit: int = 50) -> list[models.BackupJob]:
    statement = (
        select(models.BackupJob)
        .order_by(models.BackupJob.executed_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement))


def build_inventory_snapshot(db: Session) -> dict[str, object]:
    stores_stmt = (
        select(models.Store)
        .options(joinedload(models.Store.devices))
        .order_by(models.Store.name.asc())
    )
    stores = list(db.scalars(stores_stmt).unique())

    users_stmt = (
        select(models.User)
        .options(joinedload(models.User.roles).joinedload(models.UserRole.role))
        .order_by(models.User.username.asc())
    )
    users = list(db.scalars(users_stmt).unique())

    movements_stmt = select(models.InventoryMovement).order_by(models.InventoryMovement.created_at.desc())
    movements = list(db.scalars(movements_stmt))

    sync_stmt = select(models.SyncSession).order_by(models.SyncSession.started_at.desc())
    sync_sessions = list(db.scalars(sync_stmt))

    audit_stmt = select(models.AuditLog).order_by(models.AuditLog.created_at.desc())
    audits = list(db.scalars(audit_stmt))

    snapshot = {
        "stores": [
            {
                "id": store.id,
                "name": store.name,
                "location": store.location,
                "timezone": store.timezone,
                "devices": [
                    {
                        "id": device.id,
                        "sku": device.sku,
                        "name": device.name,
                        "quantity": device.quantity,
                        "store_id": device.store_id,
                    }
                    for device in store.devices
                ],
            }
            for store in stores
        ],
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "roles": [role.role.name for role in user.roles],
                "created_at": user.created_at.isoformat(),
            }
            for user in users
        ],
        "movements": [
            {
                "id": movement.id,
                "store_id": movement.store_id,
                "device_id": movement.device_id,
                "movement_type": movement.movement_type.value,
                "quantity": movement.quantity,
                "reason": movement.reason,
                "performed_by_id": movement.performed_by_id,
                "created_at": movement.created_at.isoformat(),
            }
            for movement in movements
        ],
        "sync_sessions": [
            {
                "id": sync_session.id,
                "store_id": sync_session.store_id,
                "mode": sync_session.mode.value,
                "status": sync_session.status.value,
                "started_at": sync_session.started_at.isoformat(),
                "finished_at": sync_session.finished_at.isoformat()
                if sync_session.finished_at
                else None,
                "triggered_by_id": sync_session.triggered_by_id,
                "error_message": sync_session.error_message,
            }
            for sync_session in sync_sessions
        ],
        "audit_logs": [
            {
                "id": audit.id,
                "action": audit.action,
                "entity_type": audit.entity_type,
                "entity_id": audit.entity_id,
                "details": audit.details,
                "performed_by_id": audit.performed_by_id,
                "created_at": audit.created_at.isoformat(),
            }
            for audit in audits
        ],
    }
    return snapshot
