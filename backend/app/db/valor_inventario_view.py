"""Utilidades para la vista materializada de valoración de inventario."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

VIEW_NAME = "valor_inventario"

CREATE_VALOR_INVENTARIO_VIEW_SQL_POSTGRES = """
CREATE VIEW valor_inventario AS
WITH purchase_totals AS (
    SELECT
        poi.device_id AS device_id,
        SUM(poi.quantity_received) AS total_quantity,
        SUM(poi.quantity_received * poi.unit_cost) AS total_cost
    FROM purchase_order_items AS poi
    GROUP BY poi.device_id
),
purchase_recent AS (
    SELECT
        poi.device_id AS device_id,
        SUM(
            CASE
                WHEN po.created_at >= NOW() - INTERVAL '30 days' THEN poi.quantity_received
                ELSE 0
            END
        ) AS received_last_30_days,
        SUM(
            CASE
                WHEN po.created_at >= NOW() - INTERVAL '90 days' THEN poi.quantity_received
                ELSE 0
            END
        ) AS received_last_90_days,
        MAX(po.created_at) AS last_purchase_at
    FROM purchase_order_items AS poi
    JOIN purchase_orders AS po ON po.id = poi.purchase_order_id
    GROUP BY poi.device_id
),
sales_stats AS (
    SELECT
        si.device_id AS device_id,
        SUM(si.quantity) AS sold_total_units,
        SUM(
            CASE
                WHEN s.fecha >= NOW() - INTERVAL '30 days' THEN si.quantity
                ELSE 0
            END
        ) AS sold_units_last_30_days,
        SUM(
            CASE
                WHEN s.fecha >= NOW() - INTERVAL '90 days' THEN si.quantity
                ELSE 0
            END
        ) AS sold_units_last_90_days,
        MAX(s.fecha) AS last_sale_at
    FROM detalle_ventas AS si
    JOIN ventas AS s ON s.id_venta = si.venta_id
    WHERE s.estado <> 'CANCELADA'
    GROUP BY si.device_id
),
movement_stats AS (
    SELECT
        im.producto_id AS device_id,
        MAX(im.fecha) AS last_movement_at
    FROM inventory_movements AS im
    GROUP BY im.producto_id
),
device_metrics AS (
    SELECT
        d.id AS device_id,
        d.sucursal_id AS store_id,
        COALESCE(NULLIF(d.categoria, ''), 'Sin categoría') AS categoria,
        d.sku AS sku,
        d.name AS device_name,
        d.quantity AS quantity,
        d.unit_price AS unit_price,
        d.costo_unitario AS costo_unitario,
        d.margen_porcentaje AS margen_porcentaje,
        d.fecha_ingreso::timestamp AS fecha_ingreso,
        CASE
            WHEN COALESCE(pt.total_quantity, 0) > 0
                THEN ROUND(pt.total_cost / NULLIF(pt.total_quantity, 0), 2)
            ELSE d.costo_unitario
        END AS costo_promedio_ponderado
    FROM devices AS d
    LEFT JOIN purchase_totals AS pt ON pt.device_id = d.id
)
SELECT
    dm.store_id AS store_id,
    s.nombre AS store_name,
    dm.device_id AS device_id,
    dm.sku AS sku,
    dm.device_name AS device_name,
    dm.categoria AS categoria,
    dm.quantity AS quantity,
    dm.costo_promedio_ponderado AS costo_promedio_ponderado,
    ROUND(dm.quantity * dm.unit_price, 2) AS valor_total_producto,
    ROUND(dm.quantity * dm.costo_promedio_ponderado, 2) AS valor_costo_producto,
    ROUND(SUM(dm.quantity * dm.unit_price) OVER (PARTITION BY dm.store_id), 2) AS valor_total_tienda,
    ROUND(SUM(dm.quantity * dm.unit_price) OVER (), 2) AS valor_total_general,
    ROUND(SUM(dm.quantity * dm.costo_promedio_ponderado) OVER (PARTITION BY dm.store_id), 2) AS valor_costo_tienda,
    ROUND(SUM(dm.quantity * dm.costo_promedio_ponderado) OVER (), 2) AS valor_costo_general,
    ROUND(dm.unit_price - dm.costo_promedio_ponderado, 2) AS margen_unitario,
    ROUND(
        CASE
            WHEN dm.unit_price = 0 THEN 0
            ELSE ((dm.unit_price - dm.costo_promedio_ponderado) * 100.0) / dm.unit_price
        END,
        2
    ) AS margen_producto_porcentaje,
    ROUND(SUM(dm.quantity * dm.unit_price) OVER (PARTITION BY dm.categoria), 2) AS valor_total_categoria,
    ROUND(
        SUM(dm.quantity * (dm.unit_price - dm.costo_promedio_ponderado)) OVER (PARTITION BY dm.categoria),
        2
    ) AS margen_categoria_valor,
    ROUND(
        CASE
            WHEN SUM(dm.quantity * dm.unit_price) OVER (PARTITION BY dm.categoria) = 0 THEN 0
            ELSE (
                SUM(dm.quantity * (dm.unit_price - dm.costo_promedio_ponderado)) OVER (PARTITION BY dm.categoria)
                * 100.0
                / NULLIF(SUM(dm.quantity * dm.unit_price) OVER (PARTITION BY dm.categoria), 0)
            )
        END,
        2
    ) AS margen_categoria_porcentaje,
    ROUND(SUM(dm.quantity * (dm.unit_price - dm.costo_promedio_ponderado)) OVER (PARTITION BY dm.store_id), 2) AS margen_total_tienda,
    ROUND(SUM(dm.quantity * (dm.unit_price - dm.costo_promedio_ponderado)) OVER (), 2) AS margen_total_general,
    COALESCE(ss.sold_total_units, 0) AS ventas_totales,
    COALESCE(ss.sold_units_last_30_days, 0) AS ventas_30_dias,
    COALESCE(ss.sold_units_last_90_days, 0) AS ventas_90_dias,
    ss.last_sale_at AS ultima_venta,
    pr.last_purchase_at AS ultima_compra,
    ms.last_movement_at AS ultimo_movimiento,
    ROUND(
        CASE
            WHEN COALESCE(pr.received_last_30_days, 0) > 0 THEN
                COALESCE(ss.sold_units_last_30_days, 0)::numeric
                / NULLIF(pr.received_last_30_days, 0)
            WHEN COALESCE(ss.sold_units_last_30_days, 0) > 0 THEN 1
            ELSE 0
        END,
        2
    ) AS rotacion_30_dias,
    ROUND(
        CASE
            WHEN COALESCE(pr.received_last_90_days, 0) > 0 THEN
                COALESCE(ss.sold_units_last_90_days, 0)::numeric
                / NULLIF(pr.received_last_90_days, 0)
            WHEN COALESCE(ss.sold_units_last_90_days, 0) > 0 THEN 1
            ELSE 0
        END,
        2
    ) AS rotacion_90_dias,
    ROUND(
        CASE
            WHEN COALESCE(pt.total_quantity, 0) > 0 THEN
                COALESCE(ss.sold_total_units, 0)::numeric
                / NULLIF(pt.total_quantity, 0)
            WHEN COALESCE(ss.sold_total_units, 0) > 0 THEN 1
            ELSE 0
        END,
        2
    ) AS rotacion_total,
    CASE
        WHEN GREATEST(
            COALESCE(ss.last_sale_at, TIMESTAMP '1970-01-01'),
            COALESCE(pr.last_purchase_at, TIMESTAMP '1970-01-01'),
            COALESCE(ms.last_movement_at, TIMESTAMP '1970-01-01'),
            COALESCE(dm.fecha_ingreso, TIMESTAMP '1970-01-01')
        ) = TIMESTAMP '1970-01-01' THEN NULL
        ELSE (
            CURRENT_DATE - GREATEST(
                COALESCE(ss.last_sale_at::date, DATE '1970-01-01'),
                COALESCE(pr.last_purchase_at::date, DATE '1970-01-01'),
                COALESCE(ms.last_movement_at::date, DATE '1970-01-01'),
                COALESCE(dm.fecha_ingreso::date, DATE '1970-01-01')
            )
        )
    END AS dias_sin_movimiento
FROM device_metrics AS dm
JOIN sucursales AS s ON s.id_sucursal = dm.store_id
LEFT JOIN purchase_totals AS pt ON pt.device_id = dm.device_id
LEFT JOIN purchase_recent AS pr ON pr.device_id = dm.device_id
LEFT JOIN sales_stats AS ss ON ss.device_id = dm.device_id
LEFT JOIN movement_stats AS ms ON ms.device_id = dm.device_id;
"""

CREATE_VALOR_INVENTARIO_VIEW_SQL_SQLITE = """
CREATE VIEW valor_inventario AS
WITH purchase_totals AS (
    SELECT
        poi.device_id AS device_id,
        SUM(poi.quantity_received) AS total_quantity,
        SUM(poi.quantity_received * poi.unit_cost) AS total_cost
    FROM purchase_order_items AS poi
    GROUP BY poi.device_id
),
purchase_recent AS (
    SELECT
        poi.device_id AS device_id,
        SUM(
            CASE
                WHEN po.created_at >= datetime('now', '-30 day') THEN poi.quantity_received
                ELSE 0
            END
        ) AS received_last_30_days,
        SUM(
            CASE
                WHEN po.created_at >= datetime('now', '-90 day') THEN poi.quantity_received
                ELSE 0
            END
        ) AS received_last_90_days,
        MAX(po.created_at) AS last_purchase_at
    FROM purchase_order_items AS poi
    JOIN purchase_orders AS po ON po.id = poi.purchase_order_id
    GROUP BY poi.device_id
),
sales_stats AS (
    SELECT
        si.device_id AS device_id,
        SUM(si.quantity) AS sold_total_units,
        SUM(
            CASE
                WHEN s.fecha >= datetime('now', '-30 day') THEN si.quantity
                ELSE 0
            END
        ) AS sold_units_last_30_days,
        SUM(
            CASE
                WHEN s.fecha >= datetime('now', '-90 day') THEN si.quantity
                ELSE 0
            END
        ) AS sold_units_last_90_days,
        MAX(s.fecha) AS last_sale_at
    FROM detalle_ventas AS si
    JOIN ventas AS s ON s.id_venta = si.venta_id
    WHERE s.estado <> 'CANCELADA'
    GROUP BY si.device_id
),
movement_stats AS (
    SELECT
        im.producto_id AS device_id,
        MAX(im.fecha) AS last_movement_at
    FROM inventory_movements AS im
    GROUP BY im.producto_id
),
device_metrics AS (
    SELECT
        d.id AS device_id,
        d.sucursal_id AS store_id,
        COALESCE(NULLIF(d.categoria, ''), 'Sin categoría') AS categoria,
        d.sku AS sku,
        d.name AS device_name,
        d.quantity AS quantity,
        d.unit_price AS unit_price,
        d.costo_unitario AS costo_unitario,
        d.margen_porcentaje AS margen_porcentaje,
        datetime(d.fecha_ingreso) AS fecha_ingreso,
        CASE
            WHEN COALESCE(pt.total_quantity, 0) > 0
                THEN ROUND(pt.total_cost / NULLIF(pt.total_quantity, 0), 2)
            ELSE d.costo_unitario
        END AS costo_promedio_ponderado
    FROM devices AS d
    LEFT JOIN purchase_totals AS pt ON pt.device_id = d.id
)
SELECT
    dm.store_id AS store_id,
    s.nombre AS store_name,
    dm.device_id AS device_id,
    dm.sku AS sku,
    dm.device_name AS device_name,
    dm.categoria AS categoria,
    dm.quantity AS quantity,
    dm.costo_promedio_ponderado AS costo_promedio_ponderado,
    ROUND(dm.quantity * dm.unit_price, 2) AS valor_total_producto,
    ROUND(dm.quantity * dm.costo_promedio_ponderado, 2) AS valor_costo_producto,
    ROUND(SUM(dm.quantity * dm.unit_price) OVER (PARTITION BY dm.store_id), 2) AS valor_total_tienda,
    ROUND(SUM(dm.quantity * dm.unit_price) OVER (), 2) AS valor_total_general,
    ROUND(SUM(dm.quantity * dm.costo_promedio_ponderado) OVER (PARTITION BY dm.store_id), 2) AS valor_costo_tienda,
    ROUND(SUM(dm.quantity * dm.costo_promedio_ponderado) OVER (), 2) AS valor_costo_general,
    ROUND(dm.unit_price - dm.costo_promedio_ponderado, 2) AS margen_unitario,
    ROUND(
        CASE
            WHEN dm.unit_price = 0 THEN 0
            ELSE ((dm.unit_price - dm.costo_promedio_ponderado) * 100.0) / dm.unit_price
        END,
        2
    ) AS margen_producto_porcentaje,
    ROUND(SUM(dm.quantity * dm.unit_price) OVER (PARTITION BY dm.categoria), 2) AS valor_total_categoria,
    ROUND(
        SUM(dm.quantity * (dm.unit_price - dm.costo_promedio_ponderado)) OVER (PARTITION BY dm.categoria),
        2
    ) AS margen_categoria_valor,
    ROUND(
        CASE
            WHEN SUM(dm.quantity * dm.unit_price) OVER (PARTITION BY dm.categoria) = 0 THEN 0
            ELSE (
                SUM(dm.quantity * (dm.unit_price - dm.costo_promedio_ponderado)) OVER (PARTITION BY dm.categoria)
                * 100.0
                / NULLIF(SUM(dm.quantity * dm.unit_price) OVER (PARTITION BY dm.categoria), 0)
            )
        END,
        2
    ) AS margen_categoria_porcentaje,
    ROUND(SUM(dm.quantity * (dm.unit_price - dm.costo_promedio_ponderado)) OVER (PARTITION BY dm.store_id), 2) AS margen_total_tienda,
    ROUND(SUM(dm.quantity * (dm.unit_price - dm.costo_promedio_ponderado)) OVER (), 2) AS margen_total_general,
    COALESCE(ss.sold_total_units, 0) AS ventas_totales,
    COALESCE(ss.sold_units_last_30_days, 0) AS ventas_30_dias,
    COALESCE(ss.sold_units_last_90_days, 0) AS ventas_90_dias,
    ss.last_sale_at AS ultima_venta,
    pr.last_purchase_at AS ultima_compra,
    ms.last_movement_at AS ultimo_movimiento,
    ROUND(
        CASE
            WHEN COALESCE(pr.received_last_30_days, 0) > 0 THEN
                CAST(COALESCE(ss.sold_units_last_30_days, 0) AS REAL)
                / NULLIF(pr.received_last_30_days, 0)
            WHEN COALESCE(ss.sold_units_last_30_days, 0) > 0 THEN 1
            ELSE 0
        END,
        2
    ) AS rotacion_30_dias,
    ROUND(
        CASE
            WHEN COALESCE(pr.received_last_90_days, 0) > 0 THEN
                CAST(COALESCE(ss.sold_units_last_90_days, 0) AS REAL)
                / NULLIF(pr.received_last_90_days, 0)
            WHEN COALESCE(ss.sold_units_last_90_days, 0) > 0 THEN 1
            ELSE 0
        END,
        2
    ) AS rotacion_90_dias,
    ROUND(
        CASE
            WHEN COALESCE(pt.total_quantity, 0) > 0 THEN
                CAST(COALESCE(ss.sold_total_units, 0) AS REAL)
                / NULLIF(pt.total_quantity, 0)
            WHEN COALESCE(ss.sold_total_units, 0) > 0 THEN 1
            ELSE 0
        END,
        2
    ) AS rotacion_total,
    CASE
        WHEN MAX(
            MAX(
                COALESCE(datetime(ss.last_sale_at), '1970-01-01 00:00:00'),
                COALESCE(datetime(pr.last_purchase_at), '1970-01-01 00:00:00')
            ),
            MAX(
                COALESCE(datetime(ms.last_movement_at), '1970-01-01 00:00:00'),
                COALESCE(datetime(dm.fecha_ingreso), '1970-01-01 00:00:00')
            )
        ) = '1970-01-01 00:00:00' THEN NULL
        ELSE CAST(
            JULIANDAY('now') - JULIANDAY(
                MAX(
                    MAX(
                        COALESCE(datetime(ss.last_sale_at), '1970-01-01 00:00:00'),
                        COALESCE(datetime(pr.last_purchase_at), '1970-01-01 00:00:00')
                    ),
                    MAX(
                        COALESCE(datetime(ms.last_movement_at), '1970-01-01 00:00:00'),
                        COALESCE(datetime(dm.fecha_ingreso), '1970-01-01 00:00:00')
                    )
                )
            ) AS INTEGER
        )
    END AS dias_sin_movimiento
FROM device_metrics AS dm
JOIN sucursales AS s ON s.id_sucursal = dm.store_id
LEFT JOIN purchase_totals AS pt ON pt.device_id = dm.device_id
LEFT JOIN purchase_recent AS pr ON pr.device_id = dm.device_id
LEFT JOIN sales_stats AS ss ON ss.device_id = dm.device_id
LEFT JOIN movement_stats AS ms ON ms.device_id = dm.device_id;
"""

# Compatibilidad hacia atrás para migraciones existentes que importan esta constante
CREATE_VALOR_INVENTARIO_VIEW_SQL = CREATE_VALOR_INVENTARIO_VIEW_SQL_POSTGRES

DROP_VALOR_INVENTARIO_VIEW_SQL = "DROP VIEW IF EXISTS valor_inventario"


def create_valor_inventario_view(connection: Connection) -> None:
    """Crea o reemplaza la vista de valoración de inventario."""

    dialect = connection.dialect.name
    if dialect == "sqlite":
        create_sql = CREATE_VALOR_INVENTARIO_VIEW_SQL_SQLITE
    else:
        create_sql = CREATE_VALOR_INVENTARIO_VIEW_SQL_POSTGRES

    with connection.begin():
        connection.execute(text(DROP_VALOR_INVENTARIO_VIEW_SQL))
        connection.execute(text(create_sql))


def drop_valor_inventario_view(connection: Connection) -> None:
    """Elimina la vista de valoración de inventario si existe."""

    with connection.begin():
        connection.execute(text(DROP_VALOR_INVENTARIO_VIEW_SQL))
