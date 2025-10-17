"""Servicios de dominio para operaciones de inventario heredadas."""
from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Integer, Numeric, String, case, column, func, select, table
from sqlalchemy.orm import Session

from .. import crud, schemas


def list_stores(db: Session) -> list[schemas.StoreResponse]:
    """Devuelve todas las sucursales disponibles ordenadas alfabéticamente."""

    stores = crud.list_stores(db)
    return [schemas.StoreResponse.model_validate(store, from_attributes=True) for store in stores]


def create_store(db: Session, store_in: schemas.StoreCreate) -> schemas.StoreResponse:
    """Persiste una nueva sucursal reutilizando las validaciones corporativas."""

    store = crud.create_store(db, store_in, performed_by_id=None)
    return schemas.StoreResponse.model_validate(store, from_attributes=True)


def list_devices(db: Session, store_id: int) -> list[schemas.DeviceResponse]:
    """Devuelve los dispositivos pertenecientes a una sucursal."""

    devices = crud.list_devices(db, store_id)
    return [schemas.DeviceResponse.model_validate(device, from_attributes=True) for device in devices]


def create_device(
    db: Session,
    *,
    store_id: int,
    device_in: schemas.DeviceCreate,
) -> schemas.DeviceResponse:
    """Persiste un nuevo dispositivo para una sucursal con reglas de catálogo pro."""

    device = crud.create_device(db, store_id, device_in, performed_by_id=None)
    return schemas.DeviceResponse.model_validate(device, from_attributes=True)


def calculate_inventory_valuation(
    db: Session,
    *,
    store_ids: Iterable[int] | None = None,
    categories: Iterable[str] | None = None,
) -> list[schemas.InventoryValuation]:
    """Devuelve métricas de valoración de inventario desde la vista corporativa."""

    valor_inventario = table(
        "valor_inventario",
        column("store_id", Integer),
        column("store_name", String),
        column("device_id", Integer),
        column("sku", String),
        column("device_name", String),
        column("categoria", String),
        column("quantity", Integer),
        column("costo_promedio_ponderado", Numeric),
        column("valor_total_producto", Numeric),
        column("valor_total_tienda", Numeric),
        column("valor_total_general", Numeric),
        column("margen_unitario", Numeric),
        column("margen_producto_porcentaje", Numeric),
        column("margen_categoria_valor", Numeric),
        column("margen_categoria_porcentaje", Numeric),
    )

    stmt = select(valor_inventario)

    if store_ids:
        store_filter = sorted({int(store_id) for store_id in store_ids if int(store_id) > 0})
        if store_filter:
            stmt = stmt.where(valor_inventario.c.store_id.in_(store_filter))

    if categories:
        category_filter = sorted({category for category in categories if category})
        if category_filter:
            stmt = stmt.where(valor_inventario.c.categoria.in_(category_filter))

    filtered_view = stmt.subquery("filtered_valor_inventario")

    valor_total_tienda_expr = func.round(
        func.sum(filtered_view.c.valor_total_producto).over(partition_by=filtered_view.c.store_id),
        2,
    )
    valor_total_general_expr = func.round(
        func.sum(filtered_view.c.valor_total_producto).over(),
        2,
    )

    margen_total_producto_expr = filtered_view.c.quantity * filtered_view.c.margen_unitario
    margen_categoria_valor_total_expr = func.sum(margen_total_producto_expr).over(
        partition_by=filtered_view.c.categoria
    )
    margen_categoria_valor_expr = func.round(
        margen_categoria_valor_total_expr,
        2,
    )
    ventas_categoria_total_expr = func.sum(filtered_view.c.valor_total_producto).over(
        partition_by=filtered_view.c.categoria
    )
    margen_categoria_porcentaje_expr = func.round(
        case(
            (ventas_categoria_total_expr == 0, 0),
            else_=(
                margen_categoria_valor_total_expr
                / func.nullif(ventas_categoria_total_expr, 0)
                * 100
            ),
        ),
        2,
    )
    margen_producto_porcentaje_expr = func.round(
        case(
            (filtered_view.c.valor_total_producto == 0, 0),
            else_=(
                margen_total_producto_expr
                / func.nullif(filtered_view.c.valor_total_producto, 0)
                * 100
            ),
        ),
        2,
    )

    final_stmt = (
        select(
            filtered_view.c.store_id,
            filtered_view.c.store_name,
            filtered_view.c.device_id,
            filtered_view.c.sku,
            filtered_view.c.device_name,
            filtered_view.c.categoria,
            filtered_view.c.quantity,
            filtered_view.c.costo_promedio_ponderado,
            filtered_view.c.valor_total_producto,
            valor_total_tienda_expr.label("valor_total_tienda"),
            valor_total_general_expr.label("valor_total_general"),
            filtered_view.c.margen_unitario,
            margen_producto_porcentaje_expr.label("margen_producto_porcentaje"),
            margen_categoria_valor_expr.label("margen_categoria_valor"),
            margen_categoria_porcentaje_expr.label("margen_categoria_porcentaje"),
        )
        .order_by(filtered_view.c.store_name.asc(), filtered_view.c.device_name.asc())
    )

    rows = db.execute(final_stmt).mappings()
    return [schemas.InventoryValuation.model_validate(row) for row in rows]
