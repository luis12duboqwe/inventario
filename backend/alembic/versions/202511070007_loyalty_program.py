"""Crea tablas de lealtad y extiende enum de forma de pago.

Revision ID: 202511070007_loyalty_program
Revises: 202511070006_return_dispositions
Create Date: 2025-11-07 14:30:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "202511070007_loyalty_program"
down_revision: str | None = "202511070006_return_dispositions"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


PAYMENT_METHOD_ENUM_NAME = "payment_method"
PAYMENT_METHOD_VALUES: tuple[str, ...] = (
    "EFECTIVO",
    "TARJETA",
    "CREDITO",
    "TRANSFERENCIA",
    "NOTA_CREDITO",
    "PUNTOS",
    "OTRO",
)
PAYMENT_METHOD_PREVIOUS_VALUES: tuple[str, ...] = tuple(
    value for value in PAYMENT_METHOD_VALUES if value != "PUNTOS"
)

LOYALTY_RULE_DEFAULT = "'{}'"
NUMERIC_ZERO_DEFAULT = "'0'"
NUMERIC_ONE_DEFAULT = "'1.0000'"

LOYALTY_TRANSACTION_TYPE_VALUES: tuple[str, ...] = (
    "earn",
    "redeem",
    "adjust",
    "expiration",
)


def _json_type(bind) -> sa.types.TypeEngine:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(bind) -> sa.sql.elements.TextClause:
    if bind.dialect.name == "postgresql":
        return sa.text("'{}'::jsonb")
    return sa.text(LOYALTY_RULE_DEFAULT)


def _add_payment_method_value(bind) -> None:
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "ALTER TYPE payment_method ADD VALUE IF NOT EXISTS 'PUNTOS'"
            )
        )
        return

    existing_enum = sa.Enum(
        *PAYMENT_METHOD_PREVIOUS_VALUES,
        name=PAYMENT_METHOD_ENUM_NAME,
        create_type=False,
    )
    new_enum = sa.Enum(
        *PAYMENT_METHOD_VALUES,
        name=PAYMENT_METHOD_ENUM_NAME,
        create_type=False,
    )
    with op.batch_alter_table("ventas") as batch_op:
        batch_op.alter_column(
            "forma_pago",
            type_=new_enum,
            existing_type=existing_enum,
            existing_nullable=False,
        )


def _remove_payment_method_value(bind) -> None:
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "UPDATE ventas SET forma_pago = 'OTRO' WHERE forma_pago = 'PUNTOS'"
            )
        )
        op.execute(sa.text("ALTER TYPE payment_method RENAME TO payment_method_old"))
        op.execute(
            sa.text(
                "CREATE TYPE payment_method AS ENUM ('EFECTIVO','TARJETA','CREDITO','TRANSFERENCIA','NOTA_CREDITO','OTRO')"
            )
        )
        op.execute(
            sa.text(
                "ALTER TABLE ventas ALTER COLUMN forma_pago TYPE payment_method USING forma_pago::text::payment_method"
            )
        )
        op.execute(sa.text("DROP TYPE payment_method_old"))
        return

    downgraded_enum = sa.Enum(
        *PAYMENT_METHOD_PREVIOUS_VALUES,
        name=PAYMENT_METHOD_ENUM_NAME,
        create_type=False,
    )
    upgraded_enum = sa.Enum(
        *PAYMENT_METHOD_VALUES,
        name=PAYMENT_METHOD_ENUM_NAME,
        create_type=False,
    )
    with op.batch_alter_table("ventas") as batch_op:
        batch_op.alter_column(
            "forma_pago",
            type_=downgraded_enum,
            existing_type=upgraded_enum,
            existing_nullable=False,
        )


def _loyalty_transaction_enum(bind) -> sa.Enum:
    if bind.dialect.name == "postgresql":
        return postgresql.ENUM(
            *LOYALTY_TRANSACTION_TYPE_VALUES,
            name="loyalty_transaction_type",
            create_type=True,
        )
    return sa.Enum(
        *LOYALTY_TRANSACTION_TYPE_VALUES,
        name="loyalty_transaction_type",
    )


def upgrade() -> None:
    bind = op.get_bind()
    json_type = _json_type(bind)
    rule_default = _json_default(bind)
    loyalty_enum = _loyalty_transaction_enum(bind)
    loyalty_enum.create(bind, checkfirst=True)

    if bind.dialect.name == "postgresql":
        loyalty_column_type: sa.types.TypeEngine = postgresql.ENUM(
            *LOYALTY_TRANSACTION_TYPE_VALUES,
            name="loyalty_transaction_type",
            create_type=False,
        )
    else:
        loyalty_column_type = loyalty_enum

    op.create_table(
        "loyalty_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("clientes.id_cliente", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "accrual_rate",
            sa.Numeric(6, 4),
            nullable=False,
            server_default=sa.text(NUMERIC_ONE_DEFAULT),
        ),
        sa.Column(
            "redemption_rate",
            sa.Numeric(6, 4),
            nullable=False,
            server_default=sa.text(NUMERIC_ONE_DEFAULT),
        ),
        sa.Column(
            "expiration_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("365"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("rule_config", json_type, nullable=False, server_default=rule_default),
        sa.Column(
            "balance_points",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text(NUMERIC_ZERO_DEFAULT),
        ),
        sa.Column(
            "lifetime_points_earned",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text(NUMERIC_ZERO_DEFAULT),
        ),
        sa.Column(
            "lifetime_points_redeemed",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text(NUMERIC_ZERO_DEFAULT),
        ),
        sa.Column(
            "expired_points_total",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text(NUMERIC_ZERO_DEFAULT),
        ),
        sa.Column("last_accrual_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_redemption_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_expiration_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index(
        "ix_loyalty_accounts_customer_id",
        "loyalty_accounts",
        ["customer_id"],
        unique=True,
    )

    op.create_table(
        "loyalty_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("loyalty_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sale_id",
            sa.Integer(),
            sa.ForeignKey("ventas.id_venta", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "transaction_type",
            loyalty_column_type,
            nullable=False,
        ),
        sa.Column(
            "points",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "balance_after",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "currency_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text(NUMERIC_ZERO_DEFAULT),
        ),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("details", json_type, nullable=False, server_default=rule_default),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "registered_by_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_loyalty_transactions_account_id",
        "loyalty_transactions",
        ["account_id"],
    )
    op.create_index(
        "ix_loyalty_transactions_sale_id",
        "loyalty_transactions",
        ["sale_id"],
    )
    op.create_index(
        "ix_loyalty_transactions_registered_by_id",
        "loyalty_transactions",
        ["registered_by_id"],
    )

    with op.batch_alter_table("ventas") as batch_op:
        batch_op.add_column(
            sa.Column(
                "loyalty_points_earned",
                sa.Numeric(12, 2),
                nullable=False,
                server_default=sa.text(NUMERIC_ZERO_DEFAULT),
            )
        )
        batch_op.add_column(
            sa.Column(
                "loyalty_points_redeemed",
                sa.Numeric(12, 2),
                nullable=False,
                server_default=sa.text(NUMERIC_ZERO_DEFAULT),
            )
        )

    if bind.dialect.name != "sqlite":
        op.alter_column("ventas", "loyalty_points_earned", server_default=None)
        op.alter_column("ventas", "loyalty_points_redeemed", server_default=None)

    _add_payment_method_value(bind)


def downgrade() -> None:
    bind = op.get_bind()

    _remove_payment_method_value(bind)

    with op.batch_alter_table("ventas") as batch_op:
        batch_op.drop_column("loyalty_points_redeemed")
        batch_op.drop_column("loyalty_points_earned")

    op.drop_index(
        "ix_loyalty_transactions_registered_by_id",
        table_name="loyalty_transactions",
    )
    op.drop_index(
        "ix_loyalty_transactions_sale_id",
        table_name="loyalty_transactions",
    )
    op.drop_index(
        "ix_loyalty_transactions_account_id",
        table_name="loyalty_transactions",
    )
    op.drop_table("loyalty_transactions")

    op.drop_index(
        "ix_loyalty_accounts_customer_id",
        table_name="loyalty_accounts",
    )
    op.drop_table("loyalty_accounts")

    loyalty_enum = _loyalty_transaction_enum(bind)
    loyalty_enum.drop(bind, checkfirst=True)
