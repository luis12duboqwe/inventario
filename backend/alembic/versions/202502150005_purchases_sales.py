from alembic import op
import sqlalchemy as sa

revision = "202502150005"
down_revision = "202502150004"
branch_labels = None
depends_on = None

PURCHASE_STATUS_NAME = "purchase_status"
PAYMENT_METHOD_NAME = "payment_method"


def upgrade() -> None:
    bind = op.get_bind()

    purchase_status = sa.Enum(
        "PENDIENTE",
        "PARCIAL",
        "COMPLETADA",
        "CANCELADA",
        name=PURCHASE_STATUS_NAME,
    )
    payment_method = sa.Enum(
        "EFECTIVO",
        "TARJETA",
        "TRANSFERENCIA",
        "OTRO",
        name=PAYMENT_METHOD_NAME,
    )
    purchase_status.create(bind, checkfirst=True)
    payment_method.create(bind, checkfirst=True)

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("supplier", sa.String(length=120), nullable=False),
        sa.Column("status", purchase_status, nullable=False, server_default="PENDIENTE"),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Index("ix_purchase_orders_store_id", "store_id"),
        sa.Index("ix_purchase_orders_status", "status"),
    )

    op.create_table(
        "purchase_order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_order_id", sa.Integer(), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_ordered", sa.Integer(), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.UniqueConstraint("purchase_order_id", "device_id", name="uq_purchase_item_unique"),
    )
    op.create_index("ix_purchase_order_items_order_id", "purchase_order_items", ["purchase_order_id"])
    op.create_index("ix_purchase_order_items_device_id", "purchase_order_items", ["device_id"])

    op.create_table(
        "purchase_returns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_order_id", sa.Integer(), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("processed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index("ix_purchase_returns_order_id", "purchase_order_id"),
        sa.Index("ix_purchase_returns_device_id", "device_id"),
    )

    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_name", sa.String(length=120), nullable=True),
        sa.Column("payment_method", payment_method, nullable=False, server_default="EFECTIVO"),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("performed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Index("ix_sales_store_id", "store_id"),
        sa.Index("ix_sales_created_at", "created_at"),
    )

    op.create_table(
        "sale_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_line", sa.Numeric(12, 2), nullable=False),
        sa.Index("ix_sale_items_sale_id", "sale_id"),
        sa.Index("ix_sale_items_device_id", "device_id"),
    )

    op.create_table(
        "sale_returns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("processed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index("ix_sale_returns_sale_id", "sale_id"),
        sa.Index("ix_sale_returns_device_id", "device_id"),
    )

    op.alter_column("purchase_orders", "status", server_default=None)
    op.alter_column("purchase_order_items", "quantity_received", server_default=None)
    op.alter_column("purchase_order_items", "unit_cost", server_default=None)
    op.alter_column("sales", "payment_method", server_default=None)
    op.alter_column("sales", "discount_percent", server_default=None)
    op.alter_column("sales", "total_amount", server_default=None)
    op.alter_column("sale_items", "discount_amount", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_sale_returns_device_id", table_name="sale_returns")
    op.drop_index("ix_sale_returns_sale_id", table_name="sale_returns")
    op.drop_table("sale_returns")

    op.drop_index("ix_sale_items_device_id", table_name="sale_items")
    op.drop_index("ix_sale_items_sale_id", table_name="sale_items")
    op.drop_table("sale_items")

    op.drop_index("ix_sales_created_at", table_name="sales")
    op.drop_index("ix_sales_store_id", table_name="sales")
    op.drop_table("sales")

    op.drop_index("ix_purchase_returns_device_id", table_name="purchase_returns")
    op.drop_index("ix_purchase_returns_order_id", table_name="purchase_returns")
    op.drop_table("purchase_returns")

    op.drop_index("ix_purchase_order_items_device_id", table_name="purchase_order_items")
    op.drop_index("ix_purchase_order_items_order_id", table_name="purchase_order_items")
    op.drop_table("purchase_order_items")

    op.drop_index("ix_purchase_orders_status", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_store_id", table_name="purchase_orders")
    op.drop_table("purchase_orders")

    purchase_status = sa.Enum(name=PURCHASE_STATUS_NAME)
    payment_method = sa.Enum(name=PAYMENT_METHOD_NAME)
    purchase_status.drop(op.get_bind(), checkfirst=True)
    payment_method.drop(op.get_bind(), checkfirst=True)
