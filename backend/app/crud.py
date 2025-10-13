"""Operaciones de base de datos para las entidades principales."""
from __future__ import annotations

import json
import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta
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


def get_totp_secret(db: Session, user_id: int) -> models.UserTOTPSecret | None:
    statement = select(models.UserTOTPSecret).where(models.UserTOTPSecret.user_id == user_id)
    return db.scalars(statement).first()


def provision_totp_secret(db: Session, user_id: int, secret: str) -> models.UserTOTPSecret:
    record = get_totp_secret(db, user_id)
    if record is None:
        record = models.UserTOTPSecret(user_id=user_id, secret=secret, is_active=False)
        db.add(record)
    else:
        record.secret = secret
        record.is_active = False
        record.activated_at = None
        record.last_verified_at = None
    db.commit()
    db.refresh(record)
    return record


def activate_totp_secret(db: Session, user_id: int) -> models.UserTOTPSecret:
    record = get_totp_secret(db, user_id)
    if record is None:
        raise LookupError("totp_not_provisioned")
    record.is_active = True
    now = datetime.utcnow()
    record.activated_at = now
    record.last_verified_at = now
    db.commit()
    db.refresh(record)
    return record


def deactivate_totp_secret(db: Session, user_id: int) -> None:
    record = get_totp_secret(db, user_id)
    if record is None:
        return
    record.is_active = False
    db.commit()


def update_totp_last_verified(db: Session, user_id: int) -> None:
    record = get_totp_secret(db, user_id)
    if record is None:
        return
    record.last_verified_at = datetime.utcnow()
    db.commit()


def create_active_session(db: Session, user_id: int, *, session_token: str) -> models.ActiveSession:
    session = models.ActiveSession(user_id=user_id, session_token=session_token)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_active_session_by_token(db: Session, session_token: str) -> models.ActiveSession | None:
    statement = select(models.ActiveSession).where(models.ActiveSession.session_token == session_token)
    return db.scalars(statement).first()


def mark_session_used(db: Session, session_token: str) -> models.ActiveSession | None:
    session = get_active_session_by_token(db, session_token)
    if session is None or session.revoked_at is not None:
        return None
    session.last_used_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


def list_active_sessions(db: Session, *, user_id: int | None = None) -> list[models.ActiveSession]:
    statement = select(models.ActiveSession).order_by(models.ActiveSession.created_at.desc())
    if user_id is not None:
        statement = statement.where(models.ActiveSession.user_id == user_id)
    return list(db.scalars(statement))


def revoke_session(
    db: Session,
    session_id: int,
    *,
    revoked_by_id: int | None,
    reason: str,
) -> models.ActiveSession:
    statement = select(models.ActiveSession).where(models.ActiveSession.id == session_id)
    session = db.scalars(statement).first()
    if session is None:
        raise LookupError("session_not_found")
    if session.revoked_at is not None:
        return session
    session.revoked_at = datetime.utcnow()
    session.revoked_by_id = revoked_by_id
    session.revoke_reason = reason
    db.commit()
    db.refresh(session)
    return session


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


def calculate_rotation_analytics(db: Session) -> list[dict[str, object]]:
    sale_stats = (
        select(
            models.SaleItem.device_id,
            func.sum(models.SaleItem.quantity).label("sold_units"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .group_by(models.SaleItem.device_id)
    )
    purchase_stats = (
        select(
            models.PurchaseOrderItem.device_id,
            func.sum(models.PurchaseOrderItem.quantity_received).label("received_units"),
        )
        .group_by(models.PurchaseOrderItem.device_id)
    )

    sold_map = {row.device_id: int(row.sold_units or 0) for row in db.execute(sale_stats)}
    received_map = {row.device_id: int(row.received_units or 0) for row in db.execute(purchase_stats)}

    device_stmt = (
        select(
            models.Device.id,
            models.Device.sku,
            models.Device.name,
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
        .order_by(models.Store.name.asc(), models.Device.name.asc())
    )
    results: list[dict[str, object]] = []
    for row in db.execute(device_stmt):
        sold_units = sold_map.get(row.id, 0)
        received_units = received_map.get(row.id, 0)
        denominator = received_units if received_units > 0 else max(sold_units, 1)
        rotation_rate = sold_units / denominator if denominator else 0
        results.append(
            {
                "store_id": row.store_id,
                "store_name": row.store_name,
                "device_id": row.id,
                "sku": row.sku,
                "name": row.name,
                "sold_units": sold_units,
                "received_units": received_units,
                "rotation_rate": float(round(rotation_rate, 2)),
            }
        )
    return results


def calculate_aging_analytics(db: Session) -> list[dict[str, object]]:
    now_date = datetime.utcnow().date()
    device_stmt = (
        select(
            models.Device.id,
            models.Device.sku,
            models.Device.name,
            models.Device.fecha_compra,
            models.Device.quantity,
            models.Store.name.label("store_name"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
    )
    metrics: list[dict[str, object]] = []
    for row in db.execute(device_stmt):
        purchase_date = row.fecha_compra
        days_in_stock = (now_date - purchase_date).days if purchase_date else 0
        metrics.append(
            {
                "device_id": row.id,
                "sku": row.sku,
                "name": row.name,
                "store_name": row.store_name,
                "days_in_stock": max(days_in_stock, 0),
                "quantity": int(row.quantity or 0),
            }
        )
    metrics.sort(key=lambda item: item["days_in_stock"], reverse=True)
    return metrics


def calculate_stockout_forecast(db: Session) -> list[dict[str, object]]:
    sale_stats = (
        select(
            models.SaleItem.device_id,
            func.sum(models.SaleItem.quantity).label("sold_units"),
            func.min(models.Sale.created_at).label("first_sale"),
            func.max(models.Sale.created_at).label("last_sale"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .group_by(models.SaleItem.device_id)
    )
    sales_map: dict[int, dict[str, object]] = {}
    for row in db.execute(sale_stats):
        sales_map[row.device_id] = {
            "sold_units": int(row.sold_units or 0),
            "first_sale": row.first_sale,
            "last_sale": row.last_sale,
        }

    device_stmt = (
        select(
            models.Device.id,
            models.Device.sku,
            models.Device.name,
            models.Device.quantity,
            models.Store.name.label("store_name"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
    )
    metrics: list[dict[str, object]] = []
    now = datetime.utcnow()
    for row in db.execute(device_stmt):
        stats = sales_map.get(row.id)
        quantity = int(row.quantity or 0)
        if not stats or stats["sold_units"] <= 0:
            metrics.append(
                {
                    "device_id": row.id,
                    "sku": row.sku,
                    "name": row.name,
                    "store_name": row.store_name,
                    "average_daily_sales": 0.0,
                    "projected_days": None,
                    "quantity": quantity,
                }
            )
            continue

        first_sale: datetime | None = stats["first_sale"]
        last_sale: datetime | None = stats["last_sale"] or now
        delta = (last_sale or now) - (first_sale or last_sale or now)
        days = max(delta.days, 1)
        avg_daily_sales = stats["sold_units"] / days
        projected_days = int(quantity / avg_daily_sales) if avg_daily_sales > 0 else None
        metrics.append(
            {
                "device_id": row.id,
                "sku": row.sku,
                "name": row.name,
                "store_name": row.store_name,
                "average_daily_sales": round(float(avg_daily_sales), 2),
                "projected_days": projected_days if projected_days is None else max(projected_days, 0),
                "quantity": quantity,
            }
        )

    metrics.sort(key=lambda item: (item["projected_days"] is None, item["projected_days"] or 0))
    return metrics


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


def enqueue_sync_outbox(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    operation: str,
    payload: dict[str, object],
) -> models.SyncOutbox:
    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    statement = select(models.SyncOutbox).where(
        models.SyncOutbox.entity_type == entity_type,
        models.SyncOutbox.entity_id == entity_id,
    )
    entry = db.scalars(statement).first()
    if entry is None:
        entry = models.SyncOutbox(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            payload=serialized,
            status=models.SyncOutboxStatus.PENDING,
        )
        db.add(entry)
    else:
        entry.operation = operation
        entry.payload = serialized
        entry.status = models.SyncOutboxStatus.PENDING
        entry.attempt_count = 0
        entry.error_message = None
        entry.last_attempt_at = None
    db.commit()
    db.refresh(entry)
    return entry


def list_sync_outbox(
    db: Session,
    *,
    statuses: Iterable[models.SyncOutboxStatus] | None = None,
    limit: int = 100,
) -> list[models.SyncOutbox]:
    statement = (
        select(models.SyncOutbox)
        .order_by(models.SyncOutbox.updated_at.desc())
        .limit(limit)
    )
    if statuses is not None:
        status_tuple = tuple(statuses)
        if status_tuple:
            statement = statement.where(models.SyncOutbox.status.in_(status_tuple))
    return list(db.scalars(statement))


def reset_outbox_entries(db: Session, entry_ids: Iterable[int]) -> list[models.SyncOutbox]:
    ids = list(entry_ids)
    if not ids:
        return []
    statement = select(models.SyncOutbox).where(models.SyncOutbox.id.in_(ids))
    entries = list(db.scalars(statement))
    if not entries:
        return []
    for entry in entries:
        entry.status = models.SyncOutboxStatus.PENDING
        entry.attempt_count = 0
        entry.error_message = None
        entry.last_attempt_at = None
    db.commit()
    return entries


def mark_outbox_attempt(
    db: Session,
    entry_id: int,
    *,
    success: bool,
    error_message: str | None = None,
) -> models.SyncOutbox:
    statement = select(models.SyncOutbox).where(models.SyncOutbox.id == entry_id)
    entry = db.scalars(statement).first()
    if entry is None:
        raise LookupError("outbox_not_found")
    entry.attempt_count += 1
    entry.last_attempt_at = datetime.utcnow()
    if success:
        entry.status = models.SyncOutboxStatus.SENT
        entry.error_message = None
    else:
        entry.status = models.SyncOutboxStatus.FAILED
        entry.error_message = error_message
    db.commit()
    db.refresh(entry)
    return entry


def list_audit_logs(
    db: Session,
    limit: int = 100,
    *,
    action: str | None = None,
    entity_type: str | None = None,
) -> list[models.AuditLog]:
    statement = select(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(limit)
    if action:
        statement = statement.where(models.AuditLog.action == action)
    if entity_type:
        statement = statement.where(models.AuditLog.entity_type == entity_type)
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
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload={
            "id": order.id,
            "status": order.status.value,
            "origin_store_id": order.origin_store_id,
            "destination_store_id": order.destination_store_id,
            "updated_at": (order.updated_at or order.created_at).isoformat(),
        },
    )
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
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="STATUS_UPDATE",
        payload={
            "id": order.id,
            "status": order.status.value,
            "dispatched_at": order.dispatched_at.isoformat() if order.dispatched_at else None,
        },
    )
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
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="STATUS_UPDATE",
        payload={
            "id": order.id,
            "status": order.status.value,
            "received_at": order.received_at.isoformat() if order.received_at else None,
        },
    )
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
    enqueue_sync_outbox(
        db,
        entity_type="transfer_order",
        entity_id=str(order.id),
        operation="STATUS_UPDATE",
        payload={
            "id": order.id,
            "status": order.status.value,
            "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
        },
    )
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


def list_purchase_orders(
    db: Session, *, store_id: int | None = None, limit: int = 50
) -> list[models.PurchaseOrder]:
    statement = (
        select(models.PurchaseOrder)
        .options(
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.returns),
        )
        .order_by(models.PurchaseOrder.created_at.desc())
        .limit(limit)
    )
    if store_id is not None:
        statement = statement.where(models.PurchaseOrder.store_id == store_id)
    return list(db.scalars(statement).unique())


def get_purchase_order(db: Session, order_id: int) -> models.PurchaseOrder:
    statement = (
        select(models.PurchaseOrder)
        .where(models.PurchaseOrder.id == order_id)
        .options(
            joinedload(models.PurchaseOrder.items),
            joinedload(models.PurchaseOrder.returns),
        )
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("purchase_not_found") from exc


def create_purchase_order(
    db: Session,
    payload: schemas.PurchaseOrderCreate,
    *,
    created_by_id: int | None = None,
) -> models.PurchaseOrder:
    if not payload.items:
        raise ValueError("purchase_items_required")

    get_store(db, payload.store_id)

    order = models.PurchaseOrder(
        store_id=payload.store_id,
        supplier=payload.supplier,
        notes=payload.notes,
        created_by_id=created_by_id,
    )
    db.add(order)
    db.flush()

    for item in payload.items:
        if item.quantity_ordered <= 0:
            raise ValueError("purchase_invalid_quantity")
        if item.unit_cost < 0:
            raise ValueError("purchase_invalid_quantity")

        device = get_device(db, payload.store_id, item.device_id)
        order_item = models.PurchaseOrderItem(
            purchase_order_id=order.id,
            device_id=device.id,
            quantity_ordered=item.quantity_ordered,
            unit_cost=_to_decimal(item.unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )
        db.add(order_item)

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="purchase_order_created",
        entity_type="purchase_order",
        entity_id=str(order.id),
        performed_by_id=created_by_id,
        details=json.dumps({"store_id": order.store_id, "supplier": order.supplier}),
    )
    db.commit()
    db.refresh(order)
    enqueue_sync_outbox(
        db,
        entity_type="purchase_order",
        entity_id=str(order.id),
        operation="UPSERT",
        payload={
            "id": order.id,
            "status": order.status.value,
            "store_id": order.store_id,
            "supplier": order.supplier,
            "created_at": order.created_at.isoformat(),
        },
    )
    return order


def receive_purchase_order(
    db: Session,
    order_id: int,
    payload: schemas.PurchaseReceiveRequest,
    *,
    received_by_id: int,
    reason: str | None = None,
) -> models.PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order.status in {models.PurchaseStatus.CANCELADA, models.PurchaseStatus.COMPLETADA}:
        raise ValueError("purchase_not_receivable")
    if not payload.items:
        raise ValueError("purchase_items_required")

    items_by_device = {item.device_id: item for item in order.items}
    reception_details: dict[str, int] = {}

    for receive_item in payload.items:
        order_item = items_by_device.get(receive_item.device_id)
        if order_item is None:
            raise LookupError("purchase_item_not_found")
        pending = order_item.quantity_ordered - order_item.quantity_received
        if receive_item.quantity <= 0 or receive_item.quantity > pending:
            raise ValueError("purchase_invalid_quantity")

        order_item.quantity_received += receive_item.quantity

        device = get_device(db, order.store_id, order_item.device_id)
        current_quantity = device.quantity
        new_quantity = current_quantity + receive_item.quantity
        current_cost_total = _to_decimal(device.costo_unitario) * _to_decimal(current_quantity)
        incoming_cost_total = _to_decimal(order_item.unit_cost) * _to_decimal(receive_item.quantity)
        divisor = _to_decimal(new_quantity or 1)
        average_cost = (current_cost_total + incoming_cost_total) / divisor
        device.quantity = new_quantity
        device.costo_unitario = average_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        _recalculate_sale_price(device)

        db.add(
            models.InventoryMovement(
                store_id=order.store_id,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=receive_item.quantity,
                reason=reason,
                performed_by_id=received_by_id,
            )
        )
        reception_details[str(device.id)] = receive_item.quantity

    if all(item.quantity_received == item.quantity_ordered for item in order.items):
        order.status = models.PurchaseStatus.COMPLETADA
        order.closed_at = datetime.utcnow()
    else:
        order.status = models.PurchaseStatus.PARCIAL

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="purchase_order_received",
        entity_type="purchase_order",
        entity_id=str(order.id),
        performed_by_id=received_by_id,
        details=json.dumps({"items": reception_details, "status": order.status.value}),
    )
    db.commit()
    db.refresh(order)
    enqueue_sync_outbox(
        db,
        entity_type="purchase_order",
        entity_id=str(order.id),
        operation="STATUS_UPDATE",
        payload={
            "id": order.id,
            "status": order.status.value,
            "closed_at": order.closed_at.isoformat() if order.closed_at else None,
        },
    )
    return order


def cancel_purchase_order(
    db: Session,
    order_id: int,
    *,
    cancelled_by_id: int,
    reason: str | None = None,
) -> models.PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order.status in {models.PurchaseStatus.CANCELADA, models.PurchaseStatus.COMPLETADA}:
        raise ValueError("purchase_not_cancellable")

    order.status = models.PurchaseStatus.CANCELADA
    order.closed_at = datetime.utcnow()
    if reason:
        order.notes = (order.notes or "") + f" | Cancelación: {reason}" if order.notes else reason

    db.commit()
    db.refresh(order)

    _log_action(
        db,
        action="purchase_order_cancelled",
        entity_type="purchase_order",
        entity_id=str(order.id),
        performed_by_id=cancelled_by_id,
        details=json.dumps({"status": order.status.value, "reason": reason}),
    )
    db.commit()
    db.refresh(order)
    enqueue_sync_outbox(
        db,
        entity_type="purchase_order",
        entity_id=str(order.id),
        operation="STATUS_UPDATE",
        payload={
            "id": order.id,
            "status": order.status.value,
            "closed_at": order.closed_at.isoformat() if order.closed_at else None,
            "reason": reason,
        },
    )
    return order


def register_purchase_return(
    db: Session,
    order_id: int,
    payload: schemas.PurchaseReturnCreate,
    *,
    processed_by_id: int,
    reason: str | None = None,
) -> models.PurchaseReturn:
    order = get_purchase_order(db, order_id)
    order_item = next((item for item in order.items if item.device_id == payload.device_id), None)
    if order_item is None:
        raise LookupError("purchase_item_not_found")
    if payload.quantity <= 0:
        raise ValueError("purchase_invalid_quantity")

    received_total = order_item.quantity_received
    returned_total = sum(ret.quantity for ret in order.returns if ret.device_id == payload.device_id)
    if payload.quantity > received_total - returned_total:
        raise ValueError("purchase_return_exceeds_received")

    device = get_device(db, order.store_id, payload.device_id)
    if device.quantity < payload.quantity:
        raise ValueError("purchase_return_insufficient_stock")
    device.quantity -= payload.quantity

    db.add(
        models.InventoryMovement(
            store_id=order.store_id,
            device_id=device.id,
            movement_type=models.MovementType.OUT,
            quantity=payload.quantity,
            reason=payload.reason or reason,
            performed_by_id=processed_by_id,
        )
    )

    purchase_return = models.PurchaseReturn(
        purchase_order_id=order.id,
        device_id=device.id,
        quantity=payload.quantity,
        reason=payload.reason,
        processed_by_id=processed_by_id,
    )
    db.add(purchase_return)
    db.commit()
    db.refresh(purchase_return)

    _log_action(
        db,
        action="purchase_return_registered",
        entity_type="purchase_order",
        entity_id=str(order.id),
        performed_by_id=processed_by_id,
        details=json.dumps({"device_id": payload.device_id, "quantity": payload.quantity}),
    )
    db.commit()
    db.refresh(order)
    enqueue_sync_outbox(
        db,
        entity_type="purchase_order",
        entity_id=str(order.id),
        operation="RETURN",
        payload={
            "id": order.id,
            "device_id": payload.device_id,
            "quantity": payload.quantity,
            "created_at": purchase_return.created_at.isoformat(),
        },
    )
    return purchase_return


def list_sales(db: Session, *, store_id: int | None = None, limit: int = 50) -> list[models.Sale]:
    statement = (
        select(models.Sale)
        .options(joinedload(models.Sale.items), joinedload(models.Sale.returns))
        .order_by(models.Sale.created_at.desc())
        .limit(limit)
    )
    if store_id is not None:
        statement = statement.where(models.Sale.store_id == store_id)
    return list(db.scalars(statement).unique())


def get_sale(db: Session, sale_id: int) -> models.Sale:
    statement = (
        select(models.Sale)
        .where(models.Sale.id == sale_id)
        .options(joinedload(models.Sale.items), joinedload(models.Sale.returns))
    )
    try:
        return db.scalars(statement).unique().one()
    except NoResultFound as exc:
        raise LookupError("sale_not_found") from exc


def create_sale(
    db: Session,
    payload: schemas.SaleCreate,
    *,
    performed_by_id: int,
    reason: str | None = None,
) -> models.Sale:
    if not payload.items:
        raise ValueError("sale_items_required")

    get_store(db, payload.store_id)

    sale = models.Sale(
        store_id=payload.store_id,
        customer_name=payload.customer_name,
        payment_method=models.PaymentMethod(payload.payment_method),
        discount_percent=_to_decimal(payload.discount_percent or 0),
        notes=payload.notes,
        performed_by_id=performed_by_id,
    )
    db.add(sale)
    db.flush()

    gross_total = Decimal("0")
    for item in payload.items:
        if item.quantity <= 0:
            raise ValueError("sale_invalid_quantity")
        device = get_device(db, payload.store_id, item.device_id)
        if device.quantity < item.quantity:
            raise ValueError("sale_insufficient_stock")

        line_unit_price = _to_decimal(device.unit_price)
        line_total = line_unit_price * _to_decimal(item.quantity)
        gross_total += line_total

        device.quantity -= item.quantity

        sale_item = models.SaleItem(
            sale_id=sale.id,
            device_id=device.id,
            quantity=item.quantity,
            unit_price=line_unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total_line=line_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )
        db.add(sale_item)

        db.add(
            models.InventoryMovement(
                store_id=payload.store_id,
                device_id=device.id,
                movement_type=models.MovementType.OUT,
                quantity=item.quantity,
                reason=reason,
                performed_by_id=performed_by_id,
            )
        )

    discount_percent = sale.discount_percent / Decimal("100")
    discount_amount = (gross_total * discount_percent).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sale.total_amount = (gross_total - discount_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    db.commit()
    db.refresh(sale)

    _log_action(
        db,
        action="sale_registered",
        entity_type="sale",
        entity_id=str(sale.id),
        performed_by_id=performed_by_id,
        details=json.dumps({"store_id": sale.store_id, "total_amount": float(sale.total_amount)}),
    )
    db.commit()
    db.refresh(sale)
    enqueue_sync_outbox(
        db,
        entity_type="sale",
        entity_id=str(sale.id),
        operation="UPSERT",
        payload={
            "id": sale.id,
            "store_id": sale.store_id,
            "total_amount": float(sale.total_amount),
            "created_at": sale.created_at.isoformat(),
        },
    )
    return sale


def register_sale_return(
    db: Session,
    payload: schemas.SaleReturnCreate,
    *,
    processed_by_id: int,
    reason: str | None = None,
) -> list[models.SaleReturn]:
    sale = get_sale(db, payload.sale_id)
    if not payload.items:
        raise ValueError("sale_return_items_required")

    returns: list[models.SaleReturn] = []
    items_by_device = {item.device_id: item for item in sale.items}

    for item in payload.items:
        sale_item = items_by_device.get(item.device_id)
        if sale_item is None:
            raise LookupError("sale_item_not_found")
        if item.quantity <= 0:
            raise ValueError("sale_return_invalid_quantity")

        returned_total = sum(
            existing.quantity for existing in sale.returns if existing.device_id == item.device_id
        )
        if item.quantity > sale_item.quantity - returned_total:
            raise ValueError("sale_return_invalid_quantity")

        device = get_device(db, sale.store_id, item.device_id)
        device.quantity += item.quantity

        sale_return = models.SaleReturn(
            sale_id=sale.id,
            device_id=item.device_id,
            quantity=item.quantity,
            reason=item.reason,
            processed_by_id=processed_by_id,
        )
        db.add(sale_return)
        returns.append(sale_return)

        db.add(
            models.InventoryMovement(
                store_id=sale.store_id,
                device_id=item.device_id,
                movement_type=models.MovementType.IN,
                quantity=item.quantity,
                reason=item.reason or reason,
                performed_by_id=processed_by_id,
            )
        )

    db.commit()
    for sale_return in returns:
        db.refresh(sale_return)

    _log_action(
        db,
        action="sale_return_registered",
        entity_type="sale",
        entity_id=str(sale.id),
        performed_by_id=processed_by_id,
        details=json.dumps({"items": [item.model_dump() for item in payload.items]}),
    )
    db.commit()
    enqueue_sync_outbox(
        db,
        entity_type="sale",
        entity_id=str(sale.id),
        operation="RETURN",
        payload={
            "id": sale.id,
            "items": [item.model_dump() for item in payload.items],
            "processed_at": datetime.utcnow().isoformat(),
        },
    )
    return returns


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
