"""Tablas base para órdenes de reparación y repuestos."""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
# These module-level variables are read by Alembic at runtime to build the migration graph.
# They are required and should not be removed despite appearing unused to static analysis.
revision: str = "202503010015_repair_orders_base"
down_revision: str | None = "202503010015"
branch_labels: Sequence[str] | None = None


REPAIR_STATUS_VALUES = (
    "PENDIENTE",
    "EN_PROCESO",
    "LISTO",
    "ENTREGADO",
    "CANCELADO",
)


def _json_type(bind) -> sa.types.TypeEngine:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _repair_status_enum(bind) -> sa.Enum:
    if bind.dialect.name == "postgresql":
        return postgresql.ENUM(*REPAIR_STATUS_VALUES, name="repair_status", create_type=True)
    return sa.Enum(*REPAIR_STATUS_VALUES, name="repair_status")


def upgrade() -> None:
    bind = op.get_bind()
    json_type = _json_type(bind)
    status_enum = _repair_status_enum(bind)
    status_enum.create(bind, checkfirst=True)

    if bind.dialect.name == "postgresql":
        status_column_type: sa.types.TypeEngine = postgresql.ENUM(
            *REPAIR_STATUS_VALUES,
            name="repair_status",
            create_type=False,
        )
    else:
        status_column_type = status_enum

    op.create_table(
        "repair_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sucursal_id",
            sa.Integer(),
            sa.ForeignKey(
                "sucursales.id_sucursal",
                name="fk_repair_orders_sucursal_id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey(
                "clientes.id_cliente",
                name="fk_repair_orders_customer_id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column("customer_name", sa.String(length=120), nullable=True),
        sa.Column("technician_name", sa.String(length=120), nullable=False),
        sa.Column("damage_type", sa.String(length=120), nullable=False),
        sa.Column("device_description", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            status_column_type,
            nullable=False,
            server_default=sa.text("'PENDIENTE'"),
        ),
        sa.Column("labor_cost", sa.Numeric(12, 2),
                  nullable=False, server_default=sa.text("'0'")),
        sa.Column("parts_cost", sa.Numeric(12, 2),
                  nullable=False, server_default=sa.text("'0'")),
        sa.Column("total_cost", sa.Numeric(12, 2),
                  nullable=False, server_default=sa.text("'0'")),
        sa.Column("parts_snapshot", json_type, nullable=False,
                  server_default=sa.text("'[]'")),
        sa.Column(
            "inventory_adjusted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_repair_orders_sucursal_id",
                    "repair_orders", ["sucursal_id"], unique=False)
    op.create_index("ix_repair_orders_customer_id",
                    "repair_orders", ["customer_id"], unique=False)
    op.create_index("ix_repair_orders_status",
                    "repair_orders", ["status"], unique=False)
    op.create_index("ix_repair_orders_opened_at",
                    "repair_orders", ["opened_at"], unique=False)
    op.create_index(
        "ix_repair_orders_delivered_at",
        "repair_orders",
        ["delivered_at"],
        unique=False,
    )

    op.create_table(
        "repair_order_parts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "repair_order_id",
            sa.Integer(),
            sa.ForeignKey(
                "repair_orders.id",
                name="fk_repair_order_parts_order_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Integer(),
            sa.ForeignKey(
                "devices.id",
                name="fk_repair_order_parts_device_id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2),
                  nullable=False, server_default=sa.text("'0'")),
        sa.UniqueConstraint(
            "repair_order_id",
            "device_id",
            name="uq_repair_order_part",
        ),
    )
    op.create_index(
        "ix_repair_order_parts_repair_order_id",
        "repair_order_parts",
        ["repair_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_repair_order_parts_device_id",
        "repair_order_parts",
        ["device_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_repair_order_parts_device_id",
                  table_name="repair_order_parts")
    op.drop_index("ix_repair_order_parts_repair_order_id",
                  table_name="repair_order_parts")
    op.drop_table("repair_order_parts")

    op.drop_index("ix_repair_orders_delivered_at", table_name="repair_orders")
    op.drop_index("ix_repair_orders_opened_at", table_name="repair_orders")
    op.drop_index("ix_repair_orders_status", table_name="repair_orders")
    op.drop_index("ix_repair_orders_customer_id", table_name="repair_orders")
    op.drop_index("ix_repair_orders_sucursal_id", table_name="repair_orders")
    op.drop_table("repair_orders")

    bind = op.get_bind()
    status_enum = _repair_status_enum(bind)
    status_enum.drop(bind, checkfirst=True)
