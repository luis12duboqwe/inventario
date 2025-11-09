"""Agregar umbrales de stock a dispositivos y variantes."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = "202511070005"
down_revision = "202511070004"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _update_variant_defaults(bind: Connection) -> None:
    if not _table_exists(bind, "device_variants"):
        return
    op.execute("UPDATE device_variants SET minimum_stock = 0 WHERE minimum_stock IS NULL")
    op.execute(
        "UPDATE device_variants SET reorder_point = minimum_stock "
        "WHERE reorder_point IS NULL OR reorder_point < minimum_stock"
    )


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("minimum_stock", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "devices",
        sa.Column("reorder_point", sa.Integer(), nullable=False, server_default="0"),
    )
    bind = op.get_bind()
    op.execute("UPDATE devices SET minimum_stock = 0 WHERE minimum_stock IS NULL")
    op.execute(
        "UPDATE devices SET reorder_point = minimum_stock "
        "WHERE reorder_point IS NULL OR reorder_point < minimum_stock"
    )
    if _table_exists(bind, "device_variants"):
        op.add_column(
            "device_variants",
            sa.Column("minimum_stock", sa.Integer(), nullable=False, server_default="0"),
        )
        op.add_column(
            "device_variants",
            sa.Column("reorder_point", sa.Integer(), nullable=False, server_default="0"),
        )
        _update_variant_defaults(bind)
    if bind.dialect.name != "sqlite":
        op.alter_column("devices", "minimum_stock", server_default=None)
        op.alter_column("devices", "reorder_point", server_default=None)
        if _table_exists(bind, "device_variants"):
            op.alter_column("device_variants", "minimum_stock", server_default=None)
            op.alter_column("device_variants", "reorder_point", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "device_variants"):
        op.drop_column("device_variants", "reorder_point")
        op.drop_column("device_variants", "minimum_stock")
    op.drop_column("devices", "reorder_point")
    op.drop_column("devices", "minimum_stock")
