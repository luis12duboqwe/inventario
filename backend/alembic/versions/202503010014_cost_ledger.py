from alembic import op
import sqlalchemy as sa

# // [PACK30-31-BACKEND]
# revision identifiers, used by Alembic.
revision = "202503010014"
down_revision = "202503010013"
branch_labels = None
depends_on = None


COST_METHOD_ENUM = sa.Enum("FIFO", "AVG", name="costing_method")


def upgrade() -> None:
    bind = op.get_bind()
    COST_METHOD_ENUM.create(bind, checkfirst=True)

    op.create_table(
        "cost_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "move_id",
            sa.Integer(),
            sa.ForeignKey("stock_moves.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            sa.Integer(),
            sa.ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("method", COST_METHOD_ENUM, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_cost_ledger_product", "cost_ledger", ["product_id"], unique=False)
    op.create_index("ix_cost_ledger_move", "cost_ledger", ["move_id"], unique=False)
    op.create_index("ix_cost_ledger_branch", "cost_ledger", ["branch_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cost_ledger_branch", table_name="cost_ledger")
    op.drop_index("ix_cost_ledger_move", table_name="cost_ledger")
    op.drop_index("ix_cost_ledger_product", table_name="cost_ledger")
    op.drop_table("cost_ledger")

    bind = op.get_bind()
    COST_METHOD_ENUM.drop(bind, checkfirst=True)
