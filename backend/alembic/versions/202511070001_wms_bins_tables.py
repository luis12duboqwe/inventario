"""Crea tablas wms_bins y device_bins para ubicaciones WMS ligeras.

Revision ID: 202511070001
Revises: 202511060001
Create Date: 2025-11-07 10:00:00 UTC

Nota: Compatible con v2.2.0 sin alterar etiquetas de versión del producto.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202511070001"
down_revision = "202511060001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wms_bins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sucursal_id", sa.Integer(), sa.ForeignKey(
            "sucursales.id_sucursal", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo", sa.String(length=60), nullable=False),
        sa.Column("pasillo", sa.String(length=60), nullable=True),
        sa.Column("rack", sa.String(length=60), nullable=True),
        sa.Column("nivel", sa.String(length=60), nullable=True),
        sa.Column("descripcion", sa.String(length=255), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("sucursal_id", "codigo",
                            name="uq_wms_bins_store_code"),
    )
    op.create_index("ix_wms_bins_store", "wms_bins",
                    ["sucursal_id"], unique=False)

    op.create_table(
        "device_bins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("producto_id", sa.Integer(), sa.ForeignKey(
            "devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bin_id", sa.Integer(), sa.ForeignKey(
            "wms_bins.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asignado_en", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("desasignado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False,
                  server_default=sa.text("1")),
    )
    op.create_index("ix_device_bins_device", "device_bins",
                    ["producto_id"], unique=False)
    op.create_index("ix_device_bins_bin", "device_bins",
                    ["bin_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_device_bins_bin", table_name="device_bins")
    op.drop_index("ix_device_bins_device", table_name="device_bins")
    op.drop_table("device_bins")

    op.drop_index("ix_wms_bins_store", table_name="wms_bins")
    op.drop_table("wms_bins")
