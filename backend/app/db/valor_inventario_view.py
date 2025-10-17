"""Utilidades para la vista materializada de valoración de inventario."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

VIEW_NAME = "valor_inventario"

CREATE_VALOR_INVENTARIO_VIEW_SQL = """
CREATE VIEW valor_inventario AS
WITH purchase_totals AS (
    SELECT
        poi.device_id AS device_id,
        SUM(poi.quantity_received) AS total_quantity,
        SUM(poi.quantity_received * poi.unit_cost) AS total_cost
    FROM purchase_order_items AS poi
    GROUP BY poi.device_id
),
device_metrics AS (
    SELECT
        d.id AS device_id,
        d.store_id AS store_id,
        COALESCE(NULLIF(d.categoria, ''), 'Sin categoría') AS categoria,
        d.sku AS sku,
        d.name AS device_name,
        d.quantity AS quantity,
        d.unit_price AS unit_price,
        d.costo_unitario AS costo_unitario,
        d.margen_porcentaje AS margen_porcentaje,
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
    s.name AS store_name,
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
            ELSE ((dm.unit_price - dm.costo_promedio_ponderado) / dm.unit_price) * 100
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
                / NULLIF(SUM(dm.quantity * dm.unit_price) OVER (PARTITION BY dm.categoria), 0)
            ) * 100
        END,
        2
    ) AS margen_categoria_porcentaje,
    ROUND(SUM(dm.quantity * (dm.unit_price - dm.costo_promedio_ponderado)) OVER (PARTITION BY dm.store_id), 2) AS margen_total_tienda,
    ROUND(SUM(dm.quantity * (dm.unit_price - dm.costo_promedio_ponderado)) OVER (), 2) AS margen_total_general
FROM device_metrics AS dm
JOIN stores AS s ON s.id = dm.store_id;
"""

DROP_VALOR_INVENTARIO_VIEW_SQL = "DROP VIEW IF EXISTS valor_inventario"


def create_valor_inventario_view(connection: Connection) -> None:
    """Crea o reemplaza la vista de valoración de inventario."""

    connection.execute(text(DROP_VALOR_INVENTARIO_VIEW_SQL))
    connection.execute(text(CREATE_VALOR_INVENTARIO_VIEW_SQL))


def drop_valor_inventario_view(connection: Connection) -> None:
    """Elimina la vista de valoración de inventario si existe."""

    connection.execute(text(DROP_VALOR_INVENTARIO_VIEW_SQL))
