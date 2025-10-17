"""add pos tables and sale amounts"""

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
        "sales",
        sa.Column(
            "subtotal_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "sales",
        sa.Column(
            "tax_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )

    op.alter_column("sales", "subtotal_amount", server_default=None)
    op.alter_column("sales", "tax_amount", server_default=None)

    op.create_table(
        "pos_configs",
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("invoice_prefix", sa.String(length=12), nullable=False),
        sa.Column("printer_name", sa.String(length=120), nullable=True),
        sa.Column("printer_profile", sa.String(length=255), nullable=True),
        sa.Column("quick_product_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("store_id"),
    )
    op.create_index(op.f("ix_pos_configs_store_id"), "pos_configs", ["store_id"], unique=True)

    op.create_table(
        "pos_draft_sales",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pos_draft_sales_id"), "pos_draft_sales", ["id"], unique=False)
    op.create_index(op.f("ix_pos_draft_sales_store_id"), "pos_draft_sales", ["store_id"], unique=False)

    op.alter_column("pos_configs", "tax_rate", server_default=None)
    op.alter_column("pos_configs", "quick_product_ids", server_default=None)
    op.alter_column("pos_draft_sales", "payload", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_pos_draft_sales_store_id"), table_name="pos_draft_sales")
    op.drop_index(op.f("ix_pos_draft_sales_id"), table_name="pos_draft_sales")
    op.drop_table("pos_draft_sales")

    op.drop_index(op.f("ix_pos_configs_store_id"), table_name="pos_configs")
    op.drop_table("pos_configs")

    op.drop_column("sales", "tax_amount")
    op.drop_column("sales", "subtotal_amount")
