"""Operaciones CRUD para el módulo de Ventas (Sales)."""
from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..core.transactions import flush_session, transactional_session
from ..services.sales import consume_supplier_batch
from .audit import log_audit_event as _log_action
from .common import to_decimal
from .customers import (
    _create_customer_ledger_entry,
    _validate_customer_credit,
    get_customer,
)
from .devices import get_device
from .inventory import (
    _active_reservations_by_device,
    expire_reservations,
    get_inventory_reservation,
    register_inventory_movement,
    release_reservation,
)
from .stores import get_store, recalculate_store_inventory_value
from .sync import enqueue_sync_outbox


def _ensure_device_available_for_sale(
    device: models.Device, quantity: int, *, active_reserved: int = 0
) -> None:
    if quantity <= 0:
        raise ValueError("sale_invalid_quantity")
    effective_stock = device.quantity - active_reserved
    if effective_stock < quantity:
        raise ValueError("sale_insufficient_stock")
    if device.imei or device.serial:
        if device.estado and device.estado.lower() == "vendido":
            raise ValueError("sale_device_already_sold")
        if quantity > 1:
            raise ValueError("sale_requires_single_unit")


def _mark_device_sold(device: models.Device) -> None:
    if device.imei or device.serial:
        device.estado = "vendido"


def _restore_device_availability(device: models.Device) -> None:
    if device.imei or device.serial:
        device.estado = "disponible"


def _ensure_device_available_for_preview(
    device: models.Device,
    quantity: int,
    *,
    reserved_quantity: int = 0,
    active_reserved: int = 0,
) -> None:
    if quantity <= 0:
        raise ValueError("sale_invalid_quantity")
    effective_stock = max(device.quantity - active_reserved, 0)
    available_quantity = effective_stock + reserved_quantity
    if available_quantity < quantity:
        raise ValueError("sale_insufficient_stock")
    if device.imei or device.serial:
        if (
            device.estado
            and device.estado.lower() == "vendido"
            and reserved_quantity <= 0
        ):
            raise ValueError("sale_device_already_sold")
        if quantity > 1:
            raise ValueError("sale_requires_single_unit")


def _preview_sale_totals(
    db: Session,
    store_id: int,
    items: list[schemas.SaleItemCreate],
    *,
    sale_discount_percent: Decimal,
    reserved_quantities: dict[int, int] | None = None,
    active_reservations: dict[int, int] | None = None,
) -> tuple[Decimal, Decimal]:
    gross_total = Decimal("0")
    total_discount = Decimal("0")
    reserved = reserved_quantities or {}
    blocked = active_reservations or {}

    for item in items:
        device = get_device(db, store_id, item.device_id)
        reserved_quantity = reserved.get(device.id, 0)
        _ensure_device_available_for_preview(
            device,
            item.quantity,
            reserved_quantity=reserved_quantity,
            active_reserved=blocked.get(device.id, 0),
        )

        # // [PACK34-pricing]
        override_price = getattr(item, "unit_price_override", None)
        if override_price is not None:
            line_unit_price = to_decimal(override_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            line_unit_price = to_decimal(device.unit_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        quantity_decimal = to_decimal(item.quantity)
        line_total = (line_unit_price * quantity_decimal).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        gross_total += line_total

        line_discount_percent = to_decimal(
            getattr(item, "discount_percent", None))
        if line_discount_percent == Decimal("0"):
            line_discount_percent = sale_discount_percent
        discount_fraction = line_discount_percent / Decimal("100")
        line_discount_amount = (line_total * discount_fraction).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_discount += line_discount_amount

    return gross_total, total_discount


def _build_sale_movement_comment(
    sale: models.Sale, device: models.Device, reason: str | None
) -> str:
    segments = [f"Venta #{sale.id}"]
    if device.sku:
        segments.append(f"SKU {device.sku}")
    if reason:
        segments.append(reason)
    return " — ".join(segments)[:255]


def _apply_sale_items(
    db: Session,
    sale: models.Sale,
    items: list[schemas.SaleItemCreate],
    *,
    store: models.Store,
    sale_discount_percent: Decimal,
    performed_by_id: int,
    reason: str | None,
    reservations: dict[int, models.InventoryReservation] | None = None,
    active_reservations: dict[int, int] | None = None,
) -> tuple[Decimal, Decimal]:
    gross_total = Decimal("0")
    total_discount = Decimal("0")
    reservation_map = reservations or {}
    blocked_reserved = dict(active_reservations or {})
    consumed: list[models.InventoryReservation] = []
    batch_consumption: dict[str, int] = {}

    for item in items:
        device = get_device(db, sale.store_id, item.device_id)
        reservation_id = getattr(item, "reservation_id", None)
        allowance = 0
        reservation: models.InventoryReservation | None = None
        if reservation_id is not None:
            reservation = reservation_map.get(reservation_id)
            if reservation is None:
                raise ValueError("reservation_not_active")
            if reservation.device_id != device.id:
                raise ValueError("reservation_device_mismatch")
            allowance = reservation.quantity
        active_reserved = max(blocked_reserved.get(
            device.id, 0) - allowance, 0)
        _ensure_device_available_for_sale(
            device, item.quantity, active_reserved=active_reserved
        )
        blocked_reserved[device.id] = active_reserved

        # // [PACK34-pricing]
        override_price = getattr(item, "unit_price_override", None)
        if override_price is not None:
            line_unit_price = to_decimal(override_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            line_unit_price = to_decimal(device.unit_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        quantity_decimal = to_decimal(item.quantity)
        line_total = (line_unit_price * quantity_decimal).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        gross_total += line_total

        line_discount_percent = to_decimal(
            getattr(item, "discount_percent", None))
        if line_discount_percent == Decimal("0"):
            line_discount_percent = sale_discount_percent
        discount_fraction = line_discount_percent / Decimal("100")
        line_discount_amount = (line_total * discount_fraction).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_discount += line_discount_amount
        net_line_total = (line_total - line_discount_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        sale_item = models.SaleItem(
            sale_id=sale.id,
            device_id=device.id,
            quantity=item.quantity,
            unit_price=line_unit_price,
            discount_amount=line_discount_amount,
            total_line=net_line_total,
            reservation_id=reservation.id if reservation is not None else None,
        )
        sale_item.warranty_status = models.WarrantyStatus.SIN_GARANTIA
        sale.items.append(sale_item)

        batch_code = getattr(item, "batch_code", None)
        movement_comment = _build_sale_movement_comment(sale, device, reason)
        if batch_code:
            batch_comment = batch_code.strip()
            if batch_comment:
                movement_comment = f"{movement_comment} | Lote {batch_comment}"[
                    :255]

        movement = register_inventory_movement(
            db,
            store_id=sale.store_id,
            device_id=device.id,
            movement_type=models.MovementType.OUT,
            quantity=item.quantity,
            comment=movement_comment,
            performed_by_id=performed_by_id,
            source_store_id=sale.store_id,
            reference_type="sale",
            reference_id=str(sale.id),
        )
        movement_device = movement.device or device
        if movement_device.quantity <= 0:
            _mark_device_sold(movement_device)
        if batch_code:
            batch = consume_supplier_batch(
                db,
                store=store,
                device=movement_device,
                batch_code=batch_code,
                quantity=item.quantity,
            )
            if batch.supplier and batch.supplier.name:
                movement_device.proveedor = batch.supplier.name
            movement_device.lote = batch.batch_code
            db.add(movement_device)
            batch_consumption[batch.batch_code] = (
                batch_consumption.get(batch.batch_code, 0) + item.quantity
            )
        if reservation is not None:
            consumed.append(reservation)

    for reservation in consumed:
        release_reservation(
            db,
            reservation.id,
            performed_by_id=performed_by_id,
            reason=reason,
            target_state=models.InventoryState.CONSUMIDO,
            reference_type="sale",
            reference_id=str(sale.id),
        )
    sale.__dict__.setdefault("_batch_consumption", batch_consumption)
    return gross_total, total_discount


def _add_months_to_date(base_date: date, months: int) -> date:
    if months <= 0:
        return base_date
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(base_date.day, last_day)
    return date(year, month, day)


def _resolve_warranty_serial(device: models.Device) -> str | None:
    identifier = (device.imei or "").strip()
    if identifier:
        return identifier
    serial = (device.serial or "").strip()
    return serial or None


def _create_warranty_assignments(
    db: Session, sale: models.Sale
) -> list[models.WarrantyAssignment]:
    activation_dt = sale.created_at or datetime.now(timezone.utc)
    activation_date = activation_dt.date()
    assignments: list[models.WarrantyAssignment] = []

    for sale_item in sale.items:
        device = get_device(db, sale.store_id, sale_item.device_id)
        coverage_months = int(device.garantia_meses or 0)
        if coverage_months <= 0:
            sale_item.warranty_status = models.WarrantyStatus.SIN_GARANTIA
            continue
        expiration_date = _add_months_to_date(activation_date, coverage_months)
        assignment = models.WarrantyAssignment(
            sale_item_id=sale_item.id,
            device_id=device.id,
            coverage_months=coverage_months,
            activation_date=activation_date,
            expiration_date=expiration_date,
            status=models.WarrantyStatus.ACTIVA,
            serial_number=_resolve_warranty_serial(device),
        )
        sale_item.warranty_status = models.WarrantyStatus.ACTIVA
        db.add(assignment)
    return assignments


def create_sale(
    db: Session,
    payload: schemas.SaleCreate,
    *,
    performed_by_id: int,
    tax_rate: Decimal | float | int | None = None,
    reason: str | None = None,
) -> models.Sale:
    if not payload.items:
        raise ValueError("sale_items_required")

    store = get_store(db, payload.store_id)

    customer = None
    customer_name = payload.customer_name
    if payload.customer_id:
        customer = get_customer(db, payload.customer_id)
        customer_name = customer_name or customer.name

    sale_discount_percent = to_decimal(payload.discount_percent or 0)
    sale_status = (payload.status or "COMPLETADA").strip() or "COMPLETADA"
    normalized_status = sale_status.upper()
    sale = models.Sale(
        store_id=payload.store_id,
        customer_id=customer.id if customer else None,
        customer_name=customer_name,
        payment_method=models.PaymentMethod(payload.payment_method),
        discount_percent=sale_discount_percent.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        status=normalized_status,
        notes=payload.notes,
        performed_by_id=performed_by_id,
    )
    with transactional_session(db):
        db.add(sale)

        expire_reservations(db, store_id=sale.store_id, device_ids=[
                            item.device_id for item in payload.items])
        reservation_map: dict[int, models.InventoryReservation] = {}
        reserved_allowances: dict[int, int] = {}
        device_ids = {item.device_id for item in payload.items}
        for item in payload.items:
            reservation_id = getattr(item, "reservation_id", None)
            if reservation_id is None:
                continue
            reservation = get_inventory_reservation(db, reservation_id)
            if reservation.store_id != sale.store_id:
                raise ValueError("reservation_store_mismatch")
            if reservation.device_id != item.device_id:
                raise ValueError("reservation_device_mismatch")
            if reservation.status != models.InventoryState.RESERVADO:
                raise ValueError("reservation_not_active")
            if reservation.quantity != item.quantity:
                raise ValueError("reservation_quantity_mismatch")
            if reservation.expires_at <= datetime.now(timezone.utc):
                raise ValueError("reservation_expired")
            reservation_map[reservation.id] = reservation
            reserved_allowances[item.device_id] = reserved_allowances.get(
                item.device_id, 0
            ) + reservation.quantity

        active_reserved_map = _active_reservations_by_device(
            db, store_id=sale.store_id, device_ids=device_ids
        )
        blocked_map: dict[int, int] = {}
        for device_id in device_ids:
            active_total = active_reserved_map.get(device_id, 0)
            allowance = reserved_allowances.get(device_id, 0)
            blocked_map[device_id] = max(active_total - allowance, 0)

        tax_value = to_decimal(tax_rate)
        if tax_value < Decimal("0"):
            tax_value = Decimal("0")
        tax_fraction = tax_value / \
            Decimal("100") if tax_value else Decimal("0")

        try:
            preview_gross_total, preview_discount = _preview_sale_totals(
                db,
                sale.store_id,
                payload.items,
                sale_discount_percent=sale_discount_percent,
                reserved_quantities=reserved_allowances,
                active_reservations=blocked_map,
            )
            preview_subtotal = (preview_gross_total - preview_discount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            preview_tax_amount = (preview_subtotal * tax_fraction).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            preview_total = (preview_subtotal + preview_tax_amount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if customer and sale.payment_method == models.PaymentMethod.CREDITO:
                _validate_customer_credit(customer, preview_total)
        except ValueError:
            db.expunge(sale)
            raise

        flush_session(db)

        ledger_entry: models.CustomerLedgerEntry | None = None
        customer_to_sync: models.Customer | None = None

        gross_total, total_discount = _apply_sale_items(
            db,
            sale,
            payload.items,
            store=store,
            sale_discount_percent=sale_discount_percent,
            performed_by_id=performed_by_id,
            reason=reason,
            reservations=reservation_map,
            active_reservations=blocked_map,
        )

        subtotal = (gross_total - total_discount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        sale.subtotal_amount = subtotal
        tax_amount = (
            subtotal * tax_fraction).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sale.tax_amount = tax_amount
        sale.total_amount = (subtotal + tax_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        flush_session(db)
        _create_warranty_assignments(db, sale)

        recalculate_store_inventory_value(db, sale.store_id)

        if customer:
            if sale.payment_method == models.PaymentMethod.CREDITO:
                customer.outstanding_debt = (
                    to_decimal(customer.outstanding_debt) + sale.total_amount
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                ledger_entry = _create_customer_ledger_entry(
                    db,
                    customer=customer,
                    entry_type=models.CustomerLedgerEntryType.SALE,
                    amount=sale.total_amount,
                    reference_type="sale",
                    reference_id=str(sale.id),
                    performed_by_id=performed_by_id,
                    notes=f"Venta a crédito #{sale.id}",
                )
                customer_to_sync = customer

        _log_action(
            db,
            action="sale_registered",
            entity_type="sale",
            entity_id=str(sale.id),
            performed_by_id=performed_by_id,
            details=json.dumps({
                "message": f"Venta #{sale.id} creada con {len(payload.items)} items",
                "reason": reason
            }),
        )
        flush_session(db)
        db.refresh(sale)

        enqueue_sync_outbox(
            db,
            entity_type="sale",
            entity_id=sale.id,
            operation="create",
            payload=schemas.SaleResponse.model_validate(
                sale).model_dump(mode="json"),
        )
        if customer_to_sync:
            enqueue_sync_outbox(
                db,
                store_id=sale.store_id,
                entity_type="customer",
                entity_id=customer_to_sync.id,
                operation="update",
                payload=schemas.CustomerResponse.model_validate(
                    customer_to_sync
                ).model_dump(mode="json"),
            )
        if ledger_entry:
            enqueue_sync_outbox(
                db,
                store_id=sale.store_id,
                entity_type="customer_ledger",
                entity_id=ledger_entry.id,
                operation="create",
                payload=schemas.CustomerLedgerEntryResponse.model_validate(
                    ledger_entry
                ).model_dump(mode="json"),
            )

    return sale


def get_sale(db: Session, sale_id: int) -> models.Sale:
    statement = (
        select(models.Sale)
        .options(
            joinedload(models.Sale.items).joinedload(models.SaleItem.device),
            joinedload(models.Sale.customer),
            joinedload(models.Sale.performed_by),
        )
        .where(models.Sale.id == sale_id)
    )
    sale = db.scalar(statement)
    if not sale:
        raise LookupError("sale_not_found")
    return sale


def list_sales(
    db: Session,
    *,
    store_id: int | None = None,
    customer_id: int | None = None,
    performed_by_id: int | None = None,
    start_date: date | datetime | None = None,
    end_date: date | datetime | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[models.Sale]:
    statement = (
        select(models.Sale)
        .options(
            joinedload(models.Sale.items).joinedload(models.SaleItem.device),
            joinedload(models.Sale.customer),
            joinedload(models.Sale.performed_by),
        )
        .order_by(desc(models.Sale.created_at))
    )

    if store_id is not None:
        statement = statement.where(models.Sale.store_id == store_id)
    if customer_id is not None:
        statement = statement.where(models.Sale.customer_id == customer_id)
    if performed_by_id is not None:
        statement = statement.where(
            models.Sale.performed_by_id == performed_by_id)
    if status:
        statement = statement.where(models.Sale.status == status.upper())

    if start_date:
        dt_start = (
            start_date
            if isinstance(start_date, datetime)
            else datetime.combine(start_date, datetime.min.time())
        )
        statement = statement.where(models.Sale.created_at >= dt_start)
    if end_date:
        dt_end = (
            end_date
            if isinstance(end_date, datetime)
            else datetime.combine(end_date, datetime.max.time())
        )
        statement = statement.where(models.Sale.created_at <= dt_end)

    if search:
        term = f"%{search.strip()}%"
        statement = statement.join(
            models.Sale.items).join(models.SaleItem.device)
        statement = statement.where(
            or_(
                models.Sale.customer_name.ilike(term),
                models.Sale.notes.ilike(term),
                models.Device.sku.ilike(term),
                models.Device.name.ilike(term),
            )
        )

    statement = statement.limit(limit).offset(offset)
    return list(db.scalars(statement).unique())


def update_sale(
    db: Session,
    sale_id: int,
    payload: schemas.SaleUpdate,
    *,
    performed_by_id: int,
    reason: str | None = None,
) -> models.Sale:
    sale = get_sale(db, sale_id)
    if sale.status == "CANCELADA":
        raise ValueError("sale_already_cancelled")

    with transactional_session(db):
        if payload.notes is not None:
            sale.notes = payload.notes
        if payload.payment_method is not None:
            sale.payment_method = models.PaymentMethod(payload.payment_method)
        if payload.status is not None:
            new_status = payload.status.upper()
            if new_status == "CANCELADA" and sale.status != "CANCELADA":
                # Use cancel_sale logic instead
                raise ValueError("use_cancel_endpoint")
            sale.status = new_status

        if payload.items is not None:
            # 1. Restore inventory for existing items
            for item in sale.items:
                device = get_device(db, sale.store_id, item.device_id)
                register_inventory_movement(
                    db,
                    store_id=sale.store_id,
                    device_id=device.id,
                    movement_type=models.MovementType.IN,
                    quantity=item.quantity,
                    comment=f"Actualización Venta #{sale.id} - Restauración",
                    performed_by_id=performed_by_id,
                    source_store_id=sale.store_id,
                    reference_type="sale_update",
                    reference_id=str(sale.id),
                )
                _restore_device_availability(device)
                db.delete(item)

            # Flush to remove items from DB before adding new ones
            db.flush()
            sale.items = []  # Clear relationship

            # 2. Apply new items
            store = get_store(db, sale.store_id)
            sale_discount_percent = to_decimal(
                payload.discount_percent) if payload.discount_percent is not None else sale.discount_percent

            # Update discount if provided
            if payload.discount_percent is not None:
                sale.discount_percent = sale_discount_percent

            gross_total, total_discount = _apply_sale_items(
                db,
                sale,
                payload.items,
                store=store,
                sale_discount_percent=sale_discount_percent,
                performed_by_id=performed_by_id,
                reason=reason or "Actualización de venta",
            )

            # 3. Recalculate totals
            pos_config = db.scalar(select(models.POSConfig).where(
                models.POSConfig.store_id == sale.store_id))
            tax_rate = pos_config.tax_rate if pos_config else Decimal("0")

            tax_value = to_decimal(tax_rate)
            if tax_value < Decimal("0"):
                tax_value = Decimal("0")
            tax_fraction = tax_value / \
                Decimal("100") if tax_value else Decimal("0")

            subtotal = (gross_total - total_discount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            sale.subtotal_amount = subtotal
            tax_amount = (
                subtotal * tax_fraction).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            sale.tax_amount = tax_amount
            sale.total_amount = (subtotal + tax_amount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            recalculate_store_inventory_value(db, sale.store_id)

        _log_action(
            db,
            action="sale_updated",
            entity_type="sale",
            entity_id=str(sale.id),
            performed_by_id=performed_by_id,
            details=f"Actualización de venta #{sale.id}",
        )
        flush_session(db)
        db.refresh(sale)

        enqueue_sync_outbox(
            db,
            entity_type="sale",
            entity_id=sale.id,
            operation="update",
            payload=schemas.SaleResponse.model_validate(
                sale).model_dump(mode="json"),
        )
    return sale


def cancel_sale(
    db: Session,
    sale_id: int,
    *,
    performed_by_id: int,
    reason: str | None = None,
) -> models.Sale:
    sale = get_sale(db, sale_id)
    if sale.status == "CANCELADA":
        raise ValueError("sale_already_cancelled")

    with transactional_session(db):
        sale.status = "CANCELADA"
        if sale.invoice_reported:
            sale.invoice_reported = False
            sale.invoice_annulled_at = datetime.now(timezone.utc)
            sale.invoice_credit_note_code = f"NC-{sale.id}-{int(datetime.now(timezone.utc).timestamp())}"

            if sale.payment_method != models.PaymentMethod.CREDITO and sale.customer_id:
                store_credit = models.StoreCredit(
                    customer_id=sale.customer_id,
                    issued_amount=sale.total_amount,
                    balance_amount=sale.total_amount,
                    code=sale.invoice_credit_note_code,
                    notes=f"Nota de crédito por cancelación de venta #{sale.id}",
                    expires_at=datetime.now(
                        timezone.utc) + timedelta(days=365),
                    issued_by_id=performed_by_id,
                    status=models.StoreCreditStatus.ACTIVO
                )
                db.add(store_credit)

        # Restore inventory
        for item in sale.items:
            device = get_device(db, sale.store_id, item.device_id)
            movement_comment = f"Cancelación Venta #{sale.id}"
            if reason:
                movement_comment += f" - {reason}"

            register_inventory_movement(
                db,
                store_id=sale.store_id,
                device_id=device.id,
                movement_type=models.MovementType.IN,
                quantity=item.quantity,
                comment=movement_comment[:255],
                performed_by_id=performed_by_id,
                source_store_id=sale.store_id,
                reference_type="sale_cancellation",
                reference_id=str(sale.id),
            )
            _restore_device_availability(device)

            # Cancel warranty
            if item.warranty_assignment:
                item.warranty_assignment.status = models.WarrantyStatus.ANULADA
                item.warranty_assignment.expiration_date = datetime.now(
                    timezone.utc).date()

        # Revert customer debt if credit sale
        customer_to_sync: models.Customer | None = None
        ledger_entry: models.CustomerLedgerEntry | None = None
        if sale.customer and sale.payment_method == models.PaymentMethod.CREDITO:
            sale.customer.outstanding_debt = (
                to_decimal(sale.customer.outstanding_debt) - sale.total_amount
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            ledger_entry = _create_customer_ledger_entry(
                db,
                customer=sale.customer,
                entry_type=models.CustomerLedgerEntryType.ADJUSTMENT,
                amount=-sale.total_amount,
                reference_id=str(sale.id),
                performed_by_id=performed_by_id,
                notes=f"Cancelación Venta #{sale.id}",
            )
            customer_to_sync = sale.customer

        recalculate_store_inventory_value(db, sale.store_id)

        _log_action(
            db,
            action="sale_cancelled",
            entity_type="sale",
            entity_id=str(sale.id),
            performed_by_id=performed_by_id,
            details=f"Venta #{sale.id} cancelada. Motivo: {reason or 'N/A'}",
        )
        flush_session(db)
        db.refresh(sale)

        enqueue_sync_outbox(
            db,
            entity_type="sale",
            entity_id=sale.id,
            operation="update",
            payload=schemas.SaleResponse.model_validate(
                sale).model_dump(mode="json"),
        )
        if customer_to_sync:
            enqueue_sync_outbox(
                db,
                store_id=sale.store_id,
                entity_type="customer",
                entity_id=customer_to_sync.id,
                operation="update",
                payload=schemas.CustomerResponse.model_validate(
                    customer_to_sync
                ).model_dump(mode="json"),
            )
        if ledger_entry:
            enqueue_sync_outbox(
                db,
                store_id=sale.store_id,
                entity_type="customer_ledger",
                entity_id=ledger_entry.id,
                operation="create",
                payload=schemas.CustomerLedgerEntryResponse.model_validate(
                    ledger_entry
                ).model_dump(mode="json"),
            )

    return sale


def search_sales_history(
    db: Session,
    *,
    ticket: str | None = None,
    date_value: date | None = None,
    customer: str | None = None,
    qr: str | None = None,
    limit: int = 20,
) -> dict[str, list[models.Sale]]:
    results = {
        "by_ticket": [],
        "by_date": [],
        "by_customer": [],
        "by_qr": []
    }

    base_query = select(models.Sale).options(
        joinedload(models.Sale.items).joinedload(models.SaleItem.device),
        joinedload(models.Sale.customer),
        joinedload(models.Sale.performed_by),
    ).order_by(desc(models.Sale.created_at))

    if ticket:
        ticket_id = None
        clean_ticket = ticket.strip().upper()
        if clean_ticket.startswith("TCK-"):
            try:
                ticket_id = int(clean_ticket.replace("TCK-", ""))
            except ValueError:
                pass
        elif clean_ticket.isdigit():
            ticket_id = int(clean_ticket)

        if ticket_id:
            results["by_ticket"] = list(db.scalars(
                base_query.where(models.Sale.id == ticket_id)).unique())

    if date_value:
        dt_start = datetime.combine(date_value, datetime.min.time())
        dt_end = datetime.combine(date_value, datetime.max.time())
        results["by_date"] = list(db.scalars(base_query.where(
            models.Sale.created_at >= dt_start, models.Sale.created_at <= dt_end).limit(limit)).unique())

    if customer:
        term = f"%{customer.strip()}%"
        results["by_customer"] = list(db.scalars(base_query.where(
            models.Sale.customer_name.ilike(term)).limit(limit)).unique())

    if qr:
        try:
            qr_data = json.loads(qr)
            sale_id = qr_data.get("sale_id")
            if sale_id:
                results["by_qr"] = list(db.scalars(
                    base_query.where(models.Sale.id == sale_id)).unique())
        except json.JSONDecodeError:
            pass

    return results


def build_sales_summary_report(
    db: Session,
    date_from: datetime | None,
    date_to: datetime | None,
    store_id: int | None = None,
) -> schemas.SalesSummaryReport:
    # 1. Total Sales (Gross)
    query = select(models.Sale).where(
        models.Sale.status != "CANCELADA"
    )
    if date_from:
        query = query.where(models.Sale.created_at >= date_from)
    if date_to:
        query = query.where(models.Sale.created_at <= date_to)

    if store_id:
        query = query.where(models.Sale.store_id == store_id)

    sales = db.scalars(query).all()

    total_sales = sum(s.total_amount for s in sales)
    total_orders = len(sales)
    avg_ticket = float(total_sales) / total_orders if total_orders > 0 else 0.0

    # 2. Returns
    return_query = select(models.SaleReturn)

    if date_from:
        return_query = return_query.where(
            models.SaleReturn.created_at >= date_from)
    if date_to:
        return_query = return_query.where(
            models.SaleReturn.created_at <= date_to)

    if store_id:
        return_query = return_query.join(models.Sale).where(
            models.Sale.store_id == store_id)

    returns = db.scalars(return_query).all()
    returns_count = len(returns)

    total_refunded = Decimal("0.0")

    for ret in returns:
        # Find the price from the sale.
        # We assume the sale items are loaded or we access them lazily.
        # Since we are in a session, lazy loading should work.
        sale_item = next(
            (item for item in ret.sale.items if item.device_id == ret.device_id), None)
        if sale_item:
            total_refunded += ret.quantity * sale_item.unit_price

    net = total_sales - total_refunded

    return schemas.SalesSummaryReport(
        total_sales=float(total_sales),
        total_orders=total_orders,
        avg_ticket=avg_ticket,
        returns_count=returns_count,
        net=float(net)
    )


def build_sales_by_product_report(
    db: Session,
    date_from: datetime | None,
    date_to: datetime | None,
    store_id: int | None = None,
    limit: int = 20,
) -> list[schemas.SalesByProductItem]:
    # 1. Sales Subquery
    sales_q = select(
        models.SaleItem.device_id,
        func.sum(models.SaleItem.quantity).label("qty"),
        func.sum(models.SaleItem.total_line).label("gross")
    ).join(models.Sale, models.SaleItem.sale_id == models.Sale.id).where(
        models.Sale.status != "CANCELADA"
    )

    if date_from:
        sales_q = sales_q.where(models.Sale.created_at >= date_from)
    if date_to:
        sales_q = sales_q.where(models.Sale.created_at <= date_to)
    if store_id:
        sales_q = sales_q.where(models.Sale.store_id == store_id)

    sales_sub = sales_q.group_by(models.SaleItem.device_id).subquery()

    # 2. Returns Subquery
    returns_q = select(
        models.SaleReturn.device_id,
        func.sum(models.SaleReturn.quantity).label("qty"),
        func.sum(models.SaleReturn.quantity *
                 models.SaleItem.unit_price).label("amount")
    ).join(models.Sale, models.SaleReturn.sale_id == models.Sale.id)\
     .join(models.SaleItem, and_(
         models.SaleReturn.sale_id == models.SaleItem.sale_id,
         models.SaleReturn.device_id == models.SaleItem.device_id
     ))

    if date_from:
        returns_q = returns_q.where(models.SaleReturn.created_at >= date_from)
    if date_to:
        returns_q = returns_q.where(models.SaleReturn.created_at <= date_to)
    if store_id:
        returns_q = returns_q.where(models.Sale.store_id == store_id)

    returns_sub = returns_q.group_by(models.SaleReturn.device_id).subquery()

    # 3. Main Query
    query = select(
        models.Device.sku,
        models.Device.name,
        func.coalesce(sales_sub.c.qty, 0).label("gross_qty"),
        func.coalesce(sales_sub.c.gross, 0).label("gross_amount"),
        func.coalesce(returns_sub.c.amount, 0).label("returned_amount")
    ).outerjoin(sales_sub, models.Device.id == sales_sub.c.device_id)\
     .outerjoin(returns_sub, models.Device.id == returns_sub.c.device_id)\
     .where(sales_sub.c.qty > 0)

    query = query.order_by(desc(func.coalesce(
        sales_sub.c.gross, 0) - func.coalesce(returns_sub.c.amount, 0)))
    query = query.limit(limit)

    results = db.execute(query).all()

    report_items = []
    for row in results:
        sku, name, gross_qty, gross_amount, returned_amount = row
        gross_qty = int(gross_qty) if gross_qty else 0
        gross_amount = float(gross_amount) if gross_amount else 0.0
        returned_amount = float(returned_amount) if returned_amount else 0.0

        net_amount = gross_amount - returned_amount

        report_items.append(schemas.SalesByProductItem(
            sku=sku,
            name=name,
            quantity=gross_qty,
            gross=gross_amount,
            net=net_amount
        ))

    return report_items


def build_cash_close_report(
    db: Session,
    date_from: datetime,
    date_to: datetime,
    store_id: int | None = None,
) -> schemas.CashCloseReport:
    # 1. Ventas brutas
    sales_query = select(func.sum(models.Sale.total_amount)).where(
        models.Sale.status != "CANCELADA",
        models.Sale.created_at >= date_from,
        models.Sale.created_at <= date_to,
    )
    if store_id:
        sales_query = sales_query.where(models.Sale.store_id == store_id)

    sales_gross = db.scalar(sales_query) or Decimal("0.0")

    # 2. Devoluciones
    returns_query = (
        select(func.sum(models.SaleReturn.quantity * models.SaleItem.unit_price))
        .join(models.Sale, models.SaleReturn.sale_id == models.Sale.id)
        .join(
            models.SaleItem,
            and_(
                models.SaleReturn.sale_id == models.SaleItem.sale_id,
                models.SaleReturn.device_id == models.SaleItem.device_id,
            ),
        )
        .where(
            models.SaleReturn.created_at >= date_from,
            models.SaleReturn.created_at <= date_to,
        )
    )

    if store_id:
        returns_query = returns_query.where(models.Sale.store_id == store_id)

    refunds = db.scalar(returns_query) or Decimal("0.0")

    # 3. Aperturas de caja en el día
    opening_stmt = select(func.coalesce(func.sum(models.CashRegisterSession.opening_amount), 0)).where(
        models.CashRegisterSession.opened_at >= date_from,
        models.CashRegisterSession.opened_at <= date_to,
    )
    if store_id:
        opening_stmt = opening_stmt.where(
            models.CashRegisterSession.store_id == store_id)
    opening = to_decimal(db.scalar(opening_stmt) or 0).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # 4. Movimientos manuales de caja
    entries_stmt = (
        select(models.CashRegisterEntry.entry_type, func.coalesce(
            func.sum(models.CashRegisterEntry.amount), 0))
        .join(models.CashRegisterSession, models.CashRegisterEntry.session_id == models.CashRegisterSession.id)
        .where(
            models.CashRegisterEntry.created_at >= date_from,
            models.CashRegisterEntry.created_at <= date_to,
        )
        .group_by(models.CashRegisterEntry.entry_type)
    )
    if store_id:
        entries_stmt = entries_stmt.where(
            models.CashRegisterSession.store_id == store_id)

    incomes = Decimal("0.0")
    expenses = Decimal("0.0")
    for entry_type, total in db.execute(entries_stmt):
        normalized_total = to_decimal(total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if entry_type == models.CashEntryType.INGRESO:
            incomes = normalized_total
        elif entry_type == models.CashEntryType.EGRESO:
            expenses = normalized_total

    closing_suggested = opening + sales_gross - refunds + incomes - expenses

    return schemas.CashCloseReport(
        opening=float(opening),
        sales_gross=float(sales_gross),
        refunds=float(refunds),
        incomes=float(incomes),
        expenses=float(expenses),
        closing_suggested=float(closing_suggested),
    )


__all__ = [
    "build_cash_close_report",
    "build_sales_by_product_report",
    "build_sales_summary_report",
    "cancel_sale",
    "create_sale",
    "get_sale",
    "list_sales",
    "search_sales_history",
    "update_sale",
]
