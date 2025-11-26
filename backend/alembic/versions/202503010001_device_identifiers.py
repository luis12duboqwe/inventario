"""Agrega tabla para identificadores extendidos de dispositivos."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202503010001"
down_revision = "202502150011"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "device_identifiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("producto_id", sa.Integer(), sa.ForeignKey(
            "devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("imei_1", sa.String(length=18), nullable=True),
        sa.Column("imei_2", sa.String(length=18), nullable=True),
        sa.Column("numero_serie", sa.String(length=120), nullable=True),
        sa.Column("estado_tecnico", sa.String(length=60), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "producto_id", name="uq_device_identifiers_producto"),
        sa.UniqueConstraint("imei_1", name="uq_device_identifiers_imei_1"),
        sa.UniqueConstraint("imei_2", name="uq_device_identifiers_imei_2"),
        sa.UniqueConstraint(
            "numero_serie", name="uq_device_identifiers_numero_serie"),
    )
    op.create_index(
        "ix_device_identifiers_producto_id",
        "device_identifiers",
        ["producto_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_device_identifiers_producto_id",
                  table_name="device_identifiers")
    op.drop_table("device_identifiers")
