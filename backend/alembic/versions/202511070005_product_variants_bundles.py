"""Crear tablas para variantes de productos y combos corporativos."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202511070005_product_variants_bundles"
down_revision = "202511070004"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("variant_sku", sa.String(length=80), nullable=False),
        sa.Column("barcode", sa.String(length=120), nullable=True),
        sa.Column("unit_price_override", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
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
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "device_id", "variant_sku", name="uq_product_variants_device_sku"
        ),
    )
    op.create_index(
        "ix_product_variants_device_id",
        "product_variants",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        "ix_product_variants_variant_sku",
        "product_variants",
        ["variant_sku"],
        unique=False,
    )

    op.create_table(
        "product_bundles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("bundle_sku", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "base_price",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text("'0'")
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
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
        sa.UniqueConstraint(
            "store_id", "bundle_sku", name="uq_product_bundles_store_sku"
        ),
    )
    op.create_index(
        "ix_product_bundles_store_id",
        "product_bundles",
        ["store_id"],
        unique=False,
    )
    op.create_index(
        "ix_product_bundles_bundle_sku",
        "product_bundles",
        ["bundle_sku"],
        unique=False,
    )

    op.create_table(
        "product_bundle_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bundle_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column(
            "quantity",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["bundle_id"], ["product_bundles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["product_variants.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_product_bundle_items_bundle_id",
        "product_bundle_items",
        ["bundle_id"],
        unique=False,
    )
    op.create_index(
        "ix_product_bundle_items_device_id",
        "product_bundle_items",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        "ix_product_bundle_items_variant_id",
        "product_bundle_items",
        ["variant_id"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column("product_variants", "is_default", server_default=None)
        op.alter_column("product_variants", "is_active", server_default=None)
        op.alter_column("product_variants", "created_at", server_default=None)
        op.alter_column("product_variants", "updated_at", server_default=None)
        op.alter_column("product_bundles", "base_price", server_default=None)
        op.alter_column("product_bundles", "is_active", server_default=None)
        op.alter_column("product_bundles", "created_at", server_default=None)
        op.alter_column("product_bundles", "updated_at", server_default=None)
        op.alter_column("product_bundle_items", "quantity", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_product_bundle_items_variant_id", table_name="product_bundle_items")
    op.drop_index("ix_product_bundle_items_device_id", table_name="product_bundle_items")
    op.drop_index("ix_product_bundle_items_bundle_id", table_name="product_bundle_items")
    op.drop_table("product_bundle_items")

    op.drop_index("ix_product_bundles_bundle_sku", table_name="product_bundles")
    op.drop_index("ix_product_bundles_store_id", table_name="product_bundles")
    op.drop_table("product_bundles")

    op.drop_index("ix_product_variants_variant_sku", table_name="product_variants")
    op.drop_index("ix_product_variants_device_id", table_name="product_variants")
    op.drop_table("product_variants")
