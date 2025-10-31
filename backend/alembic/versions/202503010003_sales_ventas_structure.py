"""Estructura en español para ventas y detalle de ventas."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202503010003"
down_revision = "202503010002"
branch_labels = None
depends_on = None


def _refresh_inspector(bind: sa.engine.Connection) -> sa.Inspector:
    """Genera un inspector actualizado para la conexión."""

    return sa.inspect(bind)


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspector.get_columns(table)}


def _has_fk(inspector: sa.Inspector, table: str, column: str, target: str) -> bool:
    for fk in inspector.get_foreign_keys(table):
        if column in fk.get("constrained_columns", []) and fk.get("referred_table") == target:
            return True
    return False


def _has_index(inspector: sa.Inspector, table: str, column: str) -> bool:
    for index in inspector.get_indexes(table):
        if column in (index.get("column_names") or []):
            return True
    return False


def _index_exists(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(index.get("name") == name for index in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("sales"):
        op.rename_table("sales", "ventas")
    if inspector.has_table("sale_items"):
        op.rename_table("sale_items", "detalle_ventas")

    inspector = _refresh_inspector(bind)

    if inspector.has_table("ventas"):
        if _has_column(inspector, "ventas", "id"):
            op.alter_column("ventas", "id", new_column_name="id_venta")
            inspector = _refresh_inspector(bind)

        if _has_column(inspector, "ventas", "customer_id"):
            op.alter_column("ventas", "customer_id", new_column_name="cliente_id")
            inspector = _refresh_inspector(bind)
        if not _has_column(inspector, "ventas", "cliente_id"):
            op.add_column("ventas", sa.Column("cliente_id", sa.Integer(), nullable=True))
            inspector = _refresh_inspector(bind)
        if not _has_fk(inspector, "ventas", "cliente_id", "customers"):
            op.create_foreign_key(
                "fk_ventas_cliente_id",
                "ventas",
                "customers",
                ["cliente_id"],
                ["id"],
                ondelete="SET NULL",
            )
            inspector = _refresh_inspector(bind)
        if not _index_exists(inspector, "ventas", "ix_ventas_cliente_id") and not _has_index(
            inspector, "ventas", "cliente_id"
        ):
            op.create_index("ix_ventas_cliente_id", "ventas", ["cliente_id"])
            inspector = _refresh_inspector(bind)

        if _has_column(inspector, "ventas", "performed_by_id"):
            op.alter_column("ventas", "performed_by_id", new_column_name="usuario_id")
            inspector = _refresh_inspector(bind)
        if not _has_column(inspector, "ventas", "usuario_id"):
            op.add_column("ventas", sa.Column("usuario_id", sa.Integer(), nullable=True))
            inspector = _refresh_inspector(bind)
        if not _has_fk(inspector, "ventas", "usuario_id", "users"):
            op.create_foreign_key(
                "fk_ventas_usuario_id",
                "ventas",
                "users",
                ["usuario_id"],
                ["id"],
                ondelete="SET NULL",
            )
            inspector = _refresh_inspector(bind)
        if not _index_exists(inspector, "ventas", "ix_ventas_usuario_id") and not _has_index(
            inspector, "ventas", "usuario_id"
        ):
            op.create_index("ix_ventas_usuario_id", "ventas", ["usuario_id"])
            inspector = _refresh_inspector(bind)

        if _has_column(inspector, "ventas", "created_at"):
            op.alter_column("ventas", "created_at", new_column_name="fecha")
            inspector = _refresh_inspector(bind)
        if not _has_column(inspector, "ventas", "fecha"):
            op.add_column(
                "ventas",
                sa.Column(
                    "fecha",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                ),
            )
            op.alter_column("ventas", "fecha", server_default=None)
            inspector = _refresh_inspector(bind)

        if _has_column(inspector, "ventas", "total_amount"):
            op.alter_column("ventas", "total_amount", new_column_name="total")
            inspector = _refresh_inspector(bind)
        if not _has_column(inspector, "ventas", "total"):
            op.add_column(
                "ventas",
                sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
            )
            op.alter_column("ventas", "total", server_default=None)
            inspector = _refresh_inspector(bind)

        if _has_column(inspector, "ventas", "tax_amount"):
            op.alter_column("ventas", "tax_amount", new_column_name="impuesto")
            inspector = _refresh_inspector(bind)
        if not _has_column(inspector, "ventas", "impuesto"):
            op.add_column(
                "ventas",
                sa.Column("impuesto", sa.Numeric(12, 2), nullable=False, server_default="0"),
            )
            op.alter_column("ventas", "impuesto", server_default=None)
            inspector = _refresh_inspector(bind)

        if _has_column(inspector, "ventas", "payment_method"):
            op.alter_column("ventas", "payment_method", new_column_name="forma_pago")
            inspector = _refresh_inspector(bind)

        if _has_column(inspector, "ventas", "subtotal_amount"):
            op.alter_column("ventas", "subtotal_amount", new_column_name="subtotal")
            inspector = _refresh_inspector(bind)
        if not _has_column(inspector, "ventas", "subtotal"):
            op.add_column(
                "ventas",
                sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
            )
            op.alter_column("ventas", "subtotal", server_default=None)
            inspector = _refresh_inspector(bind)

        if not _has_column(inspector, "ventas", "estado"):
            op.add_column(
                "ventas",
                sa.Column(
                    "estado",
                    sa.String(length=30),
                    nullable=False,
                    server_default="COMPLETADA",
                ),
            )
            op.alter_column("ventas", "estado", server_default=None)
            inspector = _refresh_inspector(bind)

    if inspector.has_table("detalle_ventas"):
        if _has_column(inspector, "detalle_ventas", "id"):
            op.alter_column("detalle_ventas", "id", new_column_name="id_detalle")
            inspector = _refresh_inspector(bind)

        if _has_column(inspector, "detalle_ventas", "sale_id"):
            op.alter_column("detalle_ventas", "sale_id", new_column_name="venta_id")
            inspector = _refresh_inspector(bind)
        if not _has_fk(inspector, "detalle_ventas", "venta_id", "ventas"):
            op.create_foreign_key(
                "fk_detalle_ventas_venta_id",
                "detalle_ventas",
                "ventas",
                ["venta_id"],
                ["id_venta"],
                ondelete="CASCADE",
            )
            inspector = _refresh_inspector(bind)
        if not _index_exists(
            inspector, "detalle_ventas", "ix_detalle_ventas_venta_id"
        ) and not _has_index(inspector, "detalle_ventas", "venta_id"):
            op.create_index("ix_detalle_ventas_venta_id", "detalle_ventas", ["venta_id"])
            inspector = _refresh_inspector(bind)

        if _has_column(inspector, "detalle_ventas", "device_id"):
            op.alter_column("detalle_ventas", "device_id", new_column_name="producto_id")
            inspector = _refresh_inspector(bind)
        if not _has_fk(inspector, "detalle_ventas", "producto_id", "devices"):
            op.create_foreign_key(
                "fk_detalle_ventas_producto_id",
                "detalle_ventas",
                "devices",
                ["producto_id"],
                ["id"],
                ondelete="RESTRICT",
            )
            inspector = _refresh_inspector(bind)
        if not _index_exists(
            inspector, "detalle_ventas", "ix_detalle_ventas_producto_id"
        ) and not _has_index(inspector, "detalle_ventas", "producto_id"):
            op.create_index("ix_detalle_ventas_producto_id", "detalle_ventas", ["producto_id"])
            inspector = _refresh_inspector(bind)

        if _has_column(inspector, "detalle_ventas", "unit_price"):
            op.alter_column(
                "detalle_ventas",
                "unit_price",
                new_column_name="precio_unitario",
            )
            inspector = _refresh_inspector(bind)
        if _has_column(inspector, "detalle_ventas", "total_line"):
            op.alter_column("detalle_ventas", "total_line", new_column_name="subtotal")
            inspector = _refresh_inspector(bind)
        if not _has_column(inspector, "detalle_ventas", "subtotal"):
            op.add_column(
                "detalle_ventas",
                sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
            )
            op.alter_column("detalle_ventas", "subtotal", server_default=None)
            inspector = _refresh_inspector(bind)

    if inspector.has_table("sale_returns"):
        if _has_column(inspector, "sale_returns", "sale_id"):
            op.alter_column("sale_returns", "sale_id", new_column_name="venta_id")
            inspector = _refresh_inspector(bind)
        if not _has_fk(inspector, "sale_returns", "venta_id", "ventas"):
            op.create_foreign_key(
                "fk_sale_returns_venta_id",
                "sale_returns",
                "ventas",
                ["venta_id"],
                ["id_venta"],
                ondelete="CASCADE",
            )
            inspector = _refresh_inspector(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("sale_returns"):
        if _has_fk(inspector, "sale_returns", "venta_id", "ventas"):
            op.drop_constraint("fk_sale_returns_venta_id", "sale_returns", type_="foreignkey")
        if _has_column(inspector, "sale_returns", "venta_id"):
            op.alter_column("sale_returns", "venta_id", new_column_name="sale_id")
        inspector = _refresh_inspector(bind)

    if inspector.has_table("detalle_ventas"):
        if _has_fk(inspector, "detalle_ventas", "venta_id", "ventas"):
            op.drop_constraint("fk_detalle_ventas_venta_id", "detalle_ventas", type_="foreignkey")
        if _index_exists(inspector, "detalle_ventas", "ix_detalle_ventas_venta_id"):
            op.drop_index("ix_detalle_ventas_venta_id", table_name="detalle_ventas")
        if _has_fk(inspector, "detalle_ventas", "producto_id", "devices"):
            op.drop_constraint("fk_detalle_ventas_producto_id", "detalle_ventas", type_="foreignkey")
        if _index_exists(inspector, "detalle_ventas", "ix_detalle_ventas_producto_id"):
            op.drop_index("ix_detalle_ventas_producto_id", table_name="detalle_ventas")
        if _has_column(inspector, "detalle_ventas", "subtotal"):
            op.alter_column("detalle_ventas", "subtotal", new_column_name="total_line")
        if _has_column(inspector, "detalle_ventas", "precio_unitario"):
            op.alter_column(
                "detalle_ventas",
                "precio_unitario",
                new_column_name="unit_price",
            )
        if _has_column(inspector, "detalle_ventas", "producto_id"):
            op.alter_column("detalle_ventas", "producto_id", new_column_name="device_id")
        if _has_column(inspector, "detalle_ventas", "venta_id"):
            op.alter_column("detalle_ventas", "venta_id", new_column_name="sale_id")
        if _has_column(inspector, "detalle_ventas", "id_detalle"):
            op.alter_column("detalle_ventas", "id_detalle", new_column_name="id")
        inspector = _refresh_inspector(bind)

    if inspector.has_table("ventas"):
        if _index_exists(inspector, "ventas", "ix_ventas_usuario_id"):
            op.drop_index("ix_ventas_usuario_id", table_name="ventas")
        if _has_fk(inspector, "ventas", "usuario_id", "users"):
            op.drop_constraint("fk_ventas_usuario_id", "ventas", type_="foreignkey")
        if _has_column(inspector, "ventas", "usuario_id"):
            op.alter_column("ventas", "usuario_id", new_column_name="performed_by_id")

        if _index_exists(inspector, "ventas", "ix_ventas_cliente_id"):
            op.drop_index("ix_ventas_cliente_id", table_name="ventas")
        if _has_fk(inspector, "ventas", "cliente_id", "customers"):
            op.drop_constraint("fk_ventas_cliente_id", "ventas", type_="foreignkey")
        if _has_column(inspector, "ventas", "cliente_id"):
            op.alter_column("ventas", "cliente_id", new_column_name="customer_id")

        if _has_column(inspector, "ventas", "estado"):
            op.drop_column("ventas", "estado")
        if not _has_column(inspector, "ventas", "subtotal_amount") and _has_column(
            inspector, "ventas", "subtotal"
        ):
            op.alter_column("ventas", "subtotal", new_column_name="subtotal_amount")
        if _has_column(inspector, "ventas", "forma_pago"):
            op.alter_column("ventas", "forma_pago", new_column_name="payment_method")
        if _has_column(inspector, "ventas", "impuesto"):
            op.alter_column("ventas", "impuesto", new_column_name="tax_amount")
        if _has_column(inspector, "ventas", "total"):
            op.alter_column("ventas", "total", new_column_name="total_amount")
        if _has_column(inspector, "ventas", "fecha"):
            op.alter_column("ventas", "fecha", new_column_name="created_at")
        if _has_column(inspector, "ventas", "id_venta"):
            op.alter_column("ventas", "id_venta", new_column_name="id")
        inspector = _refresh_inspector(bind)

    inspector = sa.inspect(bind)
    if inspector.has_table("ventas"):
        op.rename_table("ventas", "sales")
    inspector = sa.inspect(bind)
    if inspector.has_table("detalle_ventas"):
        op.rename_table("detalle_ventas", "sale_items")
***
