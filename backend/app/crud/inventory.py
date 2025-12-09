"""Operaciones CRUD para el módulo de Inventario (Movimientos, Reservas)."""
from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..core.roles import ADMIN, GERENTE
from ..core.transactions import flush_session, transactional_session
from ..services import inventory_accounting, inventory_audit
from ..utils import audit_trail as audit_trail_utils
from ..utils.cache import TTLCache
from ..config import settings
from ..core.settings import inventory_alert_settings
from .audit import get_last_audit_entries
from .audit import log_audit_event as _log_action
from .sync import enqueue_sync_outbox
from .common import to_decimal
from .devices import _recalculate_sale_price, get_device
from .stores import get_store, recalculate_store_inventory_value
from .users import get_user
from .warehouses import get_warehouse


_INVENTORY_MOVEMENTS_CACHE: TTLCache[schemas.InventoryMovementsReport] = TTLCache(
    ttl_seconds=60.0
)


def invalidate_inventory_movements_cache() -> None:
    """Limpia la caché de reportes de movimientos de inventario."""

    _INVENTORY_MOVEMENTS_CACHE.clear()


def _inventory_movements_report_cache_key(
    store_filter: set[int] | None,
    start_dt: datetime,
    end_dt: datetime,
    movement_type: models.MovementType | None,
    limit: int | None,
    offset: int,
) -> tuple[tuple[int, ...], str, str, str | None, int | None, int]:
    store_key = tuple(sorted(store_filter)) if store_filter else tuple()
    movement_key = movement_type.value if movement_type else None
    return (
        store_key,
        start_dt.isoformat(),
        end_dt.isoformat(),
        movement_key,
        limit,
        offset,
    )


def _normalize_store_ids(store_ids: Iterable[int] | None) -> set[int] | None:
    if store_ids is None:
        return None
    return {store_id for store_id in store_ids}


def _normalize_date_range(
    date_from: date | datetime | None,
    date_to: date | datetime | None,
) -> tuple[datetime, datetime]:
    if date_from is None:
        start_dt = datetime.min
    elif isinstance(date_from, datetime):
        start_dt = date_from
    else:
        start_dt = datetime.combine(date_from, datetime.min.time())

    if date_to is None:
        end_dt = datetime.max
    elif isinstance(date_to, datetime):
        end_dt = date_to
    else:
        end_dt = datetime.combine(date_to, datetime.max.time())

    return start_dt, end_dt


def _device_value(device: models.Device) -> Decimal:
    if device.unit_price and device.unit_price > 0:
        return to_decimal(device.unit_price) * device.quantity
    if device.costo_unitario and device.costo_unitario > 0:
        return to_decimal(device.costo_unitario) * device.quantity
    return Decimal("0.00")


def _movement_value(movement: models.InventoryMovement) -> Decimal:
    if movement.unit_cost is not None:
        return to_decimal(movement.unit_cost) * movement.quantity
    return Decimal("0.00")


def _hydrate_movement_references(
    db: Session, movements: Sequence[models.InventoryMovement]
) -> None:
    """Asocia los metadatos de referencia a los movimientos recuperados."""

    movement_ids = [
        movement.id for movement in movements if movement.id is not None]
    if not movement_ids:
        return

    str_ids = [str(movement_id) for movement_id in movement_ids]
    statement = (
        select(models.AuditLog)
        .where(
            models.AuditLog.entity_type == "inventory_movement",
            models.AuditLog.action == "inventory_movement_reference",
            models.AuditLog.entity_id.in_(str_ids),
        )
        .order_by(models.AuditLog.created_at.desc())
    )
    logs = list(db.scalars(statement))
    reference_map: dict[str, tuple[str | None, str | None]] = {}
    for log in logs:
        if log.entity_id in reference_map:
            continue
        data: dict[str, object]
        try:
            data = json.loads(log.details or "{}")
        except json.JSONDecodeError:
            data = {}
        reference_map[log.entity_id] = (
            str(data.get("reference_type")) if data.get(
                "reference_type") else None,
            str(data.get("reference_id")) if data.get(
                "reference_id") else None,
        )

    for movement in movements:
        reference = reference_map.get(str(movement.id))
        if not reference:
            continue
        reference_type, reference_id = reference
        if reference_type:
            setattr(movement, "reference_type", reference_type)
        if reference_id:
            setattr(movement, "reference_id", reference_id)


def _quantize_currency(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calculate_weighted_average_cost(
    current_qty: int,
    current_cost: Decimal,
    added_qty: int,
    added_cost: Decimal,
) -> Decimal:
    total_qty = Decimal(current_qty) + Decimal(added_qty)
    if total_qty <= Decimal("0"):
        return Decimal("0.00")
    total_value = (Decimal(current_qty) * current_cost) + (
        Decimal(added_qty) * added_cost
    )
    return total_value / total_qty


def _ensure_adjustment_authorized(db: Session, performed_by_id: int | None) -> None:
    if performed_by_id is None:
        # Permite ejecuciones automatizadas (importaciones, sincronizaciones) manteniendo
        # compatibilidad con flujos existentes donde no hay un usuario autenticado.
        return
    user = get_user(db, performed_by_id)
    role_names = {
        membership.role.name for membership in user.roles if membership.role}
    if not {ADMIN, GERENTE}.intersection(role_names):
        raise PermissionError("movement_adjust_requires_authorized_user")


def _normalize_movement_comment(comment: str | None) -> str:
    if comment is None:
        normalized = "Movimiento inventario"
    else:
        normalized = comment.strip() or "Movimiento inventario"
    if len(normalized) < 5:
        normalized = f"{normalized} Kardex".strip()
    if len(normalized) < 5:
        normalized = "Movimiento inventario"
    return normalized[:255]


def _record_inventory_movement_reference(
    db: Session,
    *,
    movement: models.InventoryMovement,
    reference_type: str | None,
    reference_id: str | None,
    performed_by_id: int | None,
) -> None:
    """Registra la relación del movimiento con su operación original."""

    if not reference_type or not reference_id or movement.id is None:
        return

    normalized_type = reference_type.strip().lower()
    normalized_id = str(reference_id).strip()
    if not normalized_type or not normalized_id:
        return

    if len(normalized_type) > 40:
        normalized_type = normalized_type[:40]
    if len(normalized_id) > 120:
        normalized_id = normalized_id[:120]

    details = json.dumps(
        {"reference_type": normalized_type, "reference_id": normalized_id}
    )
    _log_action(
        db,
        action="inventory_movement_reference",
        entity_type="inventory_movement",
        entity_id=str(movement.id),
        performed_by_id=performed_by_id,
        details=details,
    )
    setattr(movement, "reference_type", normalized_type)
    setattr(movement, "reference_id", normalized_id)


def _lock_device_inventory_row(
    db: Session, *, store_id: int, device_id: int
) -> None:
    """Aplica un bloqueo de fila sobre el dispositivo antes de modificar stock."""

    db.execute(
        select(models.Device.id)
        .where(
            models.Device.id == device_id,
            models.Device.store_id == store_id,
        )
        .with_for_update()
    )


def create_inventory_movement(
    db: Session,
    store_id: int,
    payload: schemas.MovementCreate,
    *,
    performed_by_id: int | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> models.InventoryMovement:
    store = get_store(db, store_id)
    # Nota: permitimos sucursal_destino_id diferente para devoluciones entre tiendas
    # if (
    #     payload.sucursal_destino_id is not None
    #     and payload.sucursal_destino_id != store_id
    # ):
    #     raise ValueError("invalid_destination_store")

    source_store_id = payload.sucursal_origen_id
    destination_store_id = payload.sucursal_destino_id or store_id

    device = get_device(db, store_id, payload.producto_id)

    destination_warehouse_id = payload.almacen_destino_id or device.warehouse_id
    source_warehouse_id = payload.almacen_origen_id or device.warehouse_id
    if destination_warehouse_id is not None:
        # Validar contra la tienda destino si existe, sino contra la tienda actual
        warehouse_store_id = destination_store_id if destination_store_id else store_id
        get_warehouse(db, destination_warehouse_id,
                      store_id=warehouse_store_id)
    if source_warehouse_id is not None:
        get_warehouse(db, source_warehouse_id,
                      store_id=source_store_id or store_id)

    if source_store_id is not None:
        get_store(db, source_store_id)

    if (
        reference_type is None
        and payload.tipo_movimiento == models.MovementType.ADJUST
        and device.id is not None
    ):
        reference_type = "manual_adjustment"
        reference_id = str(device.id)

    needs_decrement_lock = payload.tipo_movimiento == models.MovementType.OUT or (
        payload.tipo_movimiento == models.MovementType.ADJUST
        and device.quantity > payload.cantidad
    )

    with transactional_session(db):
        if needs_decrement_lock:
            _lock_device_inventory_row(
                db, store_id=store_id, device_id=device.id
            )
            db.refresh(device)

        previous_quantity = device.quantity
        previous_cost = to_decimal(device.costo_unitario)
        previous_sale_price = device.unit_price

        if (
            payload.tipo_movimiento == models.MovementType.OUT
            and device.quantity < payload.cantidad
        ):
            raise ValueError("insufficient_stock")

        movement_unit_cost: Decimal | None = None
        stock_move_type: models.StockMoveType | None = None
        stock_move_quantity: Decimal | None = None
        stock_move_branch_id: int | None = None
        ledger_quantity: Decimal | None = None
        ledger_branch_id: int | None = None
        ledger_unit_cost: Decimal | None = None

        if payload.tipo_movimiento == models.MovementType.IN:
            if payload.unit_cost is not None:
                incoming_cost = to_decimal(payload.unit_cost)
            elif previous_cost > Decimal("0"):
                incoming_cost = previous_cost
            elif device.unit_price is not None and device.unit_price > Decimal("0"):
                incoming_cost = to_decimal(device.unit_price)
            else:
                incoming_cost = previous_cost
            device.quantity += payload.cantidad
            average_cost = _calculate_weighted_average_cost(
                previous_quantity,
                previous_cost,
                payload.cantidad,
                incoming_cost,
            )
            device.costo_unitario = _quantize_currency(average_cost)
            movement_unit_cost = _quantize_currency(incoming_cost)
            _recalculate_sale_price(device)
            if (
                payload.unit_cost is None
                and previous_sale_price is not None
                and previous_sale_price > Decimal("0")
            ):
                device.unit_price = to_decimal(previous_sale_price)
                device.precio_venta = device.unit_price
            stock_move_type = models.StockMoveType.IN  # // [PACK30-31-BACKEND]
            stock_move_quantity = to_decimal(payload.cantidad)
            stock_move_branch_id = store_id
        elif payload.tipo_movimiento == models.MovementType.OUT:
            branch_for_cost = source_store_id or store_id
            computed_cost = inventory_accounting.compute_unit_cost(
                db,
                product_id=device.id,
                branch_id=branch_for_cost,
                quantity_out=payload.cantidad,
            )
            movement_unit_cost = _quantize_currency(computed_cost)
            device.quantity -= payload.cantidad
            if source_store_id is None:
                source_store_id = store_id
            if device.quantity <= 0:
                device.costo_unitario = Decimal("0.00")
            stock_move_type = models.StockMoveType.OUT
            stock_move_quantity = to_decimal(payload.cantidad)
            stock_move_branch_id = branch_for_cost
            ledger_quantity = to_decimal(payload.cantidad)
            ledger_branch_id = branch_for_cost
            ledger_unit_cost = movement_unit_cost
        elif payload.tipo_movimiento == models.MovementType.ADJUST:
            _ensure_adjustment_authorized(db, performed_by_id)
            if source_store_id is None:
                source_store_id = store_id
            adjustment_difference = payload.cantidad - previous_quantity
            adjustment_decimal = to_decimal(adjustment_difference)
            branch_for_cost = store_id
            if (device.imei or device.serial) and (
                device.estado and device.estado.lower() == "vendido"
            ):
                raise ValueError("adjustment_device_already_sold")
            if adjustment_difference < 0 and abs(adjustment_difference) > previous_quantity:
                raise ValueError("adjustment_insufficient_stock")
            if adjustment_difference < 0:
                removal_qty = abs(adjustment_difference)
                computed_cost = inventory_accounting.compute_unit_cost(
                    db,
                    product_id=device.id,
                    branch_id=branch_for_cost,
                    quantity_out=removal_qty,
                )
                movement_unit_cost = _quantize_currency(computed_cost)
                ledger_quantity = to_decimal(removal_qty)
                ledger_branch_id = branch_for_cost
                ledger_unit_cost = movement_unit_cost
            elif adjustment_difference > 0:
                if payload.unit_cost is not None:
                    incoming_cost = to_decimal(payload.unit_cost)
                elif previous_cost > Decimal("0"):
                    incoming_cost = previous_cost
                elif (
                    device.unit_price is not None
                    and device.unit_price > Decimal("0")
                ):
                    incoming_cost = to_decimal(device.unit_price)
                else:
                    incoming_cost = previous_cost

                average_cost = _calculate_weighted_average_cost(
                    previous_quantity,
                    previous_cost,
                    adjustment_difference,
                    incoming_cost,
                )
                device.costo_unitario = _quantize_currency(average_cost)
                movement_unit_cost = _quantize_currency(incoming_cost)
                _recalculate_sale_price(device)
            elif payload.unit_cost is not None and payload.cantidad > 0:
                updated_cost = to_decimal(payload.unit_cost)
                device.costo_unitario = _quantize_currency(updated_cost)
                movement_unit_cost = _quantize_currency(updated_cost)
                _recalculate_sale_price(device)
            else:
                movement_unit_cost = (
                    _quantize_currency(previous_cost)
                    if previous_cost > Decimal("0")
                    else Decimal("0.00")
                )
            device.quantity = payload.cantidad
            if device.quantity <= 0:
                device.costo_unitario = Decimal("0.00")
            stock_move_type = models.StockMoveType.ADJUST
            stock_move_quantity = adjustment_decimal
            stock_move_branch_id = branch_for_cost

        db.add(device)
        db.flush()

        movement = models.InventoryMovement(
            device_id=device.id,
            movement_type=payload.tipo_movimiento,
            quantity=payload.cantidad,
            comment=payload.comentario,
            performed_by_id=performed_by_id,
            source_store_id=source_store_id,
            store_id=destination_store_id,
            source_warehouse_id=source_warehouse_id,
            warehouse_id=destination_warehouse_id,
            unit_cost=movement_unit_cost,
        )
        db.add(movement)
        db.flush()

        _record_inventory_movement_reference(
            db,
            movement=movement,
            reference_type=reference_type,
            reference_id=reference_id,
            performed_by_id=performed_by_id,
        )

        # // [PACK30-31-BACKEND]
        if stock_move_type and stock_move_quantity is not None:
            inventory_accounting.record_stock_move(
                db,
                product_id=device.id,
                branch_id=stock_move_branch_id or store_id,
                move_type=stock_move_type,
                quantity=stock_move_quantity,
                unit_cost=movement_unit_cost or Decimal("0.00"),
                reference_id=f"mov-{movement.id}",
                performed_by_id=performed_by_id,
            )

        total_value = recalculate_store_inventory_value(db, store_id)
        setattr(movement, "store_inventory_value", total_value)

        _log_action(
            db,
            action="inventory_movement",
            entity_type="inventory_movement",
            entity_id=str(movement.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "device_id": device.id,
                    "store_id": store_id,
                    "movement_type": payload.tipo_movimiento.value,
                    "quantity": payload.cantidad,
                    "comment": movement.comment,
                }
            ),
        )

        # Registrar también sobre la entidad de dispositivo para trazabilidad en bitácora.
        _log_action(
            db,
            action="inventory_movement",
            entity_type="device",
            entity_id=str(device.id),
            performed_by_id=performed_by_id,
            details=json.dumps(
                {
                    "movement_id": movement.id,
                    "store_id": store_id,
                    "movement_type": payload.tipo_movimiento.value,
                    "quantity": payload.cantidad,
                    "comment": movement.comment,
                }
            ),
        )

        new_quantity = device.quantity
        quantity_delta = new_quantity - previous_quantity
        variance_threshold = max(
            1,
            inventory_alert_settings.adjustment_variance_threshold,
            settings.inventory_adjustment_variance_threshold,
        )

        if (
            payload.tipo_movimiento == models.MovementType.ADJUST
            and quantity_delta != 0
        ):
            adjustment_reason = (
                f", motivo={movement.comment}" if movement.comment else ""
            )
            if abs(quantity_delta) >= variance_threshold:
                _log_action(
                    db,
                    action="inventory_adjustment_alert",
                    entity_type="device",
                    entity_id=str(device.id),
                    performed_by_id=performed_by_id,
                    details=(
                        "Ajuste manual registrado; inconsistencia detectada"
                        f" en la sucursal {store.name}. stock_previo={previous_quantity}, "
                        f"stock_actual={new_quantity}, variacion={quantity_delta:+d}"
                        f", umbral={variance_threshold}{adjustment_reason}"
                    ),
                )

        if new_quantity <= settings.inventory_low_stock_threshold:
            _log_action(
                db,
                action="inventory_low_stock_alert",
                entity_type="device",
                entity_id=str(device.id),
                performed_by_id=performed_by_id,
                details=(
                    "Stock bajo detectado"
                    f" en la sucursal {store.name}. dispositivo={device.sku}, "
                    f"stock_actual={new_quantity}, umbral={settings.inventory_low_stock_threshold}"
                ),
            )

        enqueue_sync_outbox(
            db,
            entity_type="inventory",
            entity_id=str(movement.id),
            operation="UPSERT",
            payload={
                "id": movement.id,
                "store_id": store_id,
                "device_id": device.id,
                "movement_type": payload.tipo_movimiento.value,
                "quantity": payload.cantidad,
                "comment": movement.comment,
                "unit_cost": float(movement_unit_cost or Decimal("0")),
            },
        )

        return movement


def register_inventory_movement(
    db: Session,
    *,
    store_id: int,
    device_id: int,
    movement_type: models.MovementType,
    quantity: int,
    comment: str | None,
    performed_by_id: int | None,
    source_store_id: int | None = None,
    destination_store_id: int | None = None,
    source_warehouse_id: int | None = None,
    warehouse_id: int | None = None,
    unit_cost: Decimal | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> models.InventoryMovement:
    normalized_comment = _normalize_movement_comment(comment)
    movement_payload = schemas.MovementCreate(
        producto_id=device_id,
        tipo_movimiento=movement_type,
        cantidad=quantity,
        comentario=normalized_comment,
        sucursal_origen_id=source_store_id,
        sucursal_destino_id=destination_store_id,
        almacen_origen_id=source_warehouse_id,
        almacen_destino_id=warehouse_id,
        unit_cost=unit_cost,
    )
    return create_inventory_movement(
        db,
        store_id,
        movement_payload,
        performed_by_id=performed_by_id,
        reference_type=reference_type,
        reference_id=reference_id,
    )


def list_inventory_summary(
    db: Session, *, limit: int | None = None, offset: int = 0
) -> list[models.Store]:
    statement = select(models.Store).options(joinedload(models.Store.devices)).order_by(
        models.Store.name.asc()
    )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def list_incomplete_devices(
    db: Session,
    *,
    store_id: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[models.Device]:
    """Devuelve dispositivos marcados como incompletos, con opción a filtrar por sucursal."""

    statement = (
        select(models.Device)
        .options(joinedload(models.Device.store))
        .where(models.Device.completo.is_(False))
        .order_by(models.Device.id.desc())
    )

    if store_id is not None:
        statement = statement.where(models.Device.store_id == store_id)
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)

    return list(db.scalars(statement).unique())


def count_incomplete_devices(db: Session, *, store_id: int | None = None) -> int:
    """Cuenta los dispositivos incompletos para habilitar paginación."""

    statement = (
        select(func.count())
        .select_from(models.Device)
        .where(models.Device.completo.is_(False))
    )
    if store_id is not None:
        statement = statement.where(models.Device.store_id == store_id)

    return int(db.scalar(statement) or 0)


def list_devices_below_minimum_thresholds(
    db: Session, *, store_id: int | None = None
) -> list[dict[str, object]]:
    """Devuelve los dispositivos que están bajo el stock mínimo o punto de reorden."""

    query = (
        select(
            models.Device.id.label("device_id"),
            models.Device.store_id,
            models.Store.name.label("store_name"),
            models.Device.sku,
            models.Device.name,
            models.Device.quantity,
            models.Device.unit_price,
            models.Device.minimum_stock,
            models.Device.reorder_point,
        )
        .join(models.Store, models.Device.store_id == models.Store.id)
        .where(
            or_(
                models.Device.quantity <= models.Device.minimum_stock,
                models.Device.quantity <= models.Device.reorder_point,
            )
        )
    )

    if store_id:
        query = query.where(models.Device.store_id == store_id)

    rows = db.execute(query.order_by(
        models.Device.quantity, models.Device.sku)).mappings()
    return [dict(row) for row in rows]


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
                        "minimum_stock": getattr(device, "minimum_stock", 0) or 0,
                        "reorder_point": getattr(device, "reorder_point", 0) or 0,
                        "inventory_value": _device_value(device),
                    }
                )

    store_metrics.sort(key=lambda item: item["total_value"], reverse=True)
    low_stock.sort(key=lambda item: (item["quantity"], item["name"]))

    sales_stmt = (
        select(models.Sale)
        .options(
            joinedload(models.Sale.items).joinedload(models.SaleItem.device),
            joinedload(models.Sale.store),
            joinedload(models.Sale.customer),
        )
        .order_by(models.Sale.created_at.desc())
    )
    sales = list(db.scalars(sales_stmt).unique())

    repairs_stmt = select(models.RepairOrder)
    repairs = list(db.scalars(repairs_stmt))

    total_sales_amount = Decimal("0")

    return {
        "total_devices": total_devices,
        "total_units": total_units,
        "total_value": total_value,
        "store_metrics": store_metrics,
        "low_stock": low_stock,
        "sales_count": len(sales),
        "repairs_count": len(repairs),
    }


def get_inventory_integrity_report(
    db: Session, *, store_ids: Iterable[int] | None = None
) -> schemas.InventoryIntegrityReport:
    """Devuelve el reporte de integridad entre existencias y movimientos."""

    return inventory_audit.build_inventory_integrity_report(db, store_ids=store_ids)


def get_inventory_current_report(
    db: Session, *, store_ids: Iterable[int] | None = None
) -> schemas.InventoryCurrentReport:
    stores = list_inventory_summary(db)
    store_filter = _normalize_store_ids(store_ids)

    report_stores: list[schemas.InventoryCurrentStore] = []
    total_devices = 0
    total_units = 0
    total_value = Decimal("0")

    for store in stores:
        if store_filter and store.id not in store_filter:
            continue
        device_count = len(store.devices)
        store_units = sum(device.quantity for device in store.devices)
        store_value = sum(_device_value(device) for device in store.devices)

        report_stores.append(
            schemas.InventoryCurrentStore(
                store_id=store.id,
                store_name=store.name,
                device_count=device_count,
                total_units=store_units,
                total_value=store_value,
            )
        )

        total_devices += device_count
        total_units += store_units
        total_value += store_value

    totals = schemas.InventoryTotals(
        stores=len(report_stores),
        devices=total_devices,
        total_units=total_units,
        total_value=total_value,
    )

    return schemas.InventoryCurrentReport(stores=report_stores, totals=totals)


def get_inventory_movements_report(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    movement_type: models.MovementType | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> schemas.InventoryMovementsReport:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)

    cache_key = _inventory_movements_report_cache_key(
        store_filter, start_dt, end_dt, movement_type, limit, offset
    )
    cached_report = _INVENTORY_MOVEMENTS_CACHE.get(cache_key)
    if cached_report is not None:
        return cached_report.model_copy(deep=True)

    movement_stmt = (
        select(models.InventoryMovement)
        .options(
            joinedload(models.InventoryMovement.store),
            joinedload(models.InventoryMovement.source_store),
            joinedload(models.InventoryMovement.device),
            joinedload(models.InventoryMovement.performed_by),
        )
        .order_by(models.InventoryMovement.created_at.desc())
    )

    if store_filter:
        movement_stmt = movement_stmt.where(
            models.InventoryMovement.store_id.in_(store_filter)
        )
    movement_stmt = movement_stmt.where(
        models.InventoryMovement.created_at >= start_dt
    )
    movement_stmt = movement_stmt.where(
        models.InventoryMovement.created_at <= end_dt
    )
    if movement_type is not None:
        movement_stmt = movement_stmt.where(
            models.InventoryMovement.movement_type == movement_type
        )

    if offset:
        movement_stmt = movement_stmt.offset(offset)
    if limit is not None:
        movement_stmt = movement_stmt.limit(limit)

    movements = list(db.scalars(movement_stmt).unique())

    _hydrate_movement_references(db, movements)

    movement_ids = [
        movement.id for movement in movements if movement.id is not None]
    audit_logs = get_last_audit_entries(
        db,
        entity_type="inventory_movement",
        entity_ids=movement_ids,
    )
    audit_trails = {
        key: audit_trail_utils.to_audit_trail(log)
        for key, log in audit_logs.items()
    }

    totals_by_type: dict[models.MovementType, dict[str, Decimal | int]] = {}
    period_map: dict[tuple[date, models.MovementType],
                     dict[str, Decimal | int]] = {}
    total_units = 0
    total_value = Decimal("0")
    report_entries: list[schemas.MovementReportEntry] = []

    for movement in movements:
        value = _movement_value(movement)
        total_units += movement.quantity
        total_value += value

        type_data = totals_by_type.setdefault(
            movement.movement_type,
            {"quantity": 0, "value": Decimal("0")},
        )
        type_data["quantity"] = int(type_data["quantity"]) + movement.quantity
        type_data["value"] = to_decimal(type_data["value"]) + value

        period_key = (movement.created_at.date(), movement.movement_type)
        period_data = period_map.setdefault(
            period_key,
            {"quantity": 0, "value": Decimal("0")},
        )
        period_data["quantity"] = int(
            period_data["quantity"]) + movement.quantity
        period_data["value"] = to_decimal(period_data["value"]) + value

        report_entries.append(
            schemas.MovementReportEntry(
                id=movement.id,
                tipo_movimiento=movement.movement_type,
                cantidad=movement.quantity,
                valor_total=value,
                sucursal_destino_id=movement.store_id,
                sucursal_destino=movement.tienda_destino,
                sucursal_origen_id=movement.source_store_id,
                sucursal_origen=movement.tienda_origen,
                comentario=movement.comment,
                usuario=movement.usuario,
                referencia_tipo=getattr(movement, "reference_type", None),
                referencia_id=getattr(movement, "reference_id", None),
                fecha=movement.created_at,
                ultima_accion=audit_trails.get(str(movement.id)),
            )
        )

    period_summaries = [
        schemas.MovementPeriodSummary(
            periodo=period,
            tipo_movimiento=movement_type,
            total_cantidad=int(data["quantity"]),
            total_valor=to_decimal(data["value"]),
        )
        for (period, movement_type), data in sorted(period_map.items())
    ]

    summary_by_type = [
        schemas.MovementTypeSummary(
            tipo_movimiento=movement_enum,
            total_cantidad=int(totals_by_type.get(
                movement_enum, {}).get("quantity", 0)),
            total_valor=to_decimal(totals_by_type.get(
                movement_enum, {}).get("value", 0)),
        )
        for movement_enum in models.MovementType
    ]

    resumen = schemas.InventoryMovementsSummary(
        total_movimientos=len(movements),
        total_unidades=total_units,
        total_valor=total_value,
        por_tipo=summary_by_type,
    )

    report = schemas.InventoryMovementsReport(
        resumen=resumen,
        periodos=period_summaries,
        movimientos=report_entries,
    )
    _INVENTORY_MOVEMENTS_CACHE.set(cache_key, report.model_copy(deep=True))
    return report


def get_top_selling_products(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    date_from: date | datetime | None = None,
    date_to: date | datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> schemas.TopProductsReport:
    store_filter = _normalize_store_ids(store_ids)
    start_dt, end_dt = _normalize_date_range(date_from, date_to)

    sold_units = func.sum(models.SaleItem.quantity).label("sold_units")
    total_revenue = func.sum(models.SaleItem.total_line).label("total_revenue")
    estimated_cost = func.sum(
        models.SaleItem.quantity
        * func.coalesce(models.Device.costo_unitario, models.SaleItem.unit_price)
    ).label("total_cost")

    stmt = (
        select(
            models.SaleItem.device_id,
            models.Device.sku,
            models.Device.name.label("device_name"),
            models.Sale.store_id,
            models.Store.name.label("store_name"),
            sold_units,
            total_revenue,
            estimated_cost,
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .where(models.Sale.created_at >= start_dt)
        .where(models.Sale.created_at <= end_dt)
        .group_by(
            models.SaleItem.device_id,
            models.Device.sku,
            models.Device.name,
            models.Sale.store_id,
            models.Store.name,
        )
        .order_by(sold_units.desc(), total_revenue.desc())
        .offset(offset)
        .limit(limit)
    )

    if store_filter:
        stmt = stmt.where(models.Sale.store_id.in_(store_filter))

    rows = list(db.execute(stmt).mappings())

    items: list[schemas.TopProductReportItem] = []
    total_units = 0
    total_income = Decimal("0")

    for row in rows:
        units = int(row["sold_units"] or 0)
        income = to_decimal(row["total_revenue"])
        cost = to_decimal(row["total_cost"])
        margin = income - cost

        items.append(
            schemas.TopProductReportItem(
                device_id=row["device_id"],
                sku=row["sku"],
                nombre=row["device_name"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                unidades_vendidas=units,
                ingresos_totales=income,
                margen_estimado=margin,
            )
        )

        total_units += units
        total_income += income

    return schemas.TopProductsReport(
        items=items,
        total_unidades=total_units,
        total_ingresos=total_income,
    )


def get_inventory_value_report(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    categories: Iterable[str] | None = None,
) -> schemas.InventoryValueReport:
    valuations = inventory_accounting.calculate_inventory_valuation(
        db, store_ids=store_ids, categories=categories
    )

    store_map: dict[int, dict[str, Decimal | str]] = {}

    for entry in valuations:
        store_entry = store_map.setdefault(
            entry.store_id,
            {
                "store_name": entry.store_name,
                "valor_total": Decimal("0"),
                "valor_costo": Decimal("0"),
                "margen_total": Decimal("0"),
            },
        )
        store_entry["valor_total"] = to_decimal(store_entry["valor_total"]) + to_decimal(
            entry.valor_total_producto
        )
        store_entry["valor_costo"] = to_decimal(store_entry["valor_costo"]) + to_decimal(
            entry.valor_costo_producto
        )
        store_entry["margen_total"] = to_decimal(store_entry["margen_total"]) + (
            to_decimal(entry.valor_total_producto) -
            to_decimal(entry.valor_costo_producto)
        )

    stores = [
        schemas.InventoryValueStore(
            store_id=store_id,
            store_name=data["store_name"],
            valor_total=to_decimal(data["valor_total"]),
            valor_costo=to_decimal(data["valor_costo"]),
            margen_total=to_decimal(data["margen_total"]),
        )
        for store_id, data in sorted(store_map.items(), key=lambda item: item[1]["store_name"])
    ]

    total_valor = sum((store.valor_total for store in stores), Decimal("0"))
    total_costo = sum((store.valor_costo for store in stores), Decimal("0"))
    total_margen = sum((store.margen_total for store in stores), Decimal("0"))

    totals = schemas.InventoryValueTotals(
        valor_total=total_valor,
        valor_costo=total_costo,
        margen_total=total_margen,
    )

    return schemas.InventoryValueReport(stores=stores, totals=totals)


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

    movements_stmt = select(models.InventoryMovement).order_by(
        models.InventoryMovement.created_at.desc()
    )
    movements = list(db.scalars(movements_stmt))
    _hydrate_movement_references(db, movements)

    sync_stmt = select(models.SyncSession).order_by(
        models.SyncSession.started_at.desc())
    sync_sessions = list(db.scalars(sync_stmt))

    audit_stmt = select(models.AuditLog).order_by(
        models.AuditLog.created_at.desc())
    audits = list(db.scalars(audit_stmt))

    total_device_records = 0
    total_units = 0
    total_inventory_value = Decimal("0")

    stores_payload: list[dict[str, object]] = []
    for store in stores:
        devices_payload = [
            {
                "id": device.id,
                "sku": device.sku,
                "name": device.name,
                "quantity": device.quantity,
                "store_id": device.store_id,
                "unit_price": float(device.unit_price or Decimal("0")),
                "inventory_value": float(_device_value(device)),
                "imei": device.imei,
                "serial": device.serial,
                "marca": device.marca,
                "modelo": device.modelo,
                "categoria": device.categoria,
                "condicion": device.condicion,
                "color": device.color,
                "capacidad_gb": device.capacidad_gb,
                "capacidad": device.capacidad,
                "estado_comercial": device.estado_comercial.value,
                "estado": device.estado,
                "proveedor": device.proveedor,
                "costo_unitario": float(device.costo_unitario or Decimal("0")),
                "margen_porcentaje": float(device.margen_porcentaje or Decimal("0")),
                "garantia_meses": device.garantia_meses,
                "lote": device.lote,
                "fecha_compra": device.fecha_compra.isoformat()
                if device.fecha_compra
                else None,
                "fecha_ingreso": device.fecha_ingreso.isoformat()
                if device.fecha_ingreso
                else None,
                "ubicacion": device.ubicacion,
                "descripcion": device.descripcion,
                "imagen_url": device.imagen_url,
            }
            for device in store.devices
        ]
        store_units = sum(device.quantity for device in store.devices)
        store_value = to_decimal(store.inventory_value or Decimal("0"))
        total_device_records += len(devices_payload)
        total_units += store_units
        total_inventory_value += store_value

        stores_payload.append(
            {
                "id": store.id,
                "name": store.name,
                "location": store.location,
                "timezone": store.timezone,
                "inventory_value": float(store_value),
                "device_count": len(devices_payload),
                "total_units": store_units,
                "devices": devices_payload,
            }
        )

    integrity_report = inventory_audit.build_inventory_integrity_report(db)

    snapshot = {
        "stores": stores_payload,
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
                "sucursal_destino_id": movement.store_id,
                "sucursal_origen_id": movement.source_store_id,
                "device_id": movement.device_id,
                "movement_type": movement.movement_type.value,
                "quantity": movement.quantity,
                "comentario": movement.comment,
                "usuario_id": movement.performed_by_id,
                "fecha": movement.created_at.isoformat(),
                "costo_unitario": (
                    float(to_decimal(movement.unit_cost))
                    if movement.unit_cost is not None
                    else None
                ),
                "referencia_tipo": getattr(movement, "reference_type", None),
                "referencia_id": getattr(movement, "reference_id", None),
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
        "summary": {
            "store_count": len(stores),
            "device_records": total_device_records,
            "total_units": total_units,
            "inventory_value": float(
                total_inventory_value.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP)
            ),
        },
        "integrity_report": integrity_report.model_dump(mode="json"),
    }
    return snapshot


def create_inventory_import_record(
    db: Session,
    *,
    filename: str,
    columnas_detectadas: dict[str, str | None],
    registros_incompletos: int,
    total_registros: int,
    nuevos: int,
    actualizados: int,
    advertencias: list[str],
    patrones_columnas: dict[str, str],
    duration_seconds: float | None = None,
) -> models.InventoryImportTemp:
    duration_value = None
    if duration_seconds is not None:
        duration_value = Decimal(str(round(duration_seconds, 2)))
    record = models.InventoryImportTemp(
        nombre_archivo=filename,
        columnas_detectadas=columnas_detectadas,
        registros_incompletos=registros_incompletos,
        total_registros=total_registros,
        nuevos=nuevos,
        actualizados=actualizados,
        advertencias=advertencias,
        patrones_columnas=patrones_columnas,
        duracion_segundos=duration_value,
    )
    with transactional_session(db):
        db.add(record)
        flush_session(db)
        db.refresh(record)
    return record


def list_inventory_import_history(
    db: Session, *, limit: int | None = 10, offset: int = 0
) -> list[models.InventoryImportTemp]:
    statement = select(models.InventoryImportTemp).order_by(
        models.InventoryImportTemp.fecha.desc()
    )
    if offset:
        statement = statement.offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement))


def count_inventory_import_history(db: Session) -> int:
    statement = select(func.count()).select_from(models.InventoryImportTemp)
    return int(db.scalar(statement) or 0)


def get_known_import_column_patterns(db: Session) -> dict[str, str]:
    patterns: dict[str, str] = {}
    statement = select(models.InventoryImportTemp.patrones_columnas)
    for mapping in db.scalars(statement):
        if not mapping:
            continue
        for key, value in mapping.items():
            if key not in patterns:
                patterns[key] = value
    return patterns


def list_import_validations(
    db: Session,
    *,
    corregido: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.ImportValidation]:
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    statement = (
        select(models.ImportValidation)
        .order_by(models.ImportValidation.fecha.desc())
        .offset(safe_offset)
        .limit(safe_limit)
    )
    if corregido is not None:
        statement = statement.where(
            models.ImportValidation.corregido == corregido)
    return list(db.scalars(statement))


def _normalize_reservation_reason(reason: str | None) -> str:
    normalized = (reason or "").strip()
    if len(normalized) < 5:
        raise ValueError("reservation_reason_required")
    return normalized[:255]


def _active_reservations_by_device(
    db: Session,
    *,
    store_id: int,
    device_ids: Iterable[int] | None = None,
) -> dict[int, int]:
    ids = set(device_ids or [])
    now = datetime.now(timezone.utc)
    statement = (
        select(
            models.InventoryReservation.device_id,
            func.coalesce(func.sum(models.InventoryReservation.quantity), 0).label(
                "reserved"
            ),
        )
        .where(models.InventoryReservation.store_id == store_id)
        .where(models.InventoryReservation.status == models.InventoryState.RESERVADO)
        .where(models.InventoryReservation.expires_at > now)
        .group_by(models.InventoryReservation.device_id)
    )
    if ids:
        statement = statement.where(
            models.InventoryReservation.device_id.in_(ids))
    rows = db.execute(statement).all()
    reserved_map: dict[int, int] = {}
    for row in rows:
        device_id = int(row.device_id)
        reserved_value = int(row.reserved or 0)
        reserved_map[device_id] = reserved_value
    return reserved_map


def expire_reservations(
    db: Session,
    *,
    store_id: int | None = None,
    device_ids: Iterable[int] | None = None,
) -> int:
    now = datetime.now(timezone.utc)
    ids = set(device_ids or [])
    statement = select(models.InventoryReservation).where(
        models.InventoryReservation.status == models.InventoryState.RESERVADO,
        models.InventoryReservation.expires_at <= now,
    )
    if store_id is not None:
        statement = statement.where(
            models.InventoryReservation.store_id == store_id)
    if ids:
        statement = statement.where(
            models.InventoryReservation.device_id.in_(ids))
    expirations = list(db.scalars(statement).unique())
    if not expirations:
        return 0

    reason = "Expiración automática"
    for reservation in expirations:
        reservation.status = models.InventoryState.EXPIRADO
        reservation.resolution_reason = reservation.resolution_reason or reason
        reservation.resolved_at = now
        reservation.quantity = 0
        if reservation.device and (reservation.device.imei or reservation.device.serial):
            reservation.device.estado = "disponible"
    return len(expirations)


def get_inventory_reservation(
    db: Session, reservation_id: int
) -> models.InventoryReservation:
    reservation = db.get(models.InventoryReservation, reservation_id)
    if reservation is None:
        raise LookupError("reservation_not_found")
    return reservation


def list_inventory_reservations(
    db: Session,
    *,
    store_id: int | None = None,
    device_id: int | None = None,
    status: models.InventoryState | None = None,
    include_expired: bool = False,
) -> list[models.InventoryReservation]:
    statement = (
        select(models.InventoryReservation)
        .options(
            joinedload(models.InventoryReservation.device),
            joinedload(models.InventoryReservation.store),
        )
        .order_by(models.InventoryReservation.created_at.desc())
    )
    now = datetime.now(timezone.utc)
    if store_id is not None:
        statement = statement.where(
            models.InventoryReservation.store_id == store_id)
    if device_id is not None:
        statement = statement.where(
            models.InventoryReservation.device_id == device_id)
    if status is not None:
        statement = statement.where(
            models.InventoryReservation.status == status)
    if not include_expired:
        statement = statement.where(
            or_(
                models.InventoryReservation.status != models.InventoryState.RESERVADO,
                models.InventoryReservation.expires_at > now,
            )
        )
    return list(db.scalars(statement).unique())


def create_reservation(
    db: Session,
    *,
    store_id: int,
    device_id: int,
    quantity: int,
    expires_at: datetime,
    reserved_by_id: int | None,
    reason: str,
) -> models.InventoryReservation:
    if quantity <= 0:
        raise ValueError("reservation_invalid_quantity")
    if expires_at <= datetime.now(timezone.utc):
        raise ValueError("reservation_invalid_expiration")

    normalized_reason = _normalize_reservation_reason(reason)
    store = get_store(db, store_id)
    device = get_device(db, store_id, device_id)

    expire_reservations(db, store_id=store.id, device_ids=[device.id])
    active_reserved = _active_reservations_by_device(
        db, store_id=store.id, device_ids=[device.id]
    ).get(device.id, 0)
    available_quantity = device.quantity - active_reserved
    if available_quantity < quantity:
        raise ValueError("reservation_insufficient_stock")
    if device.imei or device.serial:
        if quantity != 1:
            raise ValueError("reservation_requires_single_unit")
        if device.estado and device.estado.lower() == "vendido":
            raise ValueError("reservation_device_unavailable")

    reservation = models.InventoryReservation(
        store_id=store.id,
        device_id=device.id,
        reserved_by_id=reserved_by_id,
        initial_quantity=quantity,
        quantity=quantity,
        status=models.InventoryState.RESERVADO,
        reason=normalized_reason,
        expires_at=expires_at,
    )

    with transactional_session(db):
        db.add(reservation)
        if device.imei or device.serial:
            device.estado = "reservado"
        flush_session(db)
        db.refresh(reservation)
        details = json.dumps(
            {
                "store_id": store.id,
                "device_id": device.id,
                "quantity": quantity,
                "expires_at": expires_at.isoformat(),
            }
        )
        _log_action(
            db,
            action="inventory_reservation_created",
            entity_type="inventory_reservation",
            entity_id=str(reservation.id),
            performed_by_id=reserved_by_id,
            details=details,
        )
    return reservation


def renew_reservation(
    db: Session,
    reservation_id: int,
    *,
    expires_at: datetime,
    performed_by_id: int | None,
    reason: str,
) -> models.InventoryReservation:
    reservation = get_inventory_reservation(db, reservation_id)
    if reservation.status != models.InventoryState.RESERVADO:
        raise ValueError("reservation_not_active")
    if expires_at <= datetime.now(timezone.utc):
        raise ValueError("reservation_invalid_expiration")

    _ = _normalize_reservation_reason(reason)

    with transactional_session(db):
        reservation.expires_at = expires_at
        reservation.updated_at = datetime.now(timezone.utc)
        flush_session(db)
        details = json.dumps(
            {
                "expires_at": expires_at.isoformat(),
                "reason": reason,
            }
        )
        _log_action(
            db,
            action="inventory_reservation_renewed",
            entity_type="inventory_reservation",
            entity_id=str(reservation.id),
            performed_by_id=performed_by_id,
            details=details,
        )
        db.refresh(reservation)
    return reservation


def release_reservation(
    db: Session,
    reservation_id: int,
    *,
    performed_by_id: int | None,
    reason: str | None = None,
    target_state: models.InventoryState = models.InventoryState.CANCELADO,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> models.InventoryReservation:
    if target_state not in {
        models.InventoryState.CANCELADO,
        models.InventoryState.CONSUMIDO,
    }:
        raise ValueError("reservation_invalid_transition")

    reservation = get_inventory_reservation(db, reservation_id)
    if reservation.status != models.InventoryState.RESERVADO:
        raise ValueError("reservation_not_active")

    normalized_reason = (reason or "").strip() or None
    now = datetime.now(timezone.utc)

    with transactional_session(db):
        reservation.status = target_state
        reservation.resolution_reason = normalized_reason
        reservation.resolved_at = now
        reservation.quantity = 0

        if reservation.device and (reservation.device.imei or reservation.device.serial):
            reservation.device.estado = "disponible"

        flush_session(db)
        details = json.dumps(
            {
                "target_state": target_state.value,
                "reason": normalized_reason,
                "reference_type": reference_type,
                "reference_id": reference_id,
            }
        )
        _log_action(
            db,
            action="inventory_reservation_released",
            entity_type="inventory_reservation",
            entity_id=str(reservation.id),
            performed_by_id=performed_by_id,
            details=details,
        )
        db.refresh(reservation)
    return reservation


def register_inventory_movement(
    db: Session,
    *,
    store_id: int,
    device_id: int,
    movement_type: models.MovementType,
    quantity: int,
    comment: str | None,
    performed_by_id: int | None,
    source_store_id: int | None = None,
    destination_store_id: int | None = None,
    source_warehouse_id: int | None = None,
    warehouse_id: int | None = None,
    unit_cost: Decimal | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> models.InventoryMovement:
    normalized_comment = _normalize_movement_comment(comment)
    movement_payload = schemas.MovementCreate(
        producto_id=device_id,
        tipo_movimiento=movement_type,
        cantidad=quantity,
        comentario=normalized_comment,
        sucursal_origen_id=source_store_id,
        sucursal_destino_id=destination_store_id,
        almacen_origen_id=source_warehouse_id,
        almacen_destino_id=warehouse_id,
        unit_cost=unit_cost,
    )
    return create_inventory_movement(
        db,
        store_id,
        movement_payload,
        performed_by_id=performed_by_id,
        reference_type=reference_type,
        reference_id=reference_id,
    )


__all__ = [
    "build_inventory_snapshot",
    "compute_inventory_metrics",
    "count_inventory_import_history",
    "create_inventory_import_record",
    "create_inventory_movement",
    "create_reservation",
    "expire_reservations",
    "get_inventory_current_report",
    "get_inventory_integrity_report",
    "get_inventory_movements_report",
    "get_inventory_reservation",
    "get_inventory_value_report",
    "get_known_import_column_patterns",
    "get_top_selling_products",
    "invalidate_inventory_movements_cache",
    "list_incomplete_devices",
    "list_devices_below_minimum_thresholds",
    "list_import_validations",
    "list_inventory_import_history",
    "list_inventory_reservations",
    "list_inventory_summary",
    "register_inventory_movement",
    "count_incomplete_devices",
    "release_reservation",
    "renew_reservation",
    "_hydrate_movement_references",
]
