"""Actualiza vista valor_inventario con métricas extendidas."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from backend.app.db.valor_inventario_view import (
    CREATE_VALOR_INVENTARIO_VIEW_SQL,
    DROP_VALOR_INVENTARIO_VIEW_SQL,
)

# revision identifiers, used by Alembic.
revision = "202503150001"
down_revision = "202503010002"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


OLD_CREATE_VALOR_INVENTARIO_VIEW_SQL = """
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
    ROUND(SUM(dm.quantity * dm.unit_price) OVER (PARTITION BY dm.store_id), 2) AS valor_total_tienda,
    ROUND(SUM(dm.quantity * dm.unit_price) OVER (), 2) AS valor_total_general,
    ROUND(dm.unit_price - dm.costo_promedio_ponderado, 2) AS margen_unitario,
    ROUND(
        CASE
            WHEN dm.unit_price = 0 THEN 0
            ELSE ((dm.unit_price - dm.costo_promedio_ponderado) / dm.unit_price) * 100
        END,
        2
    ) AS margen_producto_porcentaje,
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
    ) AS margen_categoria_porcentaje
FROM device_metrics AS dm
JOIN stores AS s ON s.id = dm.store_id;
"""


OLD_DROP_VALOR_INVENTARIO_VIEW_SQL = "DROP VIEW IF EXISTS valor_inventario"


def upgrade() -> None:
    op.execute(sa.text(DROP_VALOR_INVENTARIO_VIEW_SQL))
    op.execute(sa.text(CREATE_VALOR_INVENTARIO_VIEW_SQL))


def downgrade() -> None:
    op.execute(sa.text(OLD_DROP_VALOR_INVENTARIO_VIEW_SQL))
    op.execute(sa.text(OLD_CREATE_VALOR_INVENTARIO_VIEW_SQL))
