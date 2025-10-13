"""Transferencias entre sucursales y membresías por tienda."""
from alembic import op
import sqlalchemy as sa


revision = "202502150004"
down_revision = "202502150003"
branch_labels = None
depends_on = None

TRANSFER_STATUS_NAME = "transfer_status"


def upgrade() -> None:
    bind = op.get_bind()
    transfer_status = sa.Enum(
        "SOLICITADA",
        "EN_TRANSITO",
        "RECIBIDA",
        "CANCELADA",
        name=TRANSFER_STATUS_NAME,
    )
    transfer_status.create(bind, checkfirst=True)

    op.create_table(
        "store_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("can_create_transfer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("can_receive_transfer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "store_id", name="uq_membership_user_store"),
    )
    op.create_index("ix_store_memberships_user_id", "store_memberships", ["user_id"])
    op.create_index("ix_store_memberships_store_id", "store_memberships", ["store_id"])

    op.create_table(
        "transfer_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("origin_store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destination_store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", transfer_status, nullable=False, server_default="SOLICITADA"),
        sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dispatched_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("received_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cancelled_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Index("ix_transfer_orders_origin_store_id", "origin_store_id"),
        sa.Index("ix_transfer_orders_destination_store_id", "destination_store_id"),
        sa.Index("ix_transfer_orders_status", "status"),
    )

    op.create_table(
        "transfer_order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transfer_order_id", sa.Integer(), sa.ForeignKey("transfer_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.UniqueConstraint("transfer_order_id", "device_id", name="uq_transfer_item_unique"),
    )
    op.create_index("ix_transfer_order_items_transfer_order_id", "transfer_order_items", ["transfer_order_id"])
    op.create_index("ix_transfer_order_items_device_id", "transfer_order_items", ["device_id"])

    op.alter_column("transfer_orders", "status", server_default=None)
    op.alter_column("store_memberships", "can_create_transfer", server_default=None)
    op.alter_column("store_memberships", "can_receive_transfer", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_transfer_order_items_device_id", table_name="transfer_order_items")
    op.drop_index("ix_transfer_order_items_transfer_order_id", table_name="transfer_order_items")
    op.drop_table("transfer_order_items")

    op.drop_index("ix_transfer_orders_status", table_name="transfer_orders")
    op.drop_index("ix_transfer_orders_destination_store_id", table_name="transfer_orders")
    op.drop_index("ix_transfer_orders_origin_store_id", table_name="transfer_orders")
    op.drop_table("transfer_orders")

    op.drop_index("ix_store_memberships_store_id", table_name="store_memberships")
    op.drop_index("ix_store_memberships_user_id", table_name="store_memberships")
    op.drop_table("store_memberships")

    transfer_status = sa.Enum(name=TRANSFER_STATUS_NAME)
    transfer_status.drop(op.get_bind(), checkfirst=True)
