"""Utilidades para la vista de compatibilidad movimientos_inventario."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

VIEW_NAME = "movimientos_inventario"

CREATE_MOVIMIENTOS_INVENTARIO_VIEW_SQL = """
CREATE VIEW movimientos_inventario AS
SELECT
    id,
    sucursal_destino_id AS tienda_destino_id,
    sucursal_origen_id AS tienda_origen_id,
    producto_id,
    CASE
        WHEN tipo_movimiento = 'IN' THEN 'entrada'
        WHEN tipo_movimiento = 'OUT' THEN 'salida'
        WHEN tipo_movimiento = 'ADJUST' THEN 'ajuste'
        ELSE tipo_movimiento
    END AS tipo_movimiento,
    cantidad,
    comentario,
    costo_unitario,
    usuario_id,
    fecha
FROM inventory_movements;
"""

DROP_MOVIMIENTOS_INVENTARIO_VIEW_SQL = "DROP VIEW IF EXISTS movimientos_inventario"


def create_movimientos_inventario_view(connection: Connection) -> None:
    """Crea o reemplaza la vista con alias en español para movimientos."""

    with connection.begin():
        connection.execute(text(DROP_MOVIMIENTOS_INVENTARIO_VIEW_SQL))
        connection.execute(text(CREATE_MOVIMIENTOS_INVENTARIO_VIEW_SQL))


def drop_movimientos_inventario_view(connection: Connection) -> None:
    """Elimina la vista movimientos_inventario si existe."""

    with connection.begin():
        connection.execute(text(DROP_MOVIMIENTOS_INVENTARIO_VIEW_SQL))
