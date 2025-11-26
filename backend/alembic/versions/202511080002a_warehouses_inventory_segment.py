"""Create warehouses table and link inventory (no-op duplicate)

Revision ID: 202511080002a
Revises: 202511080002
Create Date: 2025-11-08 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
from backend.app.db.valor_inventario_view import (
    create_valor_inventario_view,
    drop_valor_inventario_view,
)
from backend.app.db.movimientos_inventario_view import (
    create_movimientos_inventario_view,
    drop_movimientos_inventario_view,
)

# revision identifiers, used by Alembic.
revision = "202511080002a"
down_revision = "202511080002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: esta revisión duplicaba la creación de warehouses.
    connection = op.get_bind()
    # Aseguramos que las vistas estén actualizadas sin tocar estructuras.
    drop_movimientos_inventario_view(connection)
    drop_valor_inventario_view(connection)
    create_movimientos_inventario_view(connection)
    create_valor_inventario_view(connection)


def downgrade() -> None:
    # No-op intencional para no afectar estructuras existentes.
    pass
