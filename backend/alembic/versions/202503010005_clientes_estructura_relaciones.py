"""Estructura y relaciones para clientes."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202503010005"
down_revision = "202503010004"
branch_labels = None
depends_on = None


def _refresh_inspector(bind: sa.engine.Connection) -> sa.Inspector:
    return sa.inspect(bind)


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspector.get_columns(table)}


def _has_index(inspector: sa.Inspector, table: str, column: str) -> bool:
    for index in inspector.get_indexes(table):
        if column in (index.get("column_names") or []):
            return True
    return False


def _index_exists(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(index.get("name") == name for index in inspector.get_indexes(table))


def _has_fk(inspector: sa.Inspector, table: str, column: str, target_table: str) -> bool:
    for fk in inspector.get_foreign_keys(table):
        if (
            column in fk.get("constrained_columns", [])
            and fk.get("referred_table") == target_table
        ):
            return True
    return False


def _unique_exists(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(uc.get("name") == name for uc in inspector.get_unique_constraints(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("customers") and not inspector.has_table("clientes"):
        op.rename_table("customers", "clientes")
        inspector = _refresh_inspector(bind)

    if not inspector.has_table("clientes"):
        return

    if _has_column(inspector, "clientes", "id"):
        op.alter_column("clientes", "id", new_column_name="id_cliente")
        inspector = _refresh_inspector(bind)

    if _has_column(inspector, "clientes", "name"):
        op.alter_column("clientes", "name", new_column_name="nombre")
        inspector = _refresh_inspector(bind)

    if _has_column(inspector, "clientes", "email"):
        op.alter_column("clientes", "email", new_column_name="correo")
        inspector = _refresh_inspector(bind)

    if _has_column(inspector, "clientes", "phone"):
        op.alter_column("clientes", "phone", new_column_name="telefono")
        inspector = _refresh_inspector(bind)

    if not _has_column(inspector, "clientes", "telefono"):
        op.add_column(
            "clientes",
            sa.Column("telefono", sa.String(length=40), nullable=True),
        )
        inspector = _refresh_inspector(bind)

    op.execute(
        sa.text(
            "UPDATE clientes SET telefono = 'PENDIENTE' "
            "WHERE telefono IS NULL OR TRIM(telefono) = ''"
        )
    )
    op.alter_column(
        "clientes",
        "telefono",
        existing_type=sa.String(length=40),
        nullable=False,
    )
    inspector = _refresh_inspector(bind)

    if _has_column(inspector, "clientes", "address"):
        op.alter_column("clientes", "address", new_column_name="direccion")
        inspector = _refresh_inspector(bind)

    if _has_column(inspector, "clientes", "notes"):
        op.alter_column("clientes", "notes", new_column_name="notas")
        inspector = _refresh_inspector(bind)

    if _has_column(inspector, "clientes", "outstanding_debt"):
        op.alter_column("clientes", "outstanding_debt", new_column_name="saldo")
        inspector = _refresh_inspector(bind)

    if not _has_column(inspector, "clientes", "tipo"):
        op.add_column(
            "clientes",
            sa.Column(
                "tipo",
                sa.String(length=30),
                nullable=False,
                server_default="minorista",
            ),
        )
        op.alter_column("clientes", "tipo", server_default=None)
        inspector = _refresh_inspector(bind)

    if not _has_column(inspector, "clientes", "estado"):
        op.add_column(
            "clientes",
            sa.Column(
                "estado",
                sa.String(length=20),
                nullable=False,
                server_default="activo",
            ),
        )
        op.alter_column("clientes", "estado", server_default=None)
        inspector = _refresh_inspector(bind)

    if not _has_column(inspector, "clientes", "limite_credito"):
        op.add_column(
            "clientes",
            sa.Column(
                "limite_credito",
                sa.Numeric(12, 2),
                nullable=False,
                server_default="0",
            ),
        )
        op.alter_column("clientes", "limite_credito", server_default=None)
        inspector = _refresh_inspector(bind)

    if not _index_exists(inspector, "clientes", "ix_clientes_nombre") and not _has_index(
        inspector, "clientes", "nombre"
    ):
        op.create_index("ix_clientes_nombre", "clientes", ["nombre"], unique=True)
        inspector = _refresh_inspector(bind)

    if not _index_exists(inspector, "clientes", "ix_clientes_telefono") and not _has_index(
        inspector, "clientes", "telefono"
    ):
        op.create_index("ix_clientes_telefono", "clientes", ["telefono"])
        inspector = _refresh_inspector(bind)

    if not _index_exists(inspector, "clientes", "ix_clientes_estado") and not _has_index(
        inspector, "clientes", "estado"
    ):
        op.create_index("ix_clientes_estado", "clientes", ["estado"])
        inspector = _refresh_inspector(bind)

    if not _index_exists(inspector, "clientes", "ix_clientes_tipo") and not _has_index(
        inspector, "clientes", "tipo"
    ):
        op.create_index("ix_clientes_tipo", "clientes", ["tipo"])
        inspector = _refresh_inspector(bind)

    if not _unique_exists(inspector, "clientes", "uq_clientes_correo"):
        op.execute(
            sa.text(
                "UPDATE clientes "
                "SET correo = NULL "
                "WHERE correo IS NULL OR TRIM(correo) = ''"
            )
        )
        op.execute(
            sa.text(
                "UPDATE clientes "
                "SET correo = LOWER(TRIM(correo)) "
                "WHERE correo IS NOT NULL"
            )
        )
        op.execute(
            sa.text(
                "WITH duplicates AS ("
                "    SELECT id_cliente, correo,"
                "           ROW_NUMBER() OVER (PARTITION BY correo ORDER BY id_cliente) AS rn"
                "    FROM clientes"
                "    WHERE correo IS NOT NULL"
                ")"
                "UPDATE clientes AS c "
                "SET correo = 'duplicado+' || CAST(c.id_cliente AS TEXT) || '@invalid.local' "
                "FROM duplicates d "
                "WHERE c.id_cliente = d.id_cliente AND d.rn > 1"
            )
        )
        op.create_unique_constraint("uq_clientes_correo", "clientes", ["correo"])
        inspector = _refresh_inspector(bind)

    if inspector.has_table("ventas"):
        for fk in inspector.get_foreign_keys("ventas"):
            if fk.get("referred_table") == "customers":
                op.drop_constraint(fk.get("name"), "ventas", type_="foreignkey")
        inspector = _refresh_inspector(bind)
        if not _has_fk(inspector, "ventas", "cliente_id", "clientes"):
            op.create_foreign_key(
                "fk_ventas_cliente_id",
                "ventas",
                "clientes",
                ["cliente_id"],
                ["id_cliente"],
                ondelete="SET NULL",
            )
            inspector = _refresh_inspector(bind)

    if inspector.has_table("repair_orders"):
        for fk in inspector.get_foreign_keys("repair_orders"):
            if fk.get("referred_table") == "customers":
                op.drop_constraint(fk.get("name"), "repair_orders", type_="foreignkey")
        inspector = _refresh_inspector(bind)
        if not _has_fk(inspector, "repair_orders", "customer_id", "clientes"):
            op.create_foreign_key(
                "fk_repair_orders_customer_id",
                "repair_orders",
                "clientes",
                ["customer_id"],
                ["id_cliente"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("clientes"):
        return

    dropped_sales_fk = False
    dropped_repairs_fk = False
    if inspector.has_table("ventas"):
        for fk in inspector.get_foreign_keys("ventas"):
            if fk.get("referred_table") == "clientes":
                op.drop_constraint(fk.get("name"), "ventas", type_="foreignkey")
                dropped_sales_fk = True

    if inspector.has_table("repair_orders"):
        for fk in inspector.get_foreign_keys("repair_orders"):
            if fk.get("referred_table") == "clientes":
                op.drop_constraint(fk.get("name"), "repair_orders", type_="foreignkey")
                dropped_repairs_fk = True

    inspector = _refresh_inspector(bind)

    if _unique_exists(inspector, "clientes", "uq_clientes_correo"):
        op.drop_constraint("uq_clientes_correo", "clientes", type_="unique")

    for index_name in (
        "ix_clientes_tipo",
        "ix_clientes_estado",
        "ix_clientes_telefono",
        "ix_clientes_nombre",
    ):
        if _index_exists(inspector, "clientes", index_name):
            op.drop_index(index_name, table_name="clientes")

    if _has_column(inspector, "clientes", "limite_credito"):
        op.drop_column("clientes", "limite_credito")
    if _has_column(inspector, "clientes", "estado"):
        op.drop_column("clientes", "estado")
    if _has_column(inspector, "clientes", "tipo"):
        op.drop_column("clientes", "tipo")

    if _has_column(inspector, "clientes", "saldo"):
        op.alter_column("clientes", "saldo", new_column_name="outstanding_debt")
    if _has_column(inspector, "clientes", "notas"):
        op.alter_column("clientes", "notas", new_column_name="notes")
    if _has_column(inspector, "clientes", "direccion"):
        op.alter_column("clientes", "direccion", new_column_name="address")

    if _has_column(inspector, "clientes", "telefono"):
        op.alter_column(
            "clientes",
            "telefono",
            existing_type=sa.String(length=40),
            nullable=True,
            new_column_name="phone",
        )
    if _has_column(inspector, "clientes", "correo"):
        op.alter_column("clientes", "correo", new_column_name="email")
    if _has_column(inspector, "clientes", "nombre"):
        op.alter_column("clientes", "nombre", new_column_name="name")
    if _has_column(inspector, "clientes", "id_cliente"):
        op.alter_column("clientes", "id_cliente", new_column_name="id")

    inspector = _refresh_inspector(bind)
    if inspector.has_table("clientes") and not inspector.has_table("customers"):
        op.rename_table("clientes", "customers")

    inspector = _refresh_inspector(bind)

    if dropped_sales_fk and inspector.has_table("ventas"):
        if not _has_fk(inspector, "ventas", "cliente_id", "customers"):
            op.create_foreign_key(
                "fk_ventas_customer_id",
                "ventas",
                "customers",
                ["cliente_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if dropped_repairs_fk and inspector.has_table("repair_orders"):
        if not _has_fk(inspector, "repair_orders", "customer_id", "customers"):
            op.create_foreign_key(
                "fk_repair_orders_customer_id",
                "repair_orders",
                "customers",
                ["customer_id"],
                ["id"],
                ondelete="SET NULL",
            )
