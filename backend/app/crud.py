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
