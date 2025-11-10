"""purchase return credit notes"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "202511080001"
down_revision = "202511070006_return_dispositions"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


SUPPLIER_LEDGER_ENTRY_TYPE = sa.Enum(
    "invoice",
    "payment",
    "credit_note",
    "adjustment",
    name="supplier_ledger_entry_type",
)


def _json_type(bind: sa.engine.Connection) -> sa.types.TypeEngine:
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def _json_default(bind: sa.engine.Connection) -> sa.sql.elements.TextClause:
    if bind.dialect.name == "sqlite":
        return sa.text("'{}'")
    return sa.text("'{}'::jsonb")


def _timestamp_default(bind: sa.engine.Connection) -> sa.sql.elements.TextClause:
    if bind.dialect.name == "sqlite":
        return sa.text("CURRENT_TIMESTAMP")
    return sa.text("timezone('utc', now())")


def upgrade() -> None:
    bind = op.get_bind()
    SUPPLIER_LEDGER_ENTRY_TYPE.create(bind, checkfirst=True)

    json_type = _json_type(bind)
    json_default = _json_default(bind)
    timestamp_default = _timestamp_default(bind)

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
            json_type,
            nullable=False,
            server_default=json_default,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
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

    with op.batch_alter_table("purchase_returns") as batch_op:
        batch_op.add_column(
            sa.Column("supplier_ledger_entry_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("corporate_reason", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "credit_note_amount",
                sa.Numeric(12, 2),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.create_index(
            op.f("ix_purchase_returns_supplier_ledger_entry_id"),
            ["supplier_ledger_entry_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "purchase_returns_supplier_ledger_entry_id_fkey",
            "supplier_ledger_entries",
            ["supplier_ledger_entry_id"],
            ["id"],
            ondelete="SET NULL",
        )
        if bind.dialect.name != "sqlite":
            batch_op.alter_column(
                "credit_note_amount",
                server_default=None,
            )


def downgrade() -> None:
    with op.batch_alter_table("purchase_returns") as batch_op:
        batch_op.drop_constraint(
            "purchase_returns_supplier_ledger_entry_id_fkey",
            type_="foreignkey",
        )
        batch_op.drop_index(op.f("ix_purchase_returns_supplier_ledger_entry_id"))
        batch_op.drop_column("supplier_ledger_entry_id")
        batch_op.drop_column("corporate_reason")
        batch_op.drop_column("credit_note_amount")

    op.drop_index(op.f("ix_supplier_ledger_entries_created_by_id"), table_name="supplier_ledger_entries")
    op.drop_index(op.f("ix_supplier_ledger_entries_supplier_id"), table_name="supplier_ledger_entries")
    op.drop_table("supplier_ledger_entries")
    SUPPLIER_LEDGER_ENTRY_TYPE.drop(op.get_bind(), checkfirst=True)
