"""Registrar movimientos manuales de caja y conciliaciones POS."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202511070006_cash_register_manual_entries"
down_revision = ("202511070005", "202511070005_product_variants_bundles")
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    empty_json = sa.text("'{}'") if is_sqlite else sa.text("'{}'::jsonb")
    timestamp_default = sa.text("CURRENT_TIMESTAMP") if is_sqlite else sa.text(
        "timezone('utc', now())"
    )

    op.add_column(
        "cash_register_sessions",
        sa.Column(
            "denomination_breakdown",
            json_type,
            nullable=False,
            server_default=empty_json,
        ),
    )
    op.add_column(
        "cash_register_sessions",
        sa.Column("reconciliation_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "cash_register_sessions",
        sa.Column("difference_reason", sa.Text(), nullable=True),
    )

    update_statement = (
        "UPDATE cash_register_sessions SET denomination_breakdown = '{}'"
        if is_sqlite
        else "UPDATE cash_register_sessions SET denomination_breakdown = '{}'::jsonb"
    )
    op.execute(update_statement)

    op.create_table(
        "cash_register_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column(
            "entry_type",
            sa.Enum("INGRESO", "EGRESO", name="cash_entry_type"),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["cash_register_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["usuarios.id_usuario"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_cash_register_entries_session_id",
        "cash_register_entries",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cash_register_entries_session_id", table_name="cash_register_entries"
    )
    op.drop_table("cash_register_entries")

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        sa.Enum("INGRESO", "EGRESO", name="cash_entry_type").drop(
            bind, checkfirst=True
        )

    op.drop_column("cash_register_sessions", "difference_reason")
    op.drop_column("cash_register_sessions", "reconciliation_notes")
    op.drop_column("cash_register_sessions", "denomination_breakdown")
