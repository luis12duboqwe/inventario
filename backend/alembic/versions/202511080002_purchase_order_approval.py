from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202511080002"
down_revision = "202511080001"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    with op.batch_alter_table("purchase_orders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "approved_by_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "requires_approval",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch_op.create_index(
            batch_op.f("ix_purchase_orders_approved_by_id"),
            ["approved_by_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "purchase_orders_approved_by_id_fkey",
            "usuarios",
            ["approved_by_id"],
            ["id_usuario"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("purchase_orders", schema=None) as batch_op:
        batch_op.alter_column("requires_approval", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("purchase_orders", schema=None) as batch_op:
        batch_op.drop_constraint(
            "purchase_orders_approved_by_id_fkey", type_="foreignkey"
        )
        batch_op.drop_index(batch_op.f("ix_purchase_orders_approved_by_id"))
        batch_op.drop_column("approved_by_id")
        batch_op.drop_column("requires_approval")
