"""Agregar columnas de desglose de montos en ventas"""

from alembic import op
import sqlalchemy as sa


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


def downgrade() -> None:
    op.drop_column("sales", "tax_amount")
    op.drop_column("sales", "subtotal_amount")
