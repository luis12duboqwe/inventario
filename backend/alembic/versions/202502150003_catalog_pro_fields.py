"""Agregar campos de catálogo pro para dispositivos."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202502150003"
down_revision = "202502150002"
branch_labels = None
depends_on = None


ESTADO_ENUM_NAME = "estado_comercial"


def upgrade() -> None:
    bind = op.get_bind()
    estado_enum = sa.Enum("nuevo", "A", "B", "C", name=ESTADO_ENUM_NAME)
    estado_enum.create(bind, checkfirst=True)

    op.add_column("devices", sa.Column(
        "imei", sa.String(length=18), nullable=True))
    op.add_column("devices", sa.Column(
        "serial", sa.String(length=120), nullable=True))
    op.add_column("devices", sa.Column(
        "marca", sa.String(length=80), nullable=True))
    op.add_column("devices", sa.Column(
        "modelo", sa.String(length=120), nullable=True))
    op.add_column("devices", sa.Column(
        "color", sa.String(length=60), nullable=True))
    op.add_column("devices", sa.Column(
        "capacidad_gb", sa.Integer(), nullable=True))
    op.add_column(
        "devices",
        sa.Column(
            "estado_comercial",
            estado_enum,
            nullable=False,
            server_default="nuevo",
        ),
    )
    op.add_column("devices", sa.Column(
        "proveedor", sa.String(length=120), nullable=True))
    op.add_column(
        "devices",
        sa.Column(
            "costo_unitario",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "devices",
        sa.Column(
            "margen_porcentaje",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "devices",
        sa.Column("garantia_meses", sa.Integer(),
                  nullable=False, server_default="0"),
    )
    op.add_column("devices", sa.Column(
        "lote", sa.String(length=80), nullable=True))
    op.add_column("devices", sa.Column(
        "fecha_compra", sa.Date(), nullable=True))

    op.create_index("uq_devices_imei", "devices", ["imei"], unique=True)
    op.create_index("uq_devices_serial", "devices", ["serial"], unique=True)

    if bind.dialect.name != "sqlite":  # SQLite no permite DROP DEFAULT directo
        op.alter_column("devices", "estado_comercial", server_default=None)
        op.alter_column("devices", "costo_unitario", server_default=None)
        op.alter_column("devices", "margen_porcentaje", server_default=None)
        op.alter_column("devices", "garantia_meses", server_default=None)


def downgrade() -> None:
    op.drop_index("uq_devices_serial", table_name="devices")
    op.drop_index("uq_devices_imei", table_name="devices")
    op.drop_column("devices", "fecha_compra")
    op.drop_column("devices", "lote")
    op.drop_column("devices", "garantia_meses")
    op.drop_column("devices", "margen_porcentaje")
    op.drop_column("devices", "costo_unitario")
    op.drop_column("devices", "proveedor")
    op.drop_column("devices", "estado_comercial")
    op.drop_column("devices", "capacidad_gb")
    op.drop_column("devices", "color")
    op.drop_column("devices", "modelo")
    op.drop_column("devices", "marca")
    op.drop_column("devices", "serial")
    op.drop_column("devices", "imei")

    estado_enum = sa.Enum(name=ESTADO_ENUM_NAME)
    estado_enum.drop(op.get_bind(), checkfirst=True)
