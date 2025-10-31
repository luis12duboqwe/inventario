from alembic import op
import sqlalchemy as sa

# // [PACK30-31-BACKEND]
# revision identifiers, used by Alembic.
revision = "202503010013"
down_revision = "202503010012"
branch_labels = None
depends_on = None


STOCK_MOVE_TYPE = sa.Enum(
    "IN",
    "OUT",
    "ADJ",
    "TRANSFER",
    name="stock_move_type",
)


def upgrade() -> None:
    bind = op.get_bind()
    STOCK_MOVE_TYPE.create(bind, checkfirst=True)

    op.create_table(
        "stock_moves",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "branch_id",
            sa.Integer(),
            sa.ForeignKey("sucursales.id_sucursal", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("movement_type", STOCK_MOVE_TYPE, nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_stock_moves_product", "stock_moves", ["product_id"], unique=False)
    op.create_index("ix_stock_moves_branch", "stock_moves", ["branch_id"], unique=False)
    op.create_index("ix_stock_moves_timestamp", "stock_moves", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stock_moves_timestamp", table_name="stock_moves")
    op.drop_index("ix_stock_moves_branch", table_name="stock_moves")
    op.drop_index("ix_stock_moves_product", table_name="stock_moves")
    op.drop_table("stock_moves")

    bind = op.get_bind()
    STOCK_MOVE_TYPE.drop(bind, checkfirst=True)
