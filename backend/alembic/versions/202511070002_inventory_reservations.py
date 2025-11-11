"""Crea tabla de reservas de inventario y vincula ventas/transferencias.

Revision ID: 202511070002
Revises: 202511070001
Create Date: 2025-11-07 11:00:00 UTC

Nota: Compatible con v2.2.0 sin alterar etiquetas de versión del producto.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from backend.app.db.valor_inventario_view import (
    create_valor_inventario_view,
    drop_valor_inventario_view,
)

# revision identifiers, used by Alembic.
revision = "202511070002"
down_revision = "202511070001"
branch_labels = None
depends_on = None


inventory_state_enum = sa.Enum(
    "RESERVADO",
    "CONSUMIDO",
    "CANCELADO",
    "EXPIRADO",
    name="inventory_reservation_state",
)


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    inventory_state_enum.create(bind, checkfirst=True)

    if is_sqlite:
        drop_valor_inventario_view(bind)

    op.create_table(
        "inventory_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "store_id",
            sa.Integer(),
            sa.ForeignKey("sucursales.id_sucursal", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Integer(),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reserved_by_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "resolved_by_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("initial_quantity", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            inventory_state_enum,
            nullable=False,
            server_default="RESERVADO",
        ),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("resolution_reason", sa.String(length=255), nullable=True),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", sa.String(length=50), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_inventory_reservation_store_device",
        "inventory_reservations",
        ["store_id", "device_id"],
    )

    with op.batch_alter_table("detalle_ventas", reflect_kwargs={"resolve_fks": False}) as batch_op:
        batch_op.add_column(sa.Column("reservation_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_detalle_ventas_reservation_id", ["reservation_id"]
        )
        batch_op.create_foreign_key(
            "fk_detalle_ventas_reservation_id",
            "inventory_reservations",
            ["reservation_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("transfer_order_items", reflect_kwargs={"resolve_fks": False}) as batch_op:
        batch_op.add_column(sa.Column("reservation_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_transfer_order_items_reservation_id", ["reservation_id"]
        )
        batch_op.create_foreign_key(
            "fk_transfer_order_items_reservation_id",
            "inventory_reservations",
            ["reservation_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if is_sqlite:
        create_valor_inventario_view(bind)


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        drop_valor_inventario_view(bind)

    with op.batch_alter_table("transfer_order_items", reflect_kwargs={"resolve_fks": False}) as batch_op:
        batch_op.drop_constraint(
            "fk_transfer_order_items_reservation_id", type_="foreignkey"
        )
        batch_op.drop_index("ix_transfer_order_items_reservation_id")
        batch_op.drop_column("reservation_id")

    with op.batch_alter_table("detalle_ventas", reflect_kwargs={"resolve_fks": False}) as batch_op:
        batch_op.drop_constraint(
            "fk_detalle_ventas_reservation_id", type_="foreignkey"
        )
        batch_op.drop_index("ix_detalle_ventas_reservation_id")
        batch_op.drop_column("reservation_id")

    op.drop_index(
        "ix_inventory_reservation_store_device",
        table_name="inventory_reservations",
    )
    op.drop_table("inventory_reservations")

    inventory_state_enum.drop(bind, checkfirst=True)

    if is_sqlite:
        create_valor_inventario_view(bind)
