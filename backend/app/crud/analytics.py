"""Operaciones CRUD para Analítica y Reportes Avanzados.

Migrado desde crud_legacy.py - Fase 2, Incremento 2
Contiene funciones para análisis de rotación, envejecimiento, proyecciones y comparativas.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.utils.date_helpers import normalize_date_range
from backend.app.utils.inventory_helpers import device_category_expr
from backend.app.utils.normalization_helpers import normalize_store_ids
from backend.app.utils.analytics_helpers import linear_regression, project_linear_sum

# Avoid circular imports
if TYPE_CHECKING:
    from backend.app import crud_legacy

__all__ = [
    'calculate_rotation_analytics',
    'calculate_aging_analytics',
    'calculate_stockout_forecast',
    'calculate_store_comparatives',
    'calculate_profit_margin',
    'calculate_sales_projection',
    'calculate_store_sales_forecast',
    'calculate_reorder_suggestions',
    'calculate_realtime_store_widget',
]
def calculate_rotation_analytics(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = normalize_store_ids(store_ids)
    start_dt, end_dt = normalize_date_range(date_from, date_to)
    category_expr = device_category_expr()

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
    if store_filter:
        device_stmt = device_stmt.where(
            models.Device.store_id.in_(store_filter))
    if category:
        device_stmt = device_stmt.where(category_expr == category)
    if supplier:
        device_stmt = device_stmt.where(models.Device.proveedor == supplier)
    if offset:
        device_stmt = device_stmt.offset(offset)
    if limit is not None:
        device_stmt = device_stmt.limit(limit)

    device_rows = list(db.execute(device_stmt))
    if not device_rows:
        return []

    device_ids = [row.id for row in device_rows]

    sale_stats = (
        select(
            models.SaleItem.device_id,
            func.sum(models.SaleItem.quantity).label("sold_units"),
            models.Sale.store_id,
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(models.SaleItem.device_id, models.Sale.store_id)
    )
    if store_filter:
        sale_stats = sale_stats.where(models.Sale.store_id.in_(store_filter))
    if device_ids:
        sale_stats = sale_stats.where(
            models.SaleItem.device_id.in_(device_ids))
    if start_dt:
        sale_stats = sale_stats.where(models.Sale.created_at >= start_dt)
    if end_dt:
        sale_stats = sale_stats.where(models.Sale.created_at <= end_dt)
    if category:
        sale_stats = sale_stats.where(category_expr == category)
    if supplier:
        sale_stats = sale_stats.where(models.Device.proveedor == supplier)

    purchase_stats = (
        select(
            models.PurchaseOrderItem.device_id,
            func.sum(models.PurchaseOrderItem.quantity_received).label(
                "received_units"),
            models.PurchaseOrder.store_id,
        )
        .join(models.PurchaseOrder, models.PurchaseOrder.id == models.PurchaseOrderItem.purchase_order_id)
        .join(models.Device, models.Device.id == models.PurchaseOrderItem.device_id)
        .group_by(models.PurchaseOrderItem.device_id, models.PurchaseOrder.store_id)
    )
    if store_filter:
        purchase_stats = purchase_stats.where(
            models.PurchaseOrder.store_id.in_(store_filter))
    if device_ids:
        purchase_stats = purchase_stats.where(
            models.PurchaseOrderItem.device_id.in_(device_ids)
        )
    if start_dt:
        purchase_stats = purchase_stats.where(
            models.PurchaseOrder.created_at >= start_dt)
    if end_dt:
        purchase_stats = purchase_stats.where(
            models.PurchaseOrder.created_at <= end_dt)
    if category:
        purchase_stats = purchase_stats.where(category_expr == category)
    if supplier:
        purchase_stats = purchase_stats.where(
            models.Device.proveedor == supplier)

    sold_map = {
        row.device_id: int(row.sold_units or 0) for row in db.execute(sale_stats)
    }
    received_map = {
        row.device_id: int(row.received_units or 0)
        for row in db.execute(purchase_stats)
    }

    results: list[dict[str, object]] = []
    for row in device_rows:
        sold_units = sold_map.get(row.id, 0)
        received_units = received_map.get(row.id, 0)
        denominator = received_units if received_units > 0 else max(
            sold_units, 1)
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



def calculate_aging_analytics(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = normalize_store_ids(store_ids)
    now_date = datetime.now(timezone.utc).date()
    category_expr = device_category_expr()
    device_stmt = (
        select(
            models.Device.id,
            models.Device.sku,
            models.Device.name,
            models.Device.fecha_compra,
            models.Device.quantity,
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
        .order_by(
            models.Device.fecha_compra.is_(None),
            models.Device.fecha_compra.asc(),
        )
    )
    if store_filter:
        device_stmt = device_stmt.where(
            models.Device.store_id.in_(store_filter))
    if date_from:
        device_stmt = device_stmt.where(
            models.Device.fecha_compra >= date_from)
    if date_to:
        device_stmt = device_stmt.where(models.Device.fecha_compra <= date_to)
    if category:
        device_stmt = device_stmt.where(category_expr == category)
    if supplier:
        device_stmt = device_stmt.where(models.Device.proveedor == supplier)

    if offset:
        device_stmt = device_stmt.offset(offset)
    if limit is not None:
        device_stmt = device_stmt.limit(limit)

    device_rows = list(db.execute(device_stmt))
    if not device_rows:
        return []

    metrics: list[dict[str, object]] = []
    for row in device_rows:
        purchase_date = row.fecha_compra
        days_in_stock = (now_date - purchase_date).days if purchase_date else 0
        metrics.append(
            {
                "device_id": row.id,
                "sku": row.sku,
                "name": row.name,
                "store_id": row.store_id,
                "store_name": row.store_name,
                "days_in_stock": max(days_in_stock, 0),
                "quantity": int(row.quantity or 0),
            }
        )
    metrics.sort(key=lambda item: item["days_in_stock"], reverse=True)
    return metrics



def calculate_stockout_forecast(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = normalize_store_ids(store_ids)
    start_dt, end_dt = normalize_date_range(date_from, date_to)
    category_expr = device_category_expr()

    device_stmt = (
        select(
            models.Device.id,
            models.Device.sku,
            models.Device.name,
            models.Device.quantity,
            models.Device.minimum_stock,
            models.Device.reorder_point,
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
        )
        .join(models.Store, models.Store.id == models.Device.store_id)
        .order_by(models.Store.name.asc(), models.Device.name.asc())
    )
    if store_filter:
        device_stmt = device_stmt.where(
            models.Device.store_id.in_(store_filter))
    if category:
        device_stmt = device_stmt.where(category_expr == category)
    if supplier:
        device_stmt = device_stmt.where(models.Device.proveedor == supplier)
    if offset:
        device_stmt = device_stmt.offset(offset)
    if limit is not None:
        device_stmt = device_stmt.limit(limit)

    device_rows = list(db.execute(device_stmt))
    if not device_rows:
        return []

    device_ids = [row.id for row in device_rows]

    sales_summary_stmt = (
        select(
            models.SaleItem.device_id,
            models.Sale.store_id,
            func.sum(models.SaleItem.quantity).label("sold_units"),
            func.min(models.Sale.created_at).label("first_sale"),
            func.max(models.Sale.created_at).label("last_sale"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(models.SaleItem.device_id, models.Sale.store_id)
    )
    if store_filter:
        sales_summary_stmt = sales_summary_stmt.where(
            models.Sale.store_id.in_(store_filter))
    if device_ids:
        sales_summary_stmt = sales_summary_stmt.where(
            models.SaleItem.device_id.in_(device_ids)
        )
    if start_dt:
        sales_summary_stmt = sales_summary_stmt.where(
            models.Sale.created_at >= start_dt)
    if end_dt:
        sales_summary_stmt = sales_summary_stmt.where(
            models.Sale.created_at <= end_dt)
    if category:
        sales_summary_stmt = sales_summary_stmt.where(
            category_expr == category)
    if supplier:
        sales_summary_stmt = sales_summary_stmt.where(
            models.Device.proveedor == supplier)

    day_column = func.date(models.Sale.created_at)
    daily_sales_stmt = (
        select(
            models.SaleItem.device_id,
            day_column.label("day"),
            func.sum(models.SaleItem.quantity).label("sold_units"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(models.SaleItem.device_id, day_column)
    )
    if store_filter:
        daily_sales_stmt = daily_sales_stmt.where(
            models.Sale.store_id.in_(store_filter))
    if device_ids:
        daily_sales_stmt = daily_sales_stmt.where(
            models.SaleItem.device_id.in_(device_ids)
        )
    if start_dt:
        daily_sales_stmt = daily_sales_stmt.where(
            models.Sale.created_at >= start_dt)
    if end_dt:
        daily_sales_stmt = daily_sales_stmt.where(
            models.Sale.created_at <= end_dt)
    if category:
        daily_sales_stmt = daily_sales_stmt.where(category_expr == category)
    if supplier:
        daily_sales_stmt = daily_sales_stmt.where(
            models.Device.proveedor == supplier)

    sales_map: dict[int, dict[str, object]] = {}
    for row in db.execute(sales_summary_stmt):
        sales_map[row.device_id] = {
            "sold_units": int(row.sold_units or 0),
            "first_sale": row.first_sale,
            "last_sale": row.last_sale,
            "store_id": int(row.store_id),
        }

    daily_sales_map: defaultdict[int,
                                 list[tuple[datetime, float]]] = defaultdict(list)
    for row in db.execute(daily_sales_stmt):
        day: datetime | None = row.day
        if day is None:
            continue
        daily_sales_map[row.device_id].append(
            (day, float(row.sold_units or 0)))

    metrics: list[dict[str, object]] = []
    for row in device_rows:
        stats = sales_map.get(row.id)
        quantity = int(row.quantity or 0)
        daily_points_raw = sorted(
            daily_sales_map.get(row.id, []), key=lambda item: item[0]
        )
        points = [(float(index), value)
                  for index, (_, value) in enumerate(daily_points_raw)]
        slope, intercept, r_squared = linear_regression(points)
        historical_avg = (
            sum(value for _, value in daily_points_raw) / len(daily_points_raw)
            if daily_points_raw
            else 0.0
        )
        predicted_next = max(0.0, slope * len(points) +
                             intercept) if points else 0.0
        expected_daily = max(historical_avg, predicted_next)

        if stats is None:
            sold_units = 0
        else:
            sold_units = int(stats.get("sold_units", 0))

        if expected_daily <= 0:
            projected_days: int | None = None
        else:
            projected_days = max(int(math.ceil(quantity / expected_daily)), 0)

        if slope > 0.25:
            trend_label = "acelerando"
        elif slope < -0.25:
            trend_label = "desacelerando"
        else:
            trend_label = "estable"

        alert_level: str | None
        if projected_days is None:
            alert_level = None
        elif projected_days <= 3:
            alert_level = "critical"
        elif projected_days <= 7:
            alert_level = "warning"
        else:
            alert_level = "ok"

        metrics.append(
            {
                "device_id": row.id,
                "sku": row.sku,
                "name": row.name,
                "store_id": row.store_id,
                "store_name": row.store_name,
                "average_daily_sales": round(float(expected_daily), 2),
                "projected_days": projected_days,
                "quantity": quantity,
                "minimum_stock": int(getattr(row, "minimum_stock", 0) or 0),
                "reorder_point": int(getattr(row, "reorder_point", 0) or 0),
                "trend": trend_label,
                "trend_score": round(float(slope), 4),
                "confidence": round(float(r_squared), 3),
                "alert_level": alert_level,
                "sold_units": sold_units,
            }
        )

    metrics.sort(key=lambda item: (
        item["projected_days"] is None, item["projected_days"] or 0))
    return metrics



def calculate_store_comparatives(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = normalize_store_ids(store_ids)
    start_dt, end_dt = normalize_date_range(date_from, date_to)
    category_expr = device_category_expr()

    inventory_stmt = (
        select(
            models.Store.id,
            models.Store.name,
            func.coalesce(func.count(models.Device.id),
                          0).label("device_count"),
            func.coalesce(func.sum(models.Device.quantity),
                          0).label("total_units"),
            func.coalesce(
                func.sum(models.Device.quantity * models.Device.unit_price),
                0,
            ).label("inventory_value"),
        )
        .outerjoin(models.Device, models.Device.store_id == models.Store.id)
        .group_by(models.Store.id)
        .order_by(models.Store.name.asc())
    )
    if store_filter:
        inventory_stmt = inventory_stmt.where(
            models.Store.id.in_(store_filter))
    if category:
        inventory_stmt = inventory_stmt.where(category_expr == category)
    if supplier:
        inventory_stmt = inventory_stmt.where(
            models.Device.proveedor == supplier)
    if offset:
        inventory_stmt = inventory_stmt.offset(offset)
    if limit is not None:
        inventory_stmt = inventory_stmt.limit(limit)

    inventory_rows = list(db.execute(inventory_stmt))
    if not inventory_rows:
        return []

    store_ids_window = [int(row.id) for row in inventory_rows]

    rotation = calculate_rotation_analytics(
        db,
        store_ids=store_ids_window,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=None,
        offset=0,
    )
    aging = calculate_aging_analytics(
        db,
        store_ids=store_ids_window,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=None,
        offset=0,
    )

    rotation_totals: dict[int, tuple[float, int]] = {}
    aging_totals: dict[int, tuple[float, int]] = {}

    for item in rotation:
        store_id = int(item["store_id"])
        total, count = rotation_totals.get(store_id, (0.0, 0))
        rotation_totals[store_id] = (
            total + float(item["rotation_rate"]), count + 1)

    for item in aging:
        store_id_value = item.get("store_id")
        if store_id_value is None:
            continue
        store_id = int(store_id_value)
        total, count = aging_totals.get(store_id, (0.0, 0))
        aging_totals[store_id] = (
            total + float(item["days_in_stock"]), count + 1)

    rotation_avg = {
        store_id: (total / count if count else 0.0)
        for store_id, (total, count) in rotation_totals.items()
    }
    aging_avg = {
        store_id: (total / count if count else 0.0)
        for store_id, (total, count) in aging_totals.items()
    }

    window_start = start_dt or (datetime.now(
        timezone.utc) - timedelta(days=30))
    sales_stmt = (
        select(
            models.Sale.store_id,
            func.coalesce(func.count(models.Sale.id), 0).label("orders"),
            func.coalesce(func.sum(models.Sale.total_amount),
                          0).label("revenue"),
        )
        .join(models.SaleItem, models.SaleItem.sale_id == models.Sale.id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .where(models.Sale.created_at >= window_start)
        .group_by(models.Sale.store_id)
    )
    if store_ids_window:
        sales_stmt = sales_stmt.where(
            models.Sale.store_id.in_(store_ids_window))
    if end_dt:
        sales_stmt = sales_stmt.where(models.Sale.created_at <= end_dt)
    if category:
        sales_stmt = sales_stmt.where(category_expr == category)
    if supplier:
        sales_stmt = sales_stmt.where(models.Device.proveedor == supplier)

    sales_map: dict[int, dict[str, Decimal]] = {}
    for row in db.execute(sales_stmt):
        sales_map[int(row.store_id)] = {
            "orders": Decimal(row.orders or 0),
            "revenue": Decimal(row.revenue or 0),
        }

    comparatives: list[dict[str, object]] = []
    for row in inventory_rows:
        store_id = int(row.id)
        sales = sales_map.get(
            store_id, {"orders": Decimal(0), "revenue": Decimal(0)})
        comparatives.append(
            {
                "store_id": store_id,
                "store_name": row.name,
                "device_count": int(row.device_count or 0),
                "total_units": int(row.total_units or 0),
                "inventory_value": float(row.inventory_value or 0),
                "average_rotation": round(rotation_avg.get(store_id, 0.0), 2),
                "average_aging_days": round(aging_avg.get(store_id, 0.0), 1),
                "sales_last_30_days": float(sales["revenue"]),
                "sales_count_last_30_days": int(sales["orders"]),
            }
        )

    comparatives.sort(key=lambda item: item["inventory_value"], reverse=True)
    return comparatives



def calculate_profit_margin(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = normalize_store_ids(store_ids)
    start_dt, end_dt = normalize_date_range(date_from, date_to)
    category_expr = device_category_expr()
    revenue_expr = func.coalesce(func.sum(models.SaleItem.total_line), 0)
    cost_expr = func.coalesce(
        func.sum(models.SaleItem.quantity * models.Device.costo_unitario),
        0,
    )
    profit_expr = revenue_expr - cost_expr
    stmt = (
        select(
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
            revenue_expr.label("revenue"),
            cost_expr.label("cost"),
            profit_expr.label("profit"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .group_by(models.Store.id, models.Store.name)
        .order_by(profit_expr.desc())
    )
    if store_filter:
        stmt = stmt.where(models.Store.id.in_(store_filter))
    if start_dt:
        stmt = stmt.where(models.Sale.created_at >= start_dt)
    if end_dt:
        stmt = stmt.where(models.Sale.created_at <= end_dt)
    if category:
        stmt = stmt.where(category_expr == category)
    if supplier:
        stmt = stmt.where(models.Device.proveedor == supplier)
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    metrics: list[dict[str, object]] = []
    for row in db.execute(stmt):
        revenue = Decimal(row.revenue or 0)
        cost = Decimal(row.cost or 0)
        profit = Decimal(row.profit or 0)
        margin_percent = float((profit / revenue * 100) if revenue else 0)
        metrics.append(
            {
                "store_id": int(row.store_id),
                "store_name": row.store_name,
                "revenue": float(revenue),
                "cost": float(cost),
                "profit": float(profit),
                "margin_percent": round(margin_percent, 2),
            }
        )

    return metrics



def calculate_sales_projection(
    db: Session,
    store_ids: Iterable[int] | None = None,
    *,
    horizon_days: int = 30,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = normalize_store_ids(store_ids)
    start_dt, end_dt = normalize_date_range(date_from, date_to)
    category_expr = device_category_expr()
    lookback_days = max(horizon_days, 30)
    since = start_dt or (datetime.now(timezone.utc) -
                         timedelta(days=lookback_days))

    store_stmt = select(models.Store.id, models.Store.name).order_by(
        models.Store.name.asc())
    if store_filter:
        store_stmt = store_stmt.where(models.Store.id.in_(store_filter))
    if offset:
        store_stmt = store_stmt.offset(offset)
    if limit is not None:
        store_stmt = store_stmt.limit(limit)

    store_rows = list(db.execute(store_stmt))
    if not store_rows:
        return []

    store_ids_window = [int(row.id) for row in store_rows]

    day_bucket = func.date(models.Sale.created_at)
    daily_stmt = (
        select(
            models.Store.id.label("store_id"),
            models.Store.name.label("store_name"),
            day_bucket.label("sale_day"),
            func.coalesce(func.sum(models.SaleItem.quantity),
                          0).label("units"),
            func.coalesce(func.sum(models.SaleItem.total_line),
                          0).label("revenue"),
            func.coalesce(func.count(func.distinct(
                models.Sale.id)), 0).label("orders"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .where(models.Sale.created_at >= since)
        .group_by(
            models.Store.id,
            models.Store.name,
            day_bucket,
        )
        .order_by(models.Store.name.asc())
    )
    daily_stmt = daily_stmt.where(models.Store.id.in_(store_ids_window))
    if end_dt:
        daily_stmt = daily_stmt.where(models.Sale.created_at <= end_dt)
    if category:
        daily_stmt = daily_stmt.where(category_expr == category)
    if supplier:
        daily_stmt = daily_stmt.where(models.Device.proveedor == supplier)

    stores_data: dict[int, dict[str, object]] = {}
    for row in db.execute(daily_stmt):
        store_entry = stores_data.setdefault(
            int(row.store_id),
            {
                "store_name": row.store_name,
                "daily": [],
                "orders": 0,
                "total_units": 0.0,
                "total_revenue": 0.0,
            },
        )
        day_value: datetime | None = row.sale_day
        if day_value is None:
            continue
        units_value = float(row.units or 0)
        revenue_value = float(row.revenue or 0)
        orders_value = int(row.orders or 0)
        store_entry["daily"].append(
            {
                "day": day_value,
                "units": units_value,
                "revenue": revenue_value,
                "orders": orders_value,
            }
        )
        store_entry["orders"] += orders_value
        store_entry["total_units"] += units_value
        store_entry["total_revenue"] += revenue_value

    projections: list[dict[str, object]] = []
    for store_id, payload in stores_data.items():
        daily_points = sorted(payload["daily"], key=lambda item: item["day"])
        if not daily_points:
            continue

        unit_points = [
            (float(index), item["units"])
            for index, item in enumerate(daily_points)
        ]
        revenue_points = [
            (float(index), item["revenue"])
            for index, item in enumerate(daily_points)
        ]
        slope_units, intercept_units, r2_units = linear_regression(
            unit_points)
        slope_revenue, intercept_revenue, r2_revenue = linear_regression(
            revenue_points
        )
        historical_avg_units = (
            payload["total_units"] / len(unit_points) if unit_points else 0.0
        )
        predicted_next_units = (
            max(0.0, slope_units * len(unit_points) + intercept_units)
            if unit_points
            else 0.0
        )
        average_daily_units = max(historical_avg_units, predicted_next_units)
        projected_units = project_linear_sum(
            slope_units, intercept_units, len(unit_points), horizon_days
        )
        projected_revenue = project_linear_sum(
            slope_revenue, intercept_revenue, len(revenue_points), horizon_days
        )
        average_ticket = (
            payload["total_revenue"] / payload["total_units"]
            if payload["total_units"] > 0
            else 0.0
        )
        orders = payload["orders"]
        sample_days = len(unit_points)
        confidence = 0.0
        if sample_days > 0:
            coverage = min(1.0, orders / sample_days)
            confidence = max(0.0, min(1.0, (r2_units + coverage) / 2))

        if slope_units > 0.5:
            trend = "creciendo"
        elif slope_units < -0.5:
            trend = "cayendo"
        else:
            trend = "estable"

        projections.append(
            {
                "store_id": store_id,
                "store_name": payload["store_name"],
                "average_daily_units": round(float(average_daily_units), 2),
                "average_ticket": round(float(average_ticket), 2),
                "projected_units": round(float(projected_units), 2),
                "projected_revenue": round(float(projected_revenue), 2),
                "confidence": round(float(confidence), 2),
                "trend": trend,
                "trend_score": round(float(slope_units), 4),
                "revenue_trend_score": round(float(slope_revenue), 4),
                "r2_revenue": round(float(r2_revenue), 3),
            }
        )

    projections.sort(key=lambda item: item["projected_revenue"], reverse=True)
    return projections



def calculate_store_sales_forecast(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    horizon_days: int = 14,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    projections = calculate_sales_projection(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        horizon_days=horizon_days,
        limit=limit,
        offset=offset,
    )
    forecasts: list[dict[str, object]] = []
    for item in projections:
        forecasts.append(
            {
                "store_id": int(item["store_id"]),
                "store_name": item["store_name"],
                "average_daily_units": float(item.get("average_daily_units", 0)),
                "projected_units": float(item.get("projected_units", 0)),
                "projected_revenue": float(item.get("projected_revenue", 0)),
                "trend": item.get("trend", "estable"),
                "confidence": float(item.get("confidence", 0)),
            }
        )
    return forecasts



def calculate_reorder_suggestions(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    horizon_days: int = 7,
    safety_days: int = 2,
    date_from: date | None = None,
    date_to: date | None = None,
    category: str | None = None,
    supplier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    horizon = max(horizon_days, 1) + max(safety_days, 0)
    forecast = calculate_stockout_forecast(
        db,
        store_ids=store_ids,
        date_from=date_from,
        date_to=date_to,
        category=category,
        supplier=supplier,
        limit=limit,
        offset=offset,
    )
    suggestions: list[dict[str, object]] = []
    for item in forecast:
        quantity = int(item.get("quantity", 0) or 0)
        reorder_point = int(item.get("reorder_point", 0) or 0)
        minimum_stock = int(item.get("minimum_stock", 0) or 0)
        avg_daily = float(item.get("average_daily_sales", 0.0) or 0.0)
        projected_days = item.get("projected_days")

        buffer_target = max(reorder_point, minimum_stock)
        demand_target = math.ceil(avg_daily * horizon)
        target_level = max(buffer_target, demand_target)
        recommended_order = max(target_level - quantity, 0)

        if recommended_order <= 0:
            continue

        reason_parts: list[str] = []
        if projected_days is not None:
            reason_parts.append(
                f"Agotamiento estimado en {projected_days} días")
        if demand_target > buffer_target:
            reason_parts.append(
                f"Cubre demanda proyectada ({horizon} días)"
            )
        if not reason_parts:
            reason_parts.append("Stock bajo frente al buffer configurado")

        suggestions.append(
            {
                "store_id": int(item["store_id"]),
                "store_name": item["store_name"],
                "device_id": int(item["device_id"]),
                "sku": item["sku"],
                "name": item["name"],
                "quantity": quantity,
                "reorder_point": reorder_point,
                "minimum_stock": minimum_stock,
                "recommended_order": recommended_order,
                "projected_days": projected_days,
                "average_daily_sales": round(avg_daily, 2) if avg_daily else None,
                "reason": "; ".join(reason_parts),
            }
        )

    suggestions.sort(key=lambda item: item["recommended_order"], reverse=True)
    return suggestions



def calculate_realtime_store_widget(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    category: str | None = None,
    supplier: str | None = None,
    low_stock_threshold: int = 5,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, object]]:
    store_filter = normalize_store_ids(store_ids)
    category_expr = device_category_expr()
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)

    stores_stmt = select(models.Store.id, models.Store.name,
                         models.Store.inventory_value)
    if store_filter:
        stores_stmt = stores_stmt.where(models.Store.id.in_(store_filter))
    stores_stmt = stores_stmt.order_by(models.Store.name.asc())
    if offset:
        stores_stmt = stores_stmt.offset(offset)
    if limit is not None:
        stores_stmt = stores_stmt.limit(limit)

    store_rows = list(db.execute(stores_stmt))
    if not store_rows:
        return []

    store_ids_window = [int(row.id) for row in store_rows]

    low_stock_stmt = (
        select(models.Device.store_id, func.count(
            models.Device.id).label("low_stock"))
        .where(models.Device.quantity <= low_stock_threshold)
        .group_by(models.Device.store_id)
    )
    if store_ids_window:
        low_stock_stmt = low_stock_stmt.where(
            models.Device.store_id.in_(store_ids_window)
        )
    if category:
        low_stock_stmt = low_stock_stmt.where(category_expr == category)
    if supplier:
        low_stock_stmt = low_stock_stmt.where(
            models.Device.proveedor == supplier)

    sales_today_stmt = (
        select(
            models.Store.id.label("store_id"),
            func.coalesce(func.sum(models.SaleItem.total_line),
                          0).label("revenue"),
            func.max(models.Sale.created_at).label("last_sale_at"),
        )
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .join(models.Store, models.Store.id == models.Sale.store_id)
        .join(models.Device, models.Device.id == models.SaleItem.device_id)
        .where(models.Sale.created_at >= today_start)
        .group_by(models.Store.id)
    )
    if store_ids_window:
        sales_today_stmt = sales_today_stmt.where(
            models.Store.id.in_(store_ids_window))
    if category:
        sales_today_stmt = sales_today_stmt.where(category_expr == category)
    if supplier:
        sales_today_stmt = sales_today_stmt.where(
            models.Device.proveedor == supplier)

    repairs_stmt = (
        select(
            models.RepairOrder.store_id,
            func.count(models.RepairOrder.id).label("pending"),
        )
        .where(models.RepairOrder.status != models.RepairStatus.ENTREGADO)
        .group_by(models.RepairOrder.store_id)
    )
    if store_ids_window:
        repairs_stmt = repairs_stmt.where(
            models.RepairOrder.store_id.in_(store_ids_window)
        )

    sync_stmt = (
        select(
            models.SyncSession.store_id,
            func.max(models.SyncSession.finished_at).label("last_sync"),
        )
        .group_by(models.SyncSession.store_id)
    )
    if store_ids_window:
        sync_stmt = sync_stmt.where(
            (models.SyncSession.store_id.is_(None))
            | (models.SyncSession.store_id.in_(store_ids_window))
        )

    low_stock_map = {
        int(row.store_id): int(row.low_stock or 0)
        for row in db.execute(low_stock_stmt)
    }
    sales_today_map = {
        int(row.store_id): {
            "revenue": float(row.revenue or 0),
            "last_sale_at": row.last_sale_at,
        }
        for row in db.execute(sales_today_stmt)
    }
    repairs_map = {
        int(row.store_id): max(int(row.pending or 0), 0)
        for row in db.execute(repairs_stmt)
    }
    sync_map: dict[int | None, datetime | None] = {
        row.store_id: row.last_sync for row in db.execute(sync_stmt)
    }
    global_sync = sync_map.get(None)

    projection_map = {
        item["store_id"]: item
        for item in calculate_sales_projection(
            db,
            store_ids=store_ids_window,
            category=category,
            supplier=supplier,
            horizon_days=7,
            limit=None,
            offset=0,
        )
    }

    widgets: list[dict[str, object]] = []
    for row in store_rows:
        store_id = int(row.id)
        sales_info = sales_today_map.get(
            store_id, {"revenue": 0.0, "last_sale_at": None})
        projection = projection_map.get(store_id, {})
        widgets.append(
            {
                "store_id": store_id,
                "store_name": row.name,
                "inventory_value": float(row.inventory_value or 0),
                "sales_today": round(float(sales_info["revenue"]), 2),
                "last_sale_at": sales_info.get("last_sale_at"),
                "low_stock_devices": low_stock_map.get(store_id, 0),
                "pending_repairs": repairs_map.get(store_id, 0),
                "last_sync_at": sync_map.get(store_id) or global_sync,
                "trend": projection.get("trend", "estable"),
                "trend_score": projection.get("trend_score", 0.0),
                "confidence": projection.get("confidence", 0.0),
            }
        )

    return widgets



