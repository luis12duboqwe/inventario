"""customer segments snapshot table"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202502150011"
down_revision = "202502150010"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_segment_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("annual_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("orders_last_year", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_ticket", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("frequency_label", sa.String(length=30), nullable=False, server_default="sin_datos"),
        sa.Column("segment_labels", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("last_sale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint([
            "customer_id"
        ], ["clientes.id_cliente"], ondelete="CASCADE"),
        sa.UniqueConstraint("customer_id", name="uq_customer_segment_snapshots_customer"),
    )
    op.create_index(
        op.f("ix_customer_segment_snapshots_customer_id"),
        "customer_segment_snapshots",
        ["customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_customer_segment_snapshots_customer_id"), table_name="customer_segment_snapshots")
    op.drop_table("customer_segment_snapshots")
