"""purchase return credit notes"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "202511080001"
down_revision = "202511070006"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


SUPPLIER_LEDGER_ENTRY_TYPE = sa.Enum(
    "invoice",
    "payment",
    "credit_note",
    "adjustment",
    name="supplier_ledger_entry_type",
)


def upgrade() -> None:
    bind = op.get_bind()
    SUPPLIER_LEDGER_ENTRY_TYPE.create(bind, checkfirst=True)

    op.create_table(
        "supplier_ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("entry_type", SUPPLIER_LEDGER_ENTRY_TYPE, nullable=False),
        sa.Column("reference_type", sa.String(length=60), nullable=True),
        sa.Column("reference_id", sa.String(length=80), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "details",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["usuarios.id_usuario"], ondelete="SET NULL"),
    )
    op.create_index(
        op.f("ix_supplier_ledger_entries_supplier_id"),
        "supplier_ledger_entries",
        ["supplier_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_ledger_entries_created_by_id"),
        "supplier_ledger_entries",
        ["created_by_id"],
        unique=False,
    )

    op.add_column(
        "purchase_returns",
        sa.Column("supplier_ledger_entry_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "purchase_returns",
        sa.Column("corporate_reason", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "purchase_returns",
        sa.Column(
            "credit_note_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index(
        op.f("ix_purchase_returns_supplier_ledger_entry_id"),
        "purchase_returns",
        ["supplier_ledger_entry_id"],
        unique=False,
    )
    op.create_foreign_key(
        "purchase_returns_supplier_ledger_entry_id_fkey",
        "purchase_returns",
        "supplier_ledger_entries",
        ["supplier_ledger_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column(
        "purchase_returns",
        "credit_note_amount",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_constraint(
        "purchase_returns_supplier_ledger_entry_id_fkey",
        "purchase_returns",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_purchase_returns_supplier_ledger_entry_id"),
        table_name="purchase_returns",
    )
    op.drop_column("purchase_returns", "supplier_ledger_entry_id")
    op.drop_column("purchase_returns", "corporate_reason")
    op.drop_column("purchase_returns", "credit_note_amount")

    op.drop_index(op.f("ix_supplier_ledger_entries_created_by_id"), table_name="supplier_ledger_entries")
    op.drop_index(op.f("ix_supplier_ledger_entries_supplier_id"), table_name="supplier_ledger_entries")
    op.drop_table("supplier_ledger_entries")
    SUPPLIER_LEDGER_ENTRY_TYPE.drop(op.get_bind(), checkfirst=True)
