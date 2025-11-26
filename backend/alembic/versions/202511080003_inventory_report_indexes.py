"""
Optimiza índices para movimientos y búsquedas por SKU.

Revision ID: 202511080003
Revises: 202511080002a
Create Date: 2025-11-08 01:10:00 UTC

Nota: Compatible con v2.2.0 sin alterar etiquetas de versión del producto.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202511080003"
down_revision = "202511080002a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_inventory_movements_store_fecha",
        "inventory_movements",
        ["sucursal_destino_id", "fecha"],
    )
    op.create_index(
        "ix_inventory_movements_fecha",
        "inventory_movements",
        ["fecha"],
    )
    op.create_index(
        "ix_devices_sku_lower",
        "devices",
        [sa.text("lower(sku)")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_devices_sku_lower", table_name="devices")
    op.drop_index("ix_inventory_movements_fecha", table_name="inventory_movements")
    op.drop_index(
        "ix_inventory_movements_store_fecha", table_name="inventory_movements"
    )
