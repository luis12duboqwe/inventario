"""Agregar columnas de desglose de montos en ventas"""

from decimal import Decimal, ROUND_HALF_UP

from alembic import op
import sqlalchemy as sa


revision = "202502150007"
down_revision = "202502150006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column(
            "subtotal_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "sales",
        sa.Column(
            "tax_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )

    connection = op.get_bind()
    metadata = sa.MetaData()

    sales_table = sa.Table("sales", metadata, autoload_with=connection)
    sale_items_table = sa.Table("sale_items", metadata, autoload_with=connection)
    pos_configs_table = sa.Table("pos_configs", metadata, autoload_with=connection)

    subtotal_per_sale = {
        row.sale_id: row.subtotal
        for row in connection.execute(
            sa.select(
                sale_items_table.c.sale_id,
                sa.func.coalesce(
                    sa.func.sum(sale_items_table.c.total_line),
                    sa.literal(0).cast(sa.Numeric(12, 2)),
                ).label("subtotal"),
            ).group_by(sale_items_table.c.sale_id)
        )
    }

    tax_rate_per_store = {
        row.store_id: row.tax_rate
        for row in connection.execute(
            sa.select(
                pos_configs_table.c.store_id,
                sa.func.coalesce(pos_configs_table.c.tax_rate, sa.literal(0)).label(
                    "tax_rate"
                ),
            )
        )
    }

    decimal_quantize = Decimal("0.01")

    for sale in connection.execute(
        sa.select(
            sales_table.c.id,
            sales_table.c.store_id,
            sales_table.c.total_amount,
        )
    ):
        subtotal = subtotal_per_sale.get(sale.id, Decimal("0"))
        if not isinstance(subtotal, Decimal):
            subtotal = Decimal(subtotal)
        subtotal = subtotal.quantize(decimal_quantize, rounding=ROUND_HALF_UP)

        total_amount = sale.total_amount or Decimal("0")
        if not isinstance(total_amount, Decimal):
            total_amount = Decimal(total_amount)
        total_amount = total_amount.quantize(decimal_quantize, rounding=ROUND_HALF_UP)

        computed_tax = (total_amount - subtotal).quantize(
            decimal_quantize, rounding=ROUND_HALF_UP
        )
        if computed_tax < Decimal("0"):
            computed_tax = Decimal("0")

        should_infer_from_config = (
            computed_tax == Decimal("0")
            and subtotal > Decimal("0")
            and total_amount == Decimal("0")
        )

        if should_infer_from_config:
            tax_rate = tax_rate_per_store.get(sale.store_id, Decimal("0")) or Decimal("0")
            if not isinstance(tax_rate, Decimal):
                tax_rate = Decimal(tax_rate)
            if tax_rate > Decimal("0") and subtotal > Decimal("0"):
                tax_fraction = tax_rate / Decimal("100")
                computed_tax = (subtotal * tax_fraction).quantize(
                    decimal_quantize, rounding=ROUND_HALF_UP
                )
                total_amount = (subtotal + computed_tax).quantize(
                    decimal_quantize, rounding=ROUND_HALF_UP
                )

        update_values = {
            "subtotal_amount": subtotal,
            "tax_amount": computed_tax,
        }

        if should_infer_from_config and computed_tax > Decimal("0"):
            update_values["total_amount"] = total_amount

        connection.execute(
            sa.update(sales_table)
            .where(sales_table.c.id == sale.id)
            .values(**update_values)
        )

    op.alter_column("sales", "subtotal_amount", server_default=None)
    op.alter_column("sales", "tax_amount", server_default=None)


def downgrade() -> None:
    op.drop_column("sales", "tax_amount")
    op.drop_column("sales", "subtotal_amount")
