"""Operaciones de base de datos para las entidades principales."""
from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session, joinedload

from . import models, schemas


def _ensure_unique_identifiers(
    db: Session,
    *,
    imei: str | None,
    serial: str | None,
    exclude_device_id: int | None = None,
) -> None:
    if imei:
        statement = select(models.Device).where(models.Device.imei == imei)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
            raise ValueError("device_identifier_conflict")
    if serial:
        statement = select(models.Device).where(models.Device.serial == serial)
        if exclude_device_id:
            statement = statement.where(models.Device.id != exclude_device_id)
        if db.scalars(statement).first() is not None:
            raise ValueError("device_identifier_conflict")


def _to_decimal(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _recalculate_sale_price(device: models.Device) -> None:
    base_cost = _to_decimal(device.costo_unitario)
    margin = _to_decimal(device.margen_porcentaje)
    sale_factor = Decimal("1") + (margin / Decimal("100"))
    device.unit_price = (base_cost * sale_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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


def _device_value(device: models.Device) -> Decimal:
    return Decimal(device.quantity) * (device.unit_price or Decimal("0"))


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
    store = models.Store(**payload.model_dump())
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
    payload_data = payload.model_dump()
    provided_fields = payload.model_fields_set
    imei = payload_data.get("imei")
    serial = payload_data.get("serial")
    _ensure_unique_identifiers(db, imei=imei, serial=serial)
    unit_price = payload_data.get("unit_price") if "unit_price" in provided_fields else None
    if unit_price is None:
        payload_data.setdefault("unit_price", Decimal("0"))
    if payload_data.get("costo_unitario") is None:
        payload_data["costo_unitario"] = Decimal("0")
    if payload_data.get("margen_porcentaje") is None:
        payload_data["margen_porcentaje"] = Decimal("0")
    if payload_data.get("estado_comercial") is None:
        payload_data["estado_comercial"] = models.CommercialState.NUEVO
    if payload_data.get("garantia_meses") is None:
        payload_data["garantia_meses"] = 0
    device = models.Device(store_id=store_id, **payload_data)
    if unit_price is None:
        _recalculate_sale_price(device)
    else:
        device.unit_price = unit_price
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
    updated_fields = payload.model_dump(exclude_unset=True)
    manual_price = None
    if "unit_price" in updated_fields:
        manual_price = updated_fields.pop("unit_price")
    imei = updated_fields.get("imei")
    serial = updated_fields.get("serial")
    _ensure_unique_identifiers(
        db,
        imei=imei,
        serial=serial,
        exclude_device_id=device.id,
    )

    sensitive_before = {
        "costo_unitario": device.costo_unitario,
        "estado_comercial": device.estado_comercial,
        "proveedor": device.proveedor,
    }

    for key, value in updated_fields.items():
        setattr(device, key, value)
    if manual_price is not None:
        device.unit_price = manual_price
    elif {"costo_unitario", "margen_porcentaje"}.intersection(updated_fields):
        _recalculate_sale_price(device)
    db.commit()
    db.refresh(device)

    fields_changed = list(updated_fields.keys())
    if manual_price is not None:
        fields_changed.append("unit_price")
    if fields_changed:
        sensitive_after = {
            "costo_unitario": device.costo_unitario,
            "estado_comercial": device.estado_comercial,
            "proveedor": device.proveedor,
        }
        sensitive_changes = {
            key: {"before": str(sensitive_before[key]), "after": str(value)}
            for key, value in sensitive_after.items()
            if sensitive_before.get(key) != value
        }
        _log_action(
            db,
            action="device_updated",
            entity_type="device",
            entity_id=str(device.id),
            performed_by_id=performed_by_id,
            details=json.dumps({"fields": fields_changed, "sensitive": sensitive_changes}),
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


def search_devices(db: Session, filters: schemas.DeviceSearchFilters) -> list[models.Device]:
    statement = (
        select(models.Device)
        .options(joinedload(models.Device.store))
        .join(models.Store)
    )
    if filters.imei:
        statement = statement.where(models.Device.imei == filters.imei)
    if filters.serial:
        statement = statement.where(models.Device.serial == filters.serial)
    if filters.capacidad_gb is not None:
        statement = statement.where(models.Device.capacidad_gb == filters.capacidad_gb)
    if filters.color:
        statement = statement.where(models.Device.color.ilike(f"%{filters.color}%"))
    if filters.marca:
        statement = statement.where(models.Device.marca.ilike(f"%{filters.marca}%"))
    if filters.modelo:
        statement = statement.where(models.Device.modelo.ilike(f"%{filters.modelo}%"))
    statement = statement.order_by(models.Device.store_id.asc(), models.Device.sku.asc())
    return list(db.scalars(statement).unique())


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


def compute_inventory_metrics(db: Session, *, low_stock_threshold: int = 5) -> dict[str, object]:
    stores = list_inventory_summary(db)

    total_devices = 0
    total_units = 0
    total_value = Decimal("0")
    store_metrics: list[dict[str, object]] = []
    low_stock: list[dict[str, object]] = []

    for store in stores:
        device_count = len(store.devices)
        store_units = sum(device.quantity for device in store.devices)
        store_value = sum(_device_value(device) for device in store.devices)

        total_devices += device_count
        total_units += store_units
        total_value += store_value

        store_metrics.append(
            {
                "store_id": store.id,
                "store_name": store.name,
                "device_count": device_count,
                "total_units": store_units,
                "total_value": store_value,
            }
        )

        for device in store.devices:
            if device.quantity <= low_stock_threshold:
                low_stock.append(
                    {
                        "store_id": store.id,
                        "store_name": store.name,
                        "device_id": device.id,
                        "sku": device.sku,
                        "name": device.name,
                        "quantity": device.quantity,
                        "unit_price": device.unit_price or Decimal("0"),
                    }
                )

    store_metrics.sort(key=lambda item: item["total_value"], reverse=True)
    low_stock.sort(key=lambda item: (item["quantity"], item["name"]))

    return {
        "totals": {
            "stores": len(stores),
            "devices": total_devices,
            "total_units": total_units,
            "total_value": total_value,
        },
        "top_stores": store_metrics[:5],
        "low_stock_devices": low_stock[:10],
    }


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


def get_store_membership(db: Session, *, user_id: int, store_id: int) -> models.StoreMembership | None:
    statement = select(models.StoreMembership).where(
        models.StoreMembership.user_id == user_id,
        models.StoreMembership.store_id == store_id,
    )
    return db.scalars(statement).first()


def upsert_store_membership(
    db: Session,
    *,
    user_id: int,
    store_id: int,
    can_create_transfer: bool,
    can_receive_transfer: bool,
) -> models.StoreMembership:
    membership = get_store_membership(db, user_id=user_id, store_id=store_id)
    if membership is None:
        membership = models.StoreMembership(
            user_id=user_id,
            store_id=store_id,
            can_create_transfer=can_create_transfer,
            can_receive_transfer=can_receive_transfer,
        )
        db.add(membership)
    else:
        membership.can_create_transfer = can_create_transfer
        membership.can_receive_transfer = can_receive_transfer
    db.commit()
    db.refresh(membership)
    return membership


def _require_store_permission(
    db: Session,
    *,
    user_id: int,
    store_id: int,
    permission: str,
) -> models.StoreMembership:
    membership = get_store_membership(db, user_id=user_id, store_id=store_id)
    if membership is None:
        raise PermissionError("store_membership_required")
    if permission == "create" and not membership.can_create_transfer:
        raise PermissionError("store_create_forbidden")
    if permission == "receive" and not membership.can_receive_transfer:
        raise PermissionError("store_receive_forbidden")
    return membership


def list_store_memberships(db: Session, store_id: int) -> list[models.StoreMembership]:
    statement = (
        select(models.StoreMembership)
        .options(joinedload(models.StoreMembership.user))
        .where(models.StoreMembership.store_id == store_id)
        .order_by(models.StoreMembership.user_id.asc())
    )
    return list(db.scalars(statement))


def create_transfer_order(
    db: Session,
    payload: schemas.TransferOrderCreate,
    *,
    requested_by_id: int,
) -> models.TransferOrder:
    if payload.origin_store_id == payload.destination_store_id:
        raise ValueError("transfer_same_store")

    origin_store = get_store(db, payload.origin_store_id)
    destination_store = get_store(db, payload.destination_store_id)

    _require_store_permission(
        db,
        user_id=requested_by_id,
        store_id=origin_store.id,
        permission="create",
    )

    if not payload.items:
        raise ValueError("transfer_items_required")

    order = models.TransferOrder(
        origin_store=origin_store,
        destination_store=destination_store,
        status=models.TransferStatus.SOLICITADA,
        requested_by_id=requested_by_id,
        reason=payload.reason,
    )
    db.add(order)
    db.flush()

    for item in payload.items:
        device = get_device(db, origin_store.id, item.device_id)
        if item.quantity <= 0:
            raise ValueError("transfer_invalid_quantity")
        order_item = models.TransferOrderItem(
            transfer_order=order,
            device=device,
            quantity=item.quantity,
        )
        db.add(order_item)

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="transfer_created",
        entity_type="transfer_order",
        entity_id=str(order.id),
        performed_by_id=requested_by_id,
        details=json.dumps({
            "origin": origin_store.id,
            "destination": destination_store.id,
            "reason": payload.reason,
        }),
    )
    db.commit()
    db.refresh(order)
    return order


def get_transfer_order(db: Session, transfer_id: int) -> models.TransferOrder:
    statement = (
        select(models.TransferOrder)
        .options(
            joinedload(models.TransferOrder.items).joinedload(models.TransferOrderItem.device),
            joinedload(models.TransferOrder.origin_store),
            joinedload(models.TransferOrder.destination_store),
        )
        .where(models.TransferOrder.id == transfer_id)
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("transfer_not_found") from exc


def dispatch_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
) -> models.TransferOrder:
    order = get_transfer_order(db, transfer_id)
    if order.status not in {models.TransferStatus.SOLICITADA}:
        raise ValueError("transfer_invalid_transition")

    _require_store_permission(
        db,
        user_id=performed_by_id,
        store_id=order.origin_store_id,
        permission="create",
    )

    order.status = models.TransferStatus.EN_TRANSITO
    order.dispatched_by_id = performed_by_id
    order.dispatched_at = datetime.utcnow()
    order.reason = reason or order.reason

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="transfer_dispatched",
        entity_type="transfer_order",
        entity_id=str(order.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"status": order.status.value, "reason": reason}),
    )
    db.commit()
    db.refresh(order)
    return order


def _apply_transfer_reception(
    db: Session,
    order: models.TransferOrder,
    *,
    performed_by_id: int,
) -> None:
    for item in order.items:
        device = item.device
        if device.store_id != order.origin_store_id:
            raise ValueError("transfer_device_mismatch")
        if item.quantity <= 0:
            raise ValueError("transfer_invalid_quantity")
        if device.quantity < item.quantity:
            raise ValueError("transfer_insufficient_stock")

        if (device.imei or device.serial) and device.quantity != item.quantity:
            raise ValueError("transfer_requires_full_unit")

        if device.imei or device.serial:
            device.store_id = order.destination_store_id
        else:
            device.quantity -= item.quantity
            destination_statement = select(models.Device).where(
                models.Device.store_id == order.destination_store_id,
                models.Device.sku == device.sku,
            )
            destination_device = db.scalars(destination_statement).first()
            if destination_device is None:
                clone = models.Device(
                    store_id=order.destination_store_id,
                    sku=device.sku,
                    name=device.name,
                    quantity=item.quantity,
                    unit_price=device.unit_price,
                    marca=device.marca,
                    modelo=device.modelo,
                    color=device.color,
                    capacidad_gb=device.capacidad_gb,
                    estado_comercial=device.estado_comercial,
                    proveedor=device.proveedor,
                    costo_unitario=device.costo_unitario,
                    margen_porcentaje=device.margen_porcentaje,
                    garantia_meses=device.garantia_meses,
                    lote=device.lote,
                    fecha_compra=device.fecha_compra,
                )
                db.add(clone)
            else:
                destination_device.quantity += item.quantity


def receive_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
) -> models.TransferOrder:
    order = get_transfer_order(db, transfer_id)
    if order.status not in {models.TransferStatus.SOLICITADA, models.TransferStatus.EN_TRANSITO}:
        raise ValueError("transfer_invalid_transition")

    _require_store_permission(
        db,
        user_id=performed_by_id,
        store_id=order.destination_store_id,
        permission="receive",
    )

    _apply_transfer_reception(db, order, performed_by_id=performed_by_id)

    order.status = models.TransferStatus.RECIBIDA
    order.received_by_id = performed_by_id
    order.received_at = datetime.utcnow()
    order.reason = reason or order.reason

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="transfer_received",
        entity_type="transfer_order",
        entity_id=str(order.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"status": order.status.value, "reason": reason}),
    )
    db.commit()
    db.refresh(order)
    return order


def cancel_transfer_order(
    db: Session,
    transfer_id: int,
    *,
    performed_by_id: int,
    reason: str | None,
) -> models.TransferOrder:
    order = get_transfer_order(db, transfer_id)
    if order.status in {models.TransferStatus.RECIBIDA, models.TransferStatus.CANCELADA}:
        raise ValueError("transfer_invalid_transition")

    _require_store_permission(
        db,
        user_id=performed_by_id,
        store_id=order.origin_store_id,
        permission="create",
    )

    order.status = models.TransferStatus.CANCELADA
    order.cancelled_by_id = performed_by_id
    order.cancelled_at = datetime.utcnow()
    order.reason = reason or order.reason

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="transfer_cancelled",
        entity_type="transfer_order",
        entity_id=str(order.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"status": order.status.value, "reason": reason}),
    )
    db.commit()
    db.refresh(order)
    return order


def list_transfer_orders(
    db: Session,
    *,
    store_id: int | None = None,
    limit: int = 50,
) -> list[models.TransferOrder]:
    statement = (
        select(models.TransferOrder)
        .options(joinedload(models.TransferOrder.items))
        .order_by(models.TransferOrder.created_at.desc())
        .limit(limit)
    )
    if store_id is not None:
        statement = statement.where(
            (models.TransferOrder.origin_store_id == store_id)
            | (models.TransferOrder.destination_store_id == store_id)
        )
    return list(db.scalars(statement).unique())


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
                        "unit_price": float(device.unit_price or Decimal("0")),
                        "inventory_value": float(_device_value(device)),
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
