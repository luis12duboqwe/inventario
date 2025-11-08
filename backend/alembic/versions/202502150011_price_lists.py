"""Crea tablas para listas de precios y sus partidas."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202502150011_price_lists"
down_revision = "202502150010_inventory_movements_enhancements"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "price_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["sucursales.id_sucursal"],
            name="fk_price_lists_store",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["clientes.id_cliente"],
            name="fk_price_lists_customer",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "name", "store_id", "customer_id", name="uq_price_lists_scope_name"
        ),
    )
    op.create_index(
        "ix_price_lists_priority",
        "price_lists",
        ["priority"],
        unique=False,
    )
    op.create_index(
        "ix_price_lists_store_id",
        "price_lists",
        ["store_id"],
        unique=False,
    )
    op.create_index(
        "ix_price_lists_customer_id",
        "price_lists",
        ["customer_id"],
        unique=False,
    )

    op.create_table(
        "price_list_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("price_list_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column(
            "price",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "currency",
            sa.String(length=8),
            nullable=False,
            server_default="MXN",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["price_list_id"],
            ["price_lists.id"],
            name="fk_price_list_items_list",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name="fk_price_list_items_device",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "price_list_id", "device_id", name="uq_price_list_items_device"
        ),
    )
    op.create_index(
        "ix_price_list_items_price_list_id",
        "price_list_items",
        ["price_list_id"],
        unique=False,
    )
    op.create_index(
        "ix_price_list_items_device_id",
        "price_list_items",
        ["device_id"],
        unique=False,
    )



def downgrade() -> None:
    op.drop_index(
        "ix_price_list_items_device_id", table_name="price_list_items"
    )
    op.drop_index(
        "ix_price_list_items_price_list_id", table_name="price_list_items"
    )
    op.drop_table("price_list_items")

    op.drop_index("ix_price_lists_customer_id", table_name="price_lists")
    op.drop_index("ix_price_lists_store_id", table_name="price_lists")
    op.drop_index("ix_price_lists_priority", table_name="price_lists")
    op.drop_table("price_lists")
