"""Create warehouses table and link inventory

Revision ID: 202511080002
Revises: 202511080001
Create Date: 2025-11-08 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from backend.app.db.valor_inventario_view import (
    create_valor_inventario_view,
    drop_valor_inventario_view,
)
from backend.app.db.movimientos_inventario_view import (
    create_movimientos_inventario_view,
    drop_movimientos_inventario_view,
)

# revision identifiers, used by Alembic.
revision = "202511080002"
down_revision = "202511080001"
branch_labels = None
depends_on = None


def _create_default_warehouses(connection: sa.engine.Connection) -> dict[int, int]:
    stores = connection.execute(sa.text("SELECT id_sucursal, nombre FROM sucursales"))
    mapping: dict[int, int] = {}
    for store_id, name in stores:
        timestamp_expr = "CURRENT_TIMESTAMP"
        warehouse_id = connection.execute(
            sa.text(
                """
                INSERT INTO warehouses (store_id, name, code, is_default, created_at)
                VALUES (:store_id, :name, :code, true, {timestamp})
                RETURNING id
                """
                .format(timestamp=timestamp_expr)
            ),
            {"store_id": store_id, "name": "Default", "code": f"DEF-{store_id}"},
        ).scalar_one()
        mapping[store_id] = warehouse_id
    return mapping


def upgrade() -> None:
    connection = op.get_bind()
    drop_valor_inventario_view(connection)
    drop_movimientos_inventario_view(connection)

    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["store_id"], ["sucursales.id_sucursal"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "code", name=op.f("uq_warehouse_store_code")),
        sa.UniqueConstraint("store_id", "name", name=op.f("uq_warehouse_store_name")),
    )
    op.create_index(op.f("ix_warehouses_store_id"), "warehouses", ["store_id"], unique=False)

    with op.batch_alter_table("devices", reflect_kwargs={"resolve_fks": False}) as batch_op:
        batch_op.add_column(sa.Column("warehouse_id", sa.Integer(), nullable=True))
        batch_op.create_index(op.f("ix_devices_warehouse_id"), ["warehouse_id"], unique=False)
        batch_op.drop_constraint("uq_devices_store_sku", type_="unique")
        batch_op.create_unique_constraint(
            op.f("uq_devices_store_warehouse_sku"),
            ["sucursal_id", "warehouse_id", "sku"],
        )
        batch_op.create_foreign_key(
            op.f("devices_warehouse_id_fkey"),
            "warehouses",
            ["warehouse_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table(
        "inventory_movements", reflect_kwargs={"resolve_fks": False}
    ) as batch_op:
        batch_op.add_column(sa.Column("warehouse_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("source_warehouse_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            op.f("ix_inventory_movements_warehouse_id"), ["warehouse_id"], unique=False
        )
        batch_op.create_index(
            op.f("ix_inventory_movements_source_warehouse_id"), ["source_warehouse_id"], unique=False
        )
        batch_op.create_foreign_key(
            op.f("inventory_movements_warehouse_id_fkey"),
            "warehouses",
            ["warehouse_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            op.f("inventory_movements_source_warehouse_id_fkey"),
            "warehouses",
            ["source_warehouse_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("sale_returns", reflect_kwargs={"resolve_fks": False}) as batch_op:
        batch_op.drop_constraint("sale_returns_warehouse_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            op.f("sale_returns_warehouse_id_fkey"),
            "warehouses",
            ["warehouse_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table(
        "purchase_returns", reflect_kwargs={"resolve_fks": False}
    ) as batch_op:
        batch_op.drop_constraint("purchase_returns_warehouse_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            op.f("purchase_returns_warehouse_id_fkey"),
            "warehouses",
            ["warehouse_id"],
            ["id"],
            ondelete="SET NULL",
        )

    warehouse_mapping = _create_default_warehouses(connection)
    for store_id, warehouse_id in warehouse_mapping.items():
        op.execute(
            sa.text(
                "UPDATE devices SET warehouse_id = :warehouse_id WHERE sucursal_id = :store_id"
            ).bindparams(warehouse_id=warehouse_id, store_id=store_id)
        )
        op.execute(
            sa.text(
                """
                UPDATE sale_returns
                SET warehouse_id = :warehouse_id
                WHERE venta_id IN (
                    SELECT id_venta FROM ventas WHERE sucursal_id = :store_id
                )
                """
            ).bindparams(warehouse_id=warehouse_id, store_id=store_id)
        )
        op.execute(
            sa.text(
                "UPDATE purchase_returns SET warehouse_id = :warehouse_id WHERE purchase_order_id IN (SELECT id FROM purchase_orders WHERE sucursal_id = :store_id)"
            ).bindparams(warehouse_id=warehouse_id, store_id=store_id)
        )
        op.execute(
            sa.text(
                "UPDATE inventory_movements SET warehouse_id = :warehouse_id WHERE sucursal_destino_id = :store_id"
            ).bindparams(warehouse_id=warehouse_id, store_id=store_id)
        )
        op.execute(
            sa.text(
                "UPDATE inventory_movements SET source_warehouse_id = :warehouse_id WHERE sucursal_origen_id = :store_id"
            ).bindparams(warehouse_id=warehouse_id, store_id=store_id)
        )

    if connection.dialect.name != "sqlite":
        op.alter_column("devices", "warehouse_id", existing_type=sa.Integer(), nullable=True)
        op.alter_column(
            "sale_returns", "warehouse_id", existing_type=sa.Integer(), nullable=True
        )
        op.alter_column(
            "purchase_returns", "warehouse_id", existing_type=sa.Integer(), nullable=True
        )

    create_movimientos_inventario_view(connection)
    create_valor_inventario_view(connection)


def downgrade() -> None:
    op.drop_constraint(op.f("devices_warehouse_id_fkey"), "devices", type_="foreignkey")
    op.drop_constraint(op.f("inventory_movements_source_warehouse_id_fkey"), "inventory_movements", type_="foreignkey")
    op.drop_constraint(op.f("inventory_movements_warehouse_id_fkey"), "inventory_movements", type_="foreignkey")
    op.drop_constraint(op.f("purchase_returns_warehouse_id_fkey"), "purchase_returns", type_="foreignkey")
    op.drop_constraint(op.f("sale_returns_warehouse_id_fkey"), "sale_returns", type_="foreignkey")
    op.create_foreign_key(
        "sale_returns_warehouse_id_fkey",
        "sale_returns",
        "sucursales",
        ["warehouse_id"],
        ["id_sucursal"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "purchase_returns_warehouse_id_fkey",
        "purchase_returns",
        "sucursales",
        ["warehouse_id"],
        ["id_sucursal"],
        ondelete="SET NULL",
    )
    op.drop_index(op.f("ix_inventory_movements_source_warehouse_id"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_warehouse_id"), table_name="inventory_movements")
    op.drop_column("inventory_movements", "source_warehouse_id")
    op.drop_column("inventory_movements", "warehouse_id")
    op.drop_constraint(op.f("uq_devices_store_warehouse_sku"), "devices", type_="unique")
    op.create_unique_constraint("uq_devices_store_sku", "devices", ["sucursal_id", "sku"])
    op.drop_index(op.f("ix_devices_warehouse_id"), table_name="devices")
    op.drop_column("devices", "warehouse_id")
    op.drop_index(op.f("ix_warehouses_store_id"), table_name="warehouses")
    op.drop_table("warehouses")
