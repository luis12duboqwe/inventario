"""purchase order documents"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202511080002"
down_revision = "202511080001"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_order_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_order_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("storage_backend", sa.String(length=20), nullable=False),
        sa.Column("object_path", sa.String(length=255), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["purchase_order_id"],
            ["purchase_orders.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["usuarios.id_usuario"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        op.f("ix_purchase_order_documents_purchase_order_id"),
        "purchase_order_documents",
        ["purchase_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_order_documents_uploaded_by_id"),
        "purchase_order_documents",
        ["uploaded_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_purchase_order_documents_uploaded_by_id"),
        table_name="purchase_order_documents",
    )
    op.drop_index(
        op.f("ix_purchase_order_documents_purchase_order_id"),
        table_name="purchase_order_documents",
    )
    op.drop_table("purchase_order_documents")
