"""Extend suppliers with RTN, payment terms, contact info and products"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202502150012_suppliers_extended_fields"
down_revision = "202502150011_inventory_smart_import"
branch_labels = None
depends_on = None


def _json_type(bind) -> sa.types.TypeEngine:
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def _json_default(bind):
    if bind.dialect.name == "sqlite":
        return sa.text("'[]'")
    return sa.text("'[]'::jsonb")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    json_type = _json_type(bind)
    json_default = _json_default(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    timestamp_default = (
        sa.text("CURRENT_TIMESTAMP")
        if is_sqlite
        else sa.text("timezone('utc', now())")
    )

    def _refresh_inspector() -> sa.Inspector:
        return sa.inspect(bind)

    if inspector.has_table("proveedores") and not inspector.has_table("suppliers"):
        op.rename_table("proveedores", "suppliers")
        inspector = _refresh_inspector()

    if not inspector.has_table("suppliers"):
        op.create_table(
            "suppliers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False, unique=True),
            sa.Column("rtn", sa.String(length=30), nullable=True, unique=True),
            sa.Column("payment_terms", sa.String(length=80), nullable=True),
            sa.Column("contact_name", sa.String(length=120), nullable=True),
            sa.Column("email", sa.String(length=120), nullable=True),
            sa.Column("phone", sa.String(length=40), nullable=True),
            sa.Column(
                "contact_info",
                json_type,
                nullable=False,
                server_default=json_default,
            ),
            sa.Column("address", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "products_supplied",
                json_type,
                nullable=False,
                server_default=json_default,
            ),
            sa.Column(
                "history",
                json_type,
                nullable=False,
                server_default=json_default,
            ),
            sa.Column(
                "outstanding_debt",
                sa.Numeric(12, 2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=timestamp_default,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=timestamp_default,
            ),
        )
        op.create_index("ix_suppliers_name", "suppliers", ["name"], unique=True)
        inspector = _refresh_inspector()
    else:
        columns = {col["name"] for col in inspector.get_columns("suppliers")}

        if "id_proveedor" in columns and "id" not in columns:
            op.alter_column("suppliers", "id_proveedor", new_column_name="id")
            inspector = _refresh_inspector()
            columns = {col["name"] for col in inspector.get_columns("suppliers")}
        if "nombre" in columns and "name" not in columns:
            op.alter_column("suppliers", "nombre", new_column_name="name")
            inspector = _refresh_inspector()
            columns = {col["name"] for col in inspector.get_columns("suppliers")}
        if "correo" in columns and "email" not in columns:
            op.alter_column("suppliers", "correo", new_column_name="email")
            inspector = _refresh_inspector()
            columns = {col["name"] for col in inspector.get_columns("suppliers")}
        if "telefono" in columns and "phone" not in columns:
            op.alter_column("suppliers", "telefono", new_column_name="phone")
            inspector = _refresh_inspector()
            columns = {col["name"] for col in inspector.get_columns("suppliers")}
        if "direccion" in columns and "address" not in columns:
            op.alter_column("suppliers", "direccion", new_column_name="address")
            inspector = _refresh_inspector()
            columns = {col["name"] for col in inspector.get_columns("suppliers")}
        if "notas" in columns and "notes" not in columns:
            op.alter_column("suppliers", "notas", new_column_name="notes")
            inspector = _refresh_inspector()
            columns = {col["name"] for col in inspector.get_columns("suppliers")}

        columns = {col["name"] for col in inspector.get_columns("suppliers")}
        if "contact_name" not in columns:
            op.add_column(
                "suppliers",
                sa.Column("contact_name", sa.String(length=120), nullable=True),
            )
        if "rtn" not in columns:
            op.add_column(
                "suppliers",
                sa.Column("rtn", sa.String(length=30), nullable=True),
            )
        if "payment_terms" not in columns:
            op.add_column(
                "suppliers",
                sa.Column("payment_terms", sa.String(length=80), nullable=True),
            )
        if "contact_info" not in columns:
            op.add_column(
                "suppliers",
                sa.Column(
                    "contact_info",
                    json_type,
                    nullable=False,
                    server_default=json_default,
                ),
            )
        if "products_supplied" not in columns:
            op.add_column(
                "suppliers",
                sa.Column(
                    "products_supplied",
                    json_type,
                    nullable=False,
                    server_default=json_default,
                ),
            )
        if "history" not in columns:
            op.add_column(
                "suppliers",
                sa.Column(
                    "history",
                    json_type,
                    nullable=False,
                    server_default=json_default,
                ),
            )
        if "outstanding_debt" not in columns:
            op.add_column(
                "suppliers",
                sa.Column(
                    "outstanding_debt",
                    sa.Numeric(12, 2),
                    nullable=False,
                    server_default="0",
                ),
            )
        if "created_at" not in columns:
            op.add_column(
                "suppliers",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=timestamp_default,
                ),
            )
        if "updated_at" not in columns:
            op.add_column(
                "suppliers",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=timestamp_default,
                ),
            )

        indexes = {index["name"] for index in inspector.get_indexes("suppliers")}
        for legacy_index in {
            "ix_proveedores_nombre",
            "ix_proveedores_telefono",
            "ix_proveedores_estado",
            "ix_proveedores_tipo",
        }:
            if legacy_index in indexes:
                op.drop_index(legacy_index, table_name="suppliers")
        inspector = _refresh_inspector()
        indexes = {index["name"] for index in inspector.get_indexes("suppliers")}
        if "ix_suppliers_name" not in indexes:
            op.create_index("ix_suppliers_name", "suppliers", ["name"], unique=True)

    op.create_index(
        "ix_suppliers_rtn",
        "suppliers",
        ["rtn"],
        unique=True,
    )

    if not is_sqlite:
        for column in ("contact_info", "products_supplied", "history"):
            op.alter_column("suppliers", column, server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("suppliers"):
        op.drop_index("ix_suppliers_rtn", table_name="suppliers")
        indexes = {index["name"] for index in inspector.get_indexes("suppliers")}
        if "ix_suppliers_name" in indexes:
            op.drop_index("ix_suppliers_name", table_name="suppliers")
        existing_columns = {col["name"] for col in inspector.get_columns("suppliers")}

        for column in (
            "products_supplied",
            "contact_info",
            "payment_terms",
            "rtn",
            "contact_name",
            "history",
            "outstanding_debt",
            "updated_at",
            "created_at",
        ):
            if column in existing_columns:
                op.drop_column("suppliers", column)
        inspector = sa.inspect(bind)
        existing_columns = {col["name"] for col in inspector.get_columns("suppliers")}

        if "notes" in existing_columns:
            op.alter_column("suppliers", "notes", new_column_name="notas")
        if "address" in existing_columns:
            op.alter_column("suppliers", "address", new_column_name="direccion")
        if "phone" in existing_columns:
            op.alter_column("suppliers", "phone", new_column_name="telefono")
        if "email" in existing_columns:
            op.alter_column("suppliers", "email", new_column_name="correo")
        if "name" in existing_columns:
            op.alter_column("suppliers", "name", new_column_name="nombre")
        if "id" in existing_columns:
            op.alter_column("suppliers", "id", new_column_name="id_proveedor")

        if inspector.has_table("suppliers"):
            op.rename_table("suppliers", "proveedores")
