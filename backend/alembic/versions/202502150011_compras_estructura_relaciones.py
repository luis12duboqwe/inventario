"""Asegura estructuras base de compras y proveedores."""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision = "202502150011"
down_revision = "202502150010"
branch_labels = None
depends_on = None


def _table_columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _foreign_key_exists(
    inspector: sa.Inspector,
    table_name: str,
    constrained_columns: Sequence[str],
    referred_table: str,
    referred_columns: Sequence[str],
) -> bool:
    constrained = set(constrained_columns)
    referred = set(referred_columns)
    for fk in inspector.get_foreign_keys(table_name):
        if set(fk.get("constrained_columns", ())) != constrained:
            continue
        if fk.get("referred_table") != referred_table:
            continue
        if set(fk.get("referred_columns", ())) != referred:
            continue
        return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("proveedores"):
        op.create_table(
            "proveedores",
            sa.Column("id_proveedor", sa.Integer(), primary_key=True),
            sa.Column("nombre", sa.String(length=150), nullable=False, unique=True),
            sa.Column("telefono", sa.String(length=40), nullable=True),
            sa.Column("correo", sa.String(length=120), nullable=True),
            sa.Column("direccion", sa.String(length=255), nullable=True),
            sa.Column("tipo", sa.String(length=60), nullable=True),
            sa.Column(
                "estado",
                sa.String(length=40),
                nullable=False,
                server_default="activo",
            ),
            sa.Column("notas", sa.Text(), nullable=True),
        )
        op.create_index(
            "ix_proveedores_nombre", "proveedores", ["nombre"], unique=True
        )
    else:
        existing_columns = _table_columns(inspector, "proveedores")
        if "tipo" not in existing_columns:
            op.add_column(
                "proveedores", sa.Column("tipo", sa.String(length=60), nullable=True)
            )
        if "estado" not in existing_columns:
            op.add_column(
                "proveedores",
                sa.Column(
                    "estado",
                    sa.String(length=40),
                    nullable=False,
                    server_default="activo",
                ),
            )
        if "notas" not in existing_columns:
            op.add_column("proveedores", sa.Column("notas", sa.Text(), nullable=True))
        inspector = sa.inspect(bind)
        indexes = _index_names(inspector, "proveedores")
        if "ix_proveedores_nombre" not in indexes:
            op.create_index(
                "ix_proveedores_nombre",
                "proveedores",
                ["nombre"],
                unique=True,
            )

    inspector = sa.inspect(bind)
    if not inspector.has_table("compras"):
        op.create_table(
            "compras",
            sa.Column("id_compra", sa.Integer(), primary_key=True),
            sa.Column("proveedor_id", sa.Integer(), nullable=False),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column(
                "fecha",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "total",
                sa.Numeric(14, 2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "impuesto",
                sa.Numeric(12, 2),
                nullable=False,
                server_default="0",
            ),
            sa.Column("forma_pago", sa.String(length=60), nullable=False),
            sa.Column(
                "estado", sa.String(length=40), nullable=False, server_default="PENDIENTE"
            ),
            sa.ForeignKeyConstraint(
                ["proveedor_id"],
                ["proveedores.id_proveedor"],
                name="fk_compras_proveedor_id_proveedores",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["usuario_id"],
                ["users.id"],
                name="fk_compras_usuario_id_users",
                ondelete="RESTRICT",
            ),
        )
        op.create_index("ix_compras_proveedor_id", "compras", ["proveedor_id"])
        op.create_index("ix_compras_usuario_id", "compras", ["usuario_id"])
    else:
        existing_columns = _table_columns(inspector, "compras")
        if "impuesto" not in existing_columns:
            op.add_column(
                "compras",
                sa.Column(
                    "impuesto",
                    sa.Numeric(12, 2),
                    nullable=False,
                    server_default="0",
                ),
            )
        if "forma_pago" not in existing_columns:
            op.add_column(
                "compras",
                sa.Column("forma_pago", sa.String(length=60), nullable=False),
            )
        if "estado" not in existing_columns:
            op.add_column(
                "compras",
                sa.Column(
                    "estado",
                    sa.String(length=40),
                    nullable=False,
                    server_default="PENDIENTE",
                ),
            )
        inspector = sa.inspect(bind)
        indexes = _index_names(inspector, "compras")
        if "ix_compras_proveedor_id" not in indexes:
            op.create_index("ix_compras_proveedor_id", "compras", ["proveedor_id"])
        if "ix_compras_usuario_id" not in indexes:
            op.create_index("ix_compras_usuario_id", "compras", ["usuario_id"])
        inspector = sa.inspect(bind)
        if not _foreign_key_exists(
            inspector,
            "compras",
            ["proveedor_id"],
            "proveedores",
            ["id_proveedor"],
        ):
            op.create_foreign_key(
                "fk_compras_proveedor_id_proveedores",
                "compras",
                "proveedores",
                ["proveedor_id"],
                ["id_proveedor"],
                ondelete="RESTRICT",
            )
        inspector = sa.inspect(bind)
        if not _foreign_key_exists(
            inspector,
            "compras",
            ["usuario_id"],
            "users",
            ["id"],
        ):
            op.create_foreign_key(
                "fk_compras_usuario_id_users",
                "compras",
                "users",
                ["usuario_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    inspector = sa.inspect(bind)
    if not inspector.has_table("detalle_compras"):
        op.create_table(
            "detalle_compras",
            sa.Column("id_detalle", sa.Integer(), primary_key=True),
            sa.Column("compra_id", sa.Integer(), nullable=False),
            sa.Column("producto_id", sa.Integer(), nullable=False),
            sa.Column("cantidad", sa.Integer(), nullable=False),
            sa.Column(
                "costo_unitario",
                sa.Numeric(12, 2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "subtotal",
                sa.Numeric(14, 2),
                nullable=False,
                server_default="0",
            ),
            sa.ForeignKeyConstraint(
                ["compra_id"],
                ["compras.id_compra"],
                name="fk_detalle_compras_compra_id_compras",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["producto_id"],
                ["devices.id"],
                name="fk_detalle_compras_producto_id_devices",
                ondelete="RESTRICT",
            ),
        )
        op.create_index(
            "ix_detalle_compras_compra_id", "detalle_compras", ["compra_id"]
        )
        op.create_index(
            "ix_detalle_compras_producto_id", "detalle_compras", ["producto_id"]
        )
    else:
        existing_columns = _table_columns(inspector, "detalle_compras")
        if "costo_unitario" not in existing_columns:
            op.add_column(
                "detalle_compras",
                sa.Column(
                    "costo_unitario",
                    sa.Numeric(12, 2),
                    nullable=False,
                    server_default="0",
                ),
            )
        if "subtotal" not in existing_columns:
            op.add_column(
                "detalle_compras",
                sa.Column(
                    "subtotal",
                    sa.Numeric(14, 2),
                    nullable=False,
                    server_default="0",
                ),
            )
        inspector = sa.inspect(bind)
        indexes = _index_names(inspector, "detalle_compras")
        if "ix_detalle_compras_compra_id" not in indexes:
            op.create_index(
                "ix_detalle_compras_compra_id",
                "detalle_compras",
                ["compra_id"],
            )
        if "ix_detalle_compras_producto_id" not in indexes:
            op.create_index(
                "ix_detalle_compras_producto_id",
                "detalle_compras",
                ["producto_id"],
            )
        inspector = sa.inspect(bind)
        if not _foreign_key_exists(
            inspector,
            "detalle_compras",
            ["compra_id"],
            "compras",
            ["id_compra"],
        ):
            op.create_foreign_key(
                "fk_detalle_compras_compra_id_compras",
                "detalle_compras",
                "compras",
                ["compra_id"],
                ["id_compra"],
                ondelete="CASCADE",
            )
        inspector = sa.inspect(bind)
        if not _foreign_key_exists(
            inspector,
            "detalle_compras",
            ["producto_id"],
            "devices",
            ["id"],
        ):
            op.create_foreign_key(
                "fk_detalle_compras_producto_id_devices",
                "detalle_compras",
                "devices",
                ["producto_id"],
                ["id"],
                ondelete="RESTRICT",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("detalle_compras"):
        op.drop_table("detalle_compras")
        inspector = sa.inspect(bind)

    if inspector.has_table("compras"):
        op.drop_table("compras")
        inspector = sa.inspect(bind)

    if inspector.has_table("proveedores"):
        indexes = _index_names(inspector, "proveedores")
        if "ix_proveedores_nombre" in indexes:
            op.drop_index("ix_proveedores_nombre", table_name="proveedores")
        op.drop_table("proveedores")
