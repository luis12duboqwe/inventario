"""Add return disposition and warehouse tracking

Revision ID: 202511070006_return_dispositions
Revises: 202511070005_stock_thresholds
Create Date: 2025-11-07 12:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202511070006_return_dispositions"
down_revision = "202511070005_stock_thresholds"
branch_labels = None
depends_on = None


RETURN_DISPOSITION_VALUES = ("vendible", "defectuoso", "no_vendible", "reparacion")


def upgrade() -> None:
    bind = op.get_bind()
    return_enum = sa.Enum(*RETURN_DISPOSITION_VALUES, name="return_disposition")
    return_enum.create(bind, checkfirst=True)

    op.add_column(
        "sale_returns",
        sa.Column(
            "disposition",
            return_enum,
            nullable=False,
            server_default="vendible",
        ),
    )
    op.add_column(
        "sale_returns",
        sa.Column("warehouse_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "sale_returns_warehouse_id_fkey",
        "sale_returns",
        "sucursales",
        ["warehouse_id"],
        ["id_sucursal"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_sale_returns_warehouse_id"),
        "sale_returns",
        ["warehouse_id"],
        unique=False,
    )

    op.add_column(
        "purchase_returns",
        sa.Column(
            "disposition",
            return_enum.copy(),
            nullable=False,
            server_default="defectuoso",
        ),
    )
    op.add_column(
        "purchase_returns",
        sa.Column("warehouse_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "purchase_returns_warehouse_id_fkey",
        "purchase_returns",
        "sucursales",
        ["warehouse_id"],
        ["id_sucursal"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_purchase_returns_warehouse_id"),
        "purchase_returns",
        ["warehouse_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            "UPDATE sale_returns SET disposition = :value WHERE disposition IS NULL"
        ),
        {"value": "vendible"},
    )
    op.execute(
        sa.text(
            "UPDATE purchase_returns SET disposition = :value WHERE disposition IS NULL"
        ),
        {"value": "defectuoso"},
    )

    op.alter_column("sale_returns", "disposition", server_default=None)
    op.alter_column("purchase_returns", "disposition", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "purchase_returns_warehouse_id_fkey", "purchase_returns", type_="foreignkey"
    )
    op.drop_index(op.f("ix_purchase_returns_warehouse_id"), table_name="purchase_returns")
    op.drop_column("purchase_returns", "warehouse_id")
    op.drop_column("purchase_returns", "disposition")

    op.drop_constraint(
        "sale_returns_warehouse_id_fkey", "sale_returns", type_="foreignkey"
    )
    op.drop_index(op.f("ix_sale_returns_warehouse_id"), table_name="sale_returns")
    op.drop_column("sale_returns", "warehouse_id")
    op.drop_column("sale_returns", "disposition")

    return_enum = sa.Enum(*RETURN_DISPOSITION_VALUES, name="return_disposition")
    return_enum.drop(op.get_bind(), checkfirst=True)
