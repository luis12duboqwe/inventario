"""Crea tablas de listas de precios y vincula sucursales/clientes.

Revision ID: 202511070004
Revises: 202511070003
Create Date: 2025-11-07 13:30:00 UTC

Nota: Compatible con v2.2.0 sin alterar etiquetas de versión del producto.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202511070004"
down_revision = "202511070003"
branch_labels = None
depends_on = None


price_lists_scope_uq = "uq_price_lists_scope_name"
price_list_items_uq = "uq_price_list_items_price_device"


currency_default = sa.text("'MXN'")


def upgrade() -> None:
    op.create_table(
        "price_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default=currency_default),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
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
            ["store_id"], ["sucursales.id_sucursal"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["clientes.id_cliente"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("name", "store_id", "customer_id", name=price_lists_scope_uq),
    )
    op.create_index(
        "ix_price_lists_name",
        "price_lists",
        ["name"],
    )
    op.create_index(
        "ix_price_lists_is_active",
        "price_lists",
        ["is_active"],
    )
    op.create_index(
        "ix_price_lists_store_id",
        "price_lists",
        ["store_id"],
    )
    op.create_index(
        "ix_price_lists_customer_id",
        "price_lists",
        ["customer_id"],
    )

    op.create_table(
        "price_list_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("price_list_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=True),
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
            ["price_list_id"], ["price_lists.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("price_list_id", "device_id", name=price_list_items_uq),
    )
    op.create_index(
        "ix_price_list_items_list_device",
        "price_list_items",
        ["price_list_id", "device_id"],
    )
    op.create_index(
        "ix_price_list_items_price_list",
        "price_list_items",
        ["price_list_id"],
    )
    op.create_index(
        "ix_price_list_items_device",
        "price_list_items",
        ["device_id"],
    )



def downgrade() -> None:
    op.drop_index("ix_price_list_items_device", table_name="price_list_items")
    op.drop_index("ix_price_list_items_price_list", table_name="price_list_items")
    op.drop_index("ix_price_list_items_list_device", table_name="price_list_items")
    op.drop_table("price_list_items")

    op.drop_index("ix_price_lists_customer_id", table_name="price_lists")
    op.drop_index("ix_price_lists_store_id", table_name="price_lists")
    op.drop_index("ix_price_lists_is_active", table_name="price_lists")
    op.drop_index("ix_price_lists_name", table_name="price_lists")
    op.drop_table("price_lists")
