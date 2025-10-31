"""Agregar columna unit_price para dispositivos y preparar métricas."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202502150002"
down_revision = "202502150001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.execute("UPDATE devices SET unit_price = 0 WHERE unit_price IS NULL")
    op.alter_column("devices", "unit_price", server_default=None)


def downgrade() -> None:
    op.drop_column("devices", "unit_price")
