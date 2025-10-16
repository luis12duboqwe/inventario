"""Refuerza los movimientos de inventario con origen, destino y comentario."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202502150010_inventory_movements_enhancements"
down_revision = "202502150009_inventory_catalog_extensions"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.drop_index("ix_inventory_movements_performed_by_id", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_device_id", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_store_id", table_name="inventory_movements")

    with op.batch_alter_table("inventory_movements", schema=None) as batch_op:
        batch_op.alter_column("store_id", new_column_name="tienda_destino_id")
        batch_op.alter_column("device_id", new_column_name="producto_id")
        batch_op.alter_column("movement_type", new_column_name="tipo_movimiento")
        batch_op.alter_column("quantity", new_column_name="cantidad")
        batch_op.alter_column("reason", new_column_name="comentario")
        batch_op.alter_column("unit_cost", new_column_name="costo_unitario")
        batch_op.alter_column("performed_by_id", new_column_name="usuario_id")
        batch_op.alter_column("created_at", new_column_name="fecha")
        batch_op.add_column(sa.Column("tienda_origen_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_inventory_movements_tienda_origen",
            "stores",
            ["tienda_origen_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index(
        "ix_inventory_movements_tienda_destino_id",
        "inventory_movements",
        ["tienda_destino_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_movements_producto_id",
        "inventory_movements",
        ["producto_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_movements_usuario_id",
        "inventory_movements",
        ["usuario_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_movements_tienda_origen_id",
        "inventory_movements",
        ["tienda_origen_id"],
        unique=False,
    )

    op.execute(
        "UPDATE inventory_movements SET tienda_origen_id = tienda_destino_id WHERE tipo_movimiento = 'salida'"
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_movements_tienda_origen_id", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_usuario_id", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_producto_id", table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_tienda_destino_id", table_name="inventory_movements")

    with op.batch_alter_table("inventory_movements", schema=None) as batch_op:
        batch_op.drop_constraint("fk_inventory_movements_tienda_origen", type_="foreignkey")
        batch_op.drop_column("tienda_origen_id")
        batch_op.alter_column("fecha", new_column_name="created_at")
        batch_op.alter_column("usuario_id", new_column_name="performed_by_id")
        batch_op.alter_column("costo_unitario", new_column_name="unit_cost")
        batch_op.alter_column("comentario", new_column_name="reason")
        batch_op.alter_column("cantidad", new_column_name="quantity")
        batch_op.alter_column("tipo_movimiento", new_column_name="movement_type")
        batch_op.alter_column("producto_id", new_column_name="device_id")
        batch_op.alter_column("tienda_destino_id", new_column_name="store_id")

    op.create_index(
        "ix_inventory_movements_store_id",
        "inventory_movements",
        ["store_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_movements_device_id",
        "inventory_movements",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_movements_performed_by_id",
        "inventory_movements",
        ["performed_by_id"],
        unique=False,
    )
