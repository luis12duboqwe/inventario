"""Add return disposition and warehouse tracking

Revision ID: 202511070006_return_dispositions
Revises: 202511070005_stock_thresholds
Create Date: 2025-11-07 12:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202511070006_return_dispositions"
down_revision = "202511070005_stock_thresholds"
branch_labels = None
depends_on = None


RETURN_DISPOSITION_VALUES = ("vendible", "defectuoso", "no_vendible", "reparacion")


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    return_enum = sa.Enum(*RETURN_DISPOSITION_VALUES, name="return_disposition")
    return_enum.create(bind, checkfirst=True)

    sale_index_name = op.f("ix_sale_returns_warehouse_id")
    purchase_index_name = op.f("ix_purchase_returns_warehouse_id")

    def _sale_disposition_column() -> sa.Column:
        return sa.Column(
            "disposition",
            return_enum,
            nullable=False,
            server_default="vendible",
        )

    def _purchase_disposition_column() -> sa.Column:
        return sa.Column(
            "disposition",
            return_enum.copy(),
            nullable=False,
            server_default="defectuoso",
        )

    if is_sqlite:
        with op.batch_alter_table(
            "sale_returns", recreate="always", reflect_kwargs={"resolve_fks": False}
        ) as batch_op:
            batch_op.add_column(_sale_disposition_column())
            batch_op.add_column(sa.Column("warehouse_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "sale_returns_warehouse_id_fkey",
                "sucursales",
                ["warehouse_id"],
                ["id_sucursal"],
                ondelete="SET NULL",
            )
            batch_op.create_index(sale_index_name, ["warehouse_id"], unique=False)
        with op.batch_alter_table(
            "purchase_returns", recreate="always", reflect_kwargs={"resolve_fks": False}
        ) as batch_op:
            batch_op.add_column(_purchase_disposition_column())
            batch_op.add_column(sa.Column("warehouse_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "purchase_returns_warehouse_id_fkey",
                "sucursales",
                ["warehouse_id"],
                ["id_sucursal"],
                ondelete="SET NULL",
            )
            batch_op.create_index(purchase_index_name, ["warehouse_id"], unique=False)
    else:
        op.add_column("sale_returns", _sale_disposition_column())
        op.add_column(
            "sale_returns",
            sa.Column("warehouse_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "sale_returns_warehouse_id_fkey",
            "sale_returns",
            "sucursales",
            ["warehouse_id"],
            ["id_sucursal"],
            ondelete="SET NULL",
        )
        op.create_index(
            sale_index_name,
            "sale_returns",
            ["warehouse_id"],
            unique=False,
        )

        op.add_column("purchase_returns", _purchase_disposition_column())
        op.add_column(
            "purchase_returns",
            sa.Column("warehouse_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "purchase_returns_warehouse_id_fkey",
            "purchase_returns",
            "sucursales",
            ["warehouse_id"],
            ["id_sucursal"],
            ondelete="SET NULL",
        )
        op.create_index(
            purchase_index_name,
            "purchase_returns",
            ["warehouse_id"],
            unique=False,
        )

    op.execute(
        sa.text(
            "UPDATE sale_returns SET disposition = :value WHERE disposition IS NULL"
        ).bindparams(value="vendible")
    )
    op.execute(
        sa.text(
            "UPDATE purchase_returns SET disposition = :value WHERE disposition IS NULL"
        ).bindparams(value="defectuoso")
    )

    if not is_sqlite:
        op.alter_column("sale_returns", "disposition", server_default=None)
        op.alter_column("purchase_returns", "disposition", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    sale_index_name = op.f("ix_sale_returns_warehouse_id")
    purchase_index_name = op.f("ix_purchase_returns_warehouse_id")

    if is_sqlite:
        with op.batch_alter_table(
            "purchase_returns", recreate="always", reflect_kwargs={"resolve_fks": False}
        ) as batch_op:
            batch_op.drop_index(purchase_index_name)
            batch_op.drop_constraint(
                "purchase_returns_warehouse_id_fkey", type_="foreignkey"
            )
            batch_op.drop_column("warehouse_id")
            batch_op.drop_column("disposition")
        with op.batch_alter_table(
            "sale_returns", recreate="always", reflect_kwargs={"resolve_fks": False}
        ) as batch_op:
            batch_op.drop_index(sale_index_name)
            batch_op.drop_constraint("sale_returns_warehouse_id_fkey", type_="foreignkey")
            batch_op.drop_column("warehouse_id")
            batch_op.drop_column("disposition")
    else:
        op.drop_constraint(
            "purchase_returns_warehouse_id_fkey", "purchase_returns", type_="foreignkey"
        )
        op.drop_index(purchase_index_name, table_name="purchase_returns")
        op.drop_column("purchase_returns", "warehouse_id")
        op.drop_column("purchase_returns", "disposition")

        op.drop_constraint(
            "sale_returns_warehouse_id_fkey", "sale_returns", type_="foreignkey"
        )
        op.drop_index(sale_index_name, table_name="sale_returns")
        op.drop_column("sale_returns", "warehouse_id")
        op.drop_column("sale_returns", "disposition")

    return_enum = sa.Enum(*RETURN_DISPOSITION_VALUES, name="return_disposition")
    return_enum.drop(op.get_bind(), checkfirst=True)
