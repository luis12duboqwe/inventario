"""Crea plantillas recurrentes y soporte de historial operativo."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202502150008"
down_revision = "202502150007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    recurring_type = sa.Enum(
        "purchase",
        "transfer",
        name="recurring_order_type",
    )
    recurring_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "recurring_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("order_type", recurring_type, nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("last_used_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_recurring_orders_store_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["last_used_by_id"], [
                                "users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recurring_orders_id"),
                    "recurring_orders", ["id"], unique=False)
    op.create_index(op.f("ix_recurring_orders_order_type"),
                    "recurring_orders", ["order_type"], unique=False)
    op.create_index(op.f("ix_recurring_orders_store_id"),
                    "recurring_orders", ["store_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recurring_orders_store_id"),
                  table_name="recurring_orders")
    op.drop_index(op.f("ix_recurring_orders_order_type"),
                  table_name="recurring_orders")
    op.drop_index(op.f("ix_recurring_orders_id"),
                  table_name="recurring_orders")
    op.drop_table("recurring_orders")

    recurring_type = sa.Enum(name="recurring_order_type")
    recurring_type.drop(op.get_bind(), checkfirst=True)
