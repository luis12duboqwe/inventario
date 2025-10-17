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

    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            WITH item_totals AS (
                SELECT
                    sale_id,
                    COALESCE(SUM(total_line), 0) AS subtotal
                FROM sale_items
                GROUP BY sale_id
            )
            UPDATE sales AS s
            SET subtotal_amount = ROUND(
                CASE
                    WHEN t.subtotal > 0 THEN t.subtotal
                    ELSE s.total_amount
                END,
                2
            )
            FROM item_totals AS t
            WHERE s.id = t.sale_id
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE sales
            SET subtotal_amount = total_amount
            WHERE subtotal_amount IS NULL OR subtotal_amount = 0
            """
        )
    )

    bind.execute(
        sa.text(
            """
            UPDATE sales
            SET
                tax_amount = ROUND(
                    CASE
                        WHEN total_amount >= subtotal_amount THEN total_amount - subtotal_amount
                        ELSE 0
                    END,
                    2
                ),
                subtotal_amount = ROUND(
                    CASE
                        WHEN total_amount < subtotal_amount THEN total_amount
                        ELSE subtotal_amount
                    END,
                    2
                )
            """
        )
    )

    op.alter_column(
        "sales",
        "subtotal_amount",
        server_default=None,
        existing_type=sa.Numeric(12, 2),
    )
    op.alter_column(
        "sales",
        "tax_amount",
        server_default=None,
        existing_type=sa.Numeric(12, 2),
    )

    op.create_table(
        "pos_config",
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("invoice_prefix", sa.String(length=12), nullable=False),
        sa.Column("printer_name", sa.String(length=120), nullable=True),
        sa.Column("printer_profile", sa.String(length=255), nullable=True),
        sa.Column(
            "quick_product_ids",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("store_id"),
    )
    op.create_index(op.f("ix_pos_config_store_id"), "pos_config", ["store_id"], unique=True)

    op.create_table(
        "pos_draft_sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
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
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pos_draft_sales_id"), "pos_draft_sales", ["id"], unique=False)
    op.create_index(op.f("ix_pos_draft_sales_store_id"), "pos_draft_sales", ["store_id"], unique=False)



def downgrade() -> None:
    op.drop_index(op.f("ix_pos_draft_sales_store_id"), table_name="pos_draft_sales")
    op.drop_index(op.f("ix_pos_draft_sales_id"), table_name="pos_draft_sales")
    op.drop_table("pos_draft_sales")

    op.drop_index(op.f("ix_pos_config_store_id"), table_name="pos_config")
    op.drop_table("pos_config")

    op.drop_column("sales", "tax_amount")
    op.drop_column("sales", "subtotal_amount")
