"""Extiende órdenes y repuestos de reparación."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202503010015_pack37_repairs_extensions"
down_revision = "202503010015_repair_orders_base"
branch_labels = None
depends_on = None


def upgrade() -> None:  # // [PACK37-backend]
    bind = op.get_bind()
    repair_part_source = sa.Enum(
        "STOCK", "EXTERNAL", name="repair_part_source")
    repair_part_source.create(bind, checkfirst=True)

    with op.batch_alter_table(
        "repair_orders",
        schema=None,
        reflect_kwargs={"resolve_fks": False},
    ) as batch_op:
        batch_op.add_column(sa.Column("customer_contact",
                            sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("diagnosis", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("device_model", sa.String(length=120), nullable=True))
        batch_op.add_column(
            sa.Column("imei", sa.String(length=40), nullable=True))

    with op.batch_alter_table(
        "repair_order_parts",
        schema=None,
        reflect_kwargs={"resolve_fks": False},
    ) as batch_op:
        batch_op.add_column(
            sa.Column("part_name", sa.String(length=120), nullable=True))
        batch_op.add_column(
            sa.Column(
                "source",
                sa.Enum("STOCK", "EXTERNAL", name="repair_part_source"),
                nullable=False,
                server_default="STOCK",
            )
        )
        batch_op.alter_column(
            "device_id", existing_type=sa.INTEGER(), nullable=True)
        batch_op.drop_constraint("uq_repair_order_part", type_="unique")
        batch_op.create_unique_constraint(
            "uq_repair_order_part",
            ["repair_order_id", "device_id", "part_name"],
        )

    op.execute("UPDATE repair_order_parts SET source='STOCK' WHERE source IS NULL")

    with op.batch_alter_table(
        "repair_order_parts",
        schema=None,
        reflect_kwargs={"resolve_fks": False},
    ) as batch_op:
        batch_op.alter_column("source", server_default=None)


def downgrade() -> None:  # // [PACK37-backend]
    with op.batch_alter_table(
        "repair_order_parts",
        schema=None,
        reflect_kwargs={"resolve_fks": False},
    ) as batch_op:
        batch_op.drop_constraint("uq_repair_order_part", type_="unique")
        batch_op.create_unique_constraint(
            "uq_repair_order_part",
            ["repair_order_id", "device_id"],
        )
        batch_op.alter_column(
            "device_id", existing_type=sa.INTEGER(), nullable=False)
        batch_op.drop_column("source")
        batch_op.drop_column("part_name")

    with op.batch_alter_table(
        "repair_orders",
        schema=None,
        reflect_kwargs={"resolve_fks": False},
    ) as batch_op:
        batch_op.drop_column("imei")
        batch_op.drop_column("device_model")
        batch_op.drop_column("diagnosis")
        batch_op.drop_column("customer_contact")

    bind = op.get_bind()
    repair_part_source = sa.Enum(
        "STOCK", "EXTERNAL", name="repair_part_source")
    repair_part_source.drop(bind, checkfirst=True)
