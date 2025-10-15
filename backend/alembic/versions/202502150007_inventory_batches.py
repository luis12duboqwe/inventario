"""Agrega lotes de proveedores y valuación instantánea de inventario."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202502150007"
down_revision = "202502150006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column(
            "inventory_value",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "inventory_movements",
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
    )

    op.create_table(
        "supplier_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("batch_code", sa.String(length=80), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_id", "batch_code", name="uq_supplier_batch_code"),
    )
    op.create_index(op.f("ix_supplier_batches_id"), "supplier_batches", ["id"], unique=False)
    op.create_index(
        op.f("ix_supplier_batches_supplier_id"),
        "supplier_batches",
        ["supplier_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_batches_store_id"),
        "supplier_batches",
        ["store_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_batches_device_id"),
        "supplier_batches",
        ["device_id"],
        unique=False,
    )

    op.execute("UPDATE stores SET inventory_value = 0")


def downgrade() -> None:
    op.drop_index(op.f("ix_supplier_batches_device_id"), table_name="supplier_batches")
    op.drop_index(op.f("ix_supplier_batches_store_id"), table_name="supplier_batches")
    op.drop_index(op.f("ix_supplier_batches_supplier_id"), table_name="supplier_batches")
    op.drop_index(op.f("ix_supplier_batches_id"), table_name="supplier_batches")
    op.drop_table("supplier_batches")

    op.drop_column("inventory_movements", "unit_cost")
    op.drop_column("stores", "inventory_value")
