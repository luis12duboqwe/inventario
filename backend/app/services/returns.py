"""Servicios de consulta y auditoría de devoluciones."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas

_DEFAULT_WINDOW_DAYS = 30


@dataclass(slots=True)
class _ReturnFilters:
    start: datetime
    end: datetime
    store_id: int | None
    kind: schemas.ReturnRecordType | None


def _normalize_range(
    date_from: datetime | None,
    date_to: datetime | None,
) -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    start = date_from or (now - timedelta(days=_DEFAULT_WINDOW_DAYS))
    end = date_to or now
    if start > end:
        start, end = end, start
    return start, end


def _user_display_name(user: models.User | None) -> str | None:
    if user is None:
        return None
    return user.full_name or user.username


def _customer_display_name(sale: models.Sale | None) -> str | None:
    if sale is None:
        return None
    if sale.customer and sale.customer.full_name:
        return sale.customer.full_name
    if sale.customer_name:
        return sale.customer_name
    if sale.customer and sale.customer.nombre:
        return sale.customer.nombre
    return None


def _to_decimal(value: Decimal | float | int | None) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _sale_return_amount(sale_return: models.SaleReturn) -> Decimal:
    sale = sale_return.sale
    if sale is None:
        return Decimal("0")
    sale_item = next(
        (item for item in sale.items if item.device_id == sale_return.device_id),
        None,
    )
    if sale_item is None or sale_item.quantity <= 0:
        return Decimal("0")
    unit_total = _to_decimal(sale_item.total_line)
    unit_quantity = Decimal(sale_item.quantity)
    if unit_quantity <= 0:
        return Decimal("0")
    unit_price = (unit_total / unit_quantity).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return (unit_price * Decimal(sale_return.quantity)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _serialize_sale_return(
    sale_return: models.SaleReturn,
) -> schemas.ReturnRecord:
    sale = sale_return.sale
    store = sale.store if sale else None
    device = sale_return.device
    processed_by = sale_return.processed_by
    warehouse = sale_return.warehouse
    refund_amount = _sale_return_amount(sale_return)
    payment_method = sale.payment_method if sale else None
    return schemas.ReturnRecord(
        id=sale_return.id,
        type=schemas.ReturnRecordType.SALE,
        reference_id=sale_return.sale_id,
        reference_label=f"Venta #{sale_return.sale_id}",
        store_id=sale.store_id if sale else 0,
        store_name=store.name if store else None,
        warehouse_id=sale_return.warehouse_id,
        warehouse_name=warehouse.name if warehouse else None,
        device_id=sale_return.device_id,
        device_name=device.name if device else None,
        quantity=sale_return.quantity,
        reason=sale_return.reason,
        disposition=sale_return.disposition,
        processed_by_id=sale_return.processed_by_id,
        processed_by_name=_user_display_name(processed_by),
        partner_name=_customer_display_name(sale),
        occurred_at=sale_return.created_at,
        refund_amount=refund_amount,
        payment_method=payment_method,
    )


def _serialize_purchase_return(
    purchase_return: models.PurchaseReturn,
) -> schemas.ReturnRecord:
    order = purchase_return.order
    store = order.store if order else None
    device = purchase_return.device
    processed_by = purchase_return.processed_by
    warehouse = purchase_return.warehouse
    store_id = order.store_id if order else 0
    supplier_name = order.supplier if order else None
    return schemas.ReturnRecord(
        id=purchase_return.id,
        type=schemas.ReturnRecordType.PURCHASE,
        reference_id=purchase_return.purchase_order_id,
        reference_label=f"Compra #{purchase_return.purchase_order_id}",
        store_id=store_id,
        store_name=store.name if store else None,
        warehouse_id=purchase_return.warehouse_id,
        warehouse_name=warehouse.name if warehouse else None,
        device_id=purchase_return.device_id,
        device_name=device.name if device else None,
        quantity=purchase_return.quantity,
        reason=purchase_return.reason,
        disposition=purchase_return.disposition,
        processed_by_id=purchase_return.processed_by_id,
        processed_by_name=_user_display_name(processed_by),
        partner_name=supplier_name,
        occurred_at=purchase_return.created_at,
    )


def _count_sale_returns(db: Session, filters: _ReturnFilters) -> int:
    if filters.kind is not None and filters.kind != schemas.ReturnRecordType.SALE:
        return 0
    statement = (
        select(func.count(models.SaleReturn.id))
        .join(models.Sale, models.Sale.id == models.SaleReturn.sale_id)
        .where(models.SaleReturn.created_at.between(filters.start, filters.end))
    )
    if filters.store_id is not None:
        statement = statement.where(models.Sale.store_id == filters.store_id)
    return int(db.scalar(statement) or 0)


def _count_purchase_returns(db: Session, filters: _ReturnFilters) -> int:
    if filters.kind is not None and filters.kind != schemas.ReturnRecordType.PURCHASE:
        return 0
    statement = (
        select(func.count(models.PurchaseReturn.id))
        .join(
            models.PurchaseOrder,
            models.PurchaseOrder.id == models.PurchaseReturn.purchase_order_id,
        )
        .where(models.PurchaseReturn.created_at.between(filters.start, filters.end))
    )
    if filters.store_id is not None:
        statement = statement.where(models.PurchaseOrder.store_id == filters.store_id)
    return int(db.scalar(statement) or 0)


def _list_sale_returns(
    db: Session,
    filters: _ReturnFilters,
    limit: int,
    offset: int,
) -> tuple[list[schemas.ReturnRecord], dict[str, Decimal], Decimal]:
    if filters.kind is not None and filters.kind != schemas.ReturnRecordType.SALE:
        return [], {}, Decimal("0")

    fetch_limit = limit + offset
    statement = (
        select(models.SaleReturn)
        .options(
            joinedload(models.SaleReturn.sale).joinedload(models.Sale.store),
            joinedload(models.SaleReturn.sale).joinedload(models.Sale.customer),
            joinedload(models.SaleReturn.sale).joinedload(models.Sale.items),
            joinedload(models.SaleReturn.device),
            joinedload(models.SaleReturn.processed_by),
            joinedload(models.SaleReturn.warehouse),
        )
        .where(models.SaleReturn.created_at.between(filters.start, filters.end))
        .order_by(models.SaleReturn.created_at.desc())
        .limit(fetch_limit)
    )
    if filters.store_id is not None:
        statement = statement.join(models.Sale).where(
            models.Sale.store_id == filters.store_id
        )
    sale_returns = db.scalars(statement).unique().all()
    records: list[schemas.ReturnRecord] = []
    refunds_by_method: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    refund_total = Decimal("0")
    for sale_return in sale_returns:
        record = _serialize_sale_return(sale_return)
        records.append(record)
        if record.payment_method is not None and record.refund_amount is not None:
            method_key = record.payment_method.value
            refunds_by_method[method_key] = (
                refunds_by_method[method_key] + record.refund_amount
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            refund_total = (refund_total + record.refund_amount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
    return records, dict(refunds_by_method), refund_total


def _list_purchase_returns(
    db: Session,
    filters: _ReturnFilters,
    limit: int,
    offset: int,
) -> Sequence[schemas.ReturnRecord]:
    if filters.kind is not None and filters.kind != schemas.ReturnRecordType.PURCHASE:
        return []

    fetch_limit = limit + offset
    statement = (
        select(models.PurchaseReturn)
        .options(
            joinedload(models.PurchaseReturn.order).joinedload(models.PurchaseOrder.store),
            joinedload(models.PurchaseReturn.device),
            joinedload(models.PurchaseReturn.processed_by),
            joinedload(models.PurchaseReturn.warehouse),
        )
        .where(models.PurchaseReturn.created_at.between(filters.start, filters.end))
        .order_by(models.PurchaseReturn.created_at.desc())
        .limit(fetch_limit)
    )
    if filters.store_id is not None:
        statement = statement.join(models.PurchaseOrder).where(
            models.PurchaseOrder.store_id == filters.store_id
        )
    purchase_returns = db.scalars(statement).all()
    return [_serialize_purchase_return(item) for item in purchase_returns]


def _merge_returns(
    sales: Sequence[schemas.ReturnRecord],
    purchases: Sequence[schemas.ReturnRecord],
) -> list[schemas.ReturnRecord]:
    combined = list(sales) + list(purchases)
    combined.sort(key=lambda record: record.occurred_at, reverse=True)
    return combined


def list_returns(
    db: Session,
    *,
    store_id: int | None = None,
    kind: schemas.ReturnRecordType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> schemas.ReturnsOverview:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    start, end = _normalize_range(date_from, date_to)
    filters = _ReturnFilters(start=start, end=end, store_id=store_id, kind=kind)

    sale_count = _count_sale_returns(db, filters)
    purchase_count = _count_purchase_returns(db, filters)

    sale_returns, refunds_by_method, refund_total_amount = _list_sale_returns(
        db, filters, limit, offset
    )
    purchase_returns = _list_purchase_returns(db, filters, limit, offset)

    combined = _merge_returns(sale_returns, purchase_returns)
    paginated = combined[offset : offset + limit]

    totals = schemas.ReturnsTotals(
        total=sale_count + purchase_count,
        sales=sale_count,
        purchases=purchase_count,
        refunds_by_method=refunds_by_method,
        refund_total_amount=refund_total_amount,
    )
    return schemas.ReturnsOverview(items=list(paginated), totals=totals)


__all__ = ["list_returns"]
