"""Agrega columnas de autorización para devoluciones y hash de PIN de supervisor.

Revision ID: 202511070007_return_authorizations
Revises: 202511070006_return_dispositions
Create Date: 2025-11-07 12:30:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202511070007_return_authorizations"
down_revision = "202511070006_return_dispositions"
branch_labels = None
depends_on = None


RETURN_REASON_CATEGORY_VALUES = (
    "defecto",
    "logistica",
    "cliente",
    "precio",
    "otro",
)


def upgrade() -> None:
    bind = op.get_bind()
    reason_enum = sa.Enum(
        *RETURN_REASON_CATEGORY_VALUES,
        name="return_reason_category",
    )
    reason_enum.create(bind, checkfirst=True)

    op.add_column(
        "usuarios",
        sa.Column("supervisor_pin_hash", sa.String(length=255), nullable=True),
    )

    op.add_column(
        "sale_returns",
        sa.Column(
            "reason_category",
            reason_enum,
            nullable=False,
            server_default="otro",
        ),
    )
    op.add_column(
        "sale_returns",
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "sale_returns_approved_by_id_fkey",
        "sale_returns",
        "usuarios",
        ["approved_by_id"],
        ["id_usuario"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_sale_returns_reason_category"),
        "sale_returns",
        ["reason_category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sale_returns_approved_by_id"),
        "sale_returns",
        ["approved_by_id"],
        unique=False,
    )

    op.add_column(
        "purchase_returns",
        sa.Column(
            "reason_category",
            reason_enum.copy(),
            nullable=False,
            server_default="otro",
        ),
    )
    op.add_column(
        "purchase_returns",
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "purchase_returns_approved_by_id_fkey",
        "purchase_returns",
        "usuarios",
        ["approved_by_id"],
        ["id_usuario"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_purchase_returns_reason_category"),
        "purchase_returns",
        ["reason_category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_returns_approved_by_id"),
        "purchase_returns",
        ["approved_by_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            "UPDATE sale_returns SET reason_category = :value WHERE reason_category IS NULL"
        ),
        {"value": "otro"},
    )
    op.execute(
        sa.text(
            "UPDATE purchase_returns SET reason_category = :value WHERE reason_category IS NULL"
        ),
        {"value": "otro"},
    )

    op.alter_column("sale_returns", "reason_category", server_default=None)
    op.alter_column("purchase_returns", "reason_category", server_default=None)


def downgrade() -> None:
    op.drop_index(
        op.f("ix_purchase_returns_approved_by_id"), table_name="purchase_returns"
    )
    op.drop_index(
        op.f("ix_purchase_returns_reason_category"), table_name="purchase_returns"
    )
    op.drop_constraint(
        "purchase_returns_approved_by_id_fkey",
        "purchase_returns",
        type_="foreignkey",
    )
    op.drop_column("purchase_returns", "approved_by_id")
    op.drop_column("purchase_returns", "reason_category")

    op.drop_index(
        op.f("ix_sale_returns_approved_by_id"), table_name="sale_returns"
    )
    op.drop_index(
        op.f("ix_sale_returns_reason_category"), table_name="sale_returns"
    )
    op.drop_constraint(
        "sale_returns_approved_by_id_fkey", "sale_returns", type_="foreignkey"
    )
    op.drop_column("sale_returns", "approved_by_id")
    op.drop_column("sale_returns", "reason_category")

    op.drop_column("usuarios", "supervisor_pin_hash")

    reason_enum = sa.Enum(
        *RETURN_REASON_CATEGORY_VALUES,
        name="return_reason_category",
    )
    reason_enum.drop(op.get_bind(), checkfirst=True)
