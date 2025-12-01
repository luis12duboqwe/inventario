"""Actualiza estructura de sucursales y relaciones asociadas."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.engine.reflection import Inspector

from backend.app.db.valor_inventario_view import (
    create_valor_inventario_view,
    drop_valor_inventario_view,
)
from backend.app.db.movimientos_inventario_view import (
    create_movimientos_inventario_view,
    drop_movimientos_inventario_view,
)

# revision identifiers, used by Alembic.
revision = "202503010007"
down_revision = "202503010005"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def _drop_store_foreign_keys(inspector: Inspector) -> None:
    tables_with_store_fk = [
        "devices",
        "inventory_movements",
        "sync_sessions",
        "supplier_batches",
        "purchase_orders",
        "sales",
        "repair_orders",
        "cash_register_sessions",
        "pos_configs",
        "pos_draft_sales",
        "store_memberships",
        "recurring_orders",
        "transfer_orders",
    ]
    is_sqlite = inspector.bind.dialect.name == "sqlite"
    for table in tables_with_store_fk:
        if not inspector.has_table(table):
            continue
        constraints_to_drop = [
            fk_name
            for fk in inspector.get_foreign_keys(table)
            if fk.get("referred_table") == "stores"
            if (fk_name := fk.get("name"))
        ]
        if not constraints_to_drop:
            continue
        if is_sqlite:
            with op.batch_alter_table(
                table,
                reflect_kwargs={"resolve_fks": False},
            ) as batch_op:
                for constraint_name in constraints_to_drop:
                    batch_op.drop_constraint(
                        constraint_name, type_="foreignkey")
        else:
            for constraint_name in constraints_to_drop:
                op.drop_constraint(constraint_name, table, type_="foreignkey")


def _populate_branch_metadata(connection: Connection) -> None:
    sucursales = sa.table(
        "sucursales",
        sa.column("id_sucursal", sa.Integer),
        sa.column("estado", sa.String(length=30)),
        sa.column("codigo", sa.String(length=20)),
    )
    rows = connection.execute(sa.select(sucursales.c.id_sucursal)).fetchall()
    for (branch_id,) in rows:
        connection.execute(
            sa.update(sucursales)
            .where(sucursales.c.id_sucursal == branch_id)
            .values(
                estado="activa",
                codigo=f"SUC-{branch_id:03d}",
            )
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"
    drop_valor_inventario_view(bind)
    drop_movimientos_inventario_view(bind)
    tables_to_capture = [
        "devices",
        "inventory_movements",
        "sync_sessions",
        "supplier_batches",
        "purchase_orders",
        "sales",
        "ventas",
        "store_memberships",
        "recurring_orders",
    ]
    index_snapshot: dict[str, set[str]] = {}
    for table in tables_to_capture:
        if inspector.has_table(table):
            index_snapshot[table] = {
                index_name
                for index in inspector.get_indexes(table)
                if (index_name := index.get("name"))
            }
    _drop_store_foreign_keys(inspector)

    op.rename_table("stores", "sucursales")
    op.alter_column("sucursales", "id", new_column_name="id_sucursal")
    op.alter_column("sucursales", "name", new_column_name="nombre")
    op.alter_column("sucursales", "location", new_column_name="direccion")

    op.drop_index("ix_stores_id", table_name="sucursales")
    op.drop_index("ix_stores_name", table_name="sucursales")

    op.add_column("sucursales", sa.Column(
        "telefono", sa.String(length=30), nullable=True))
    op.add_column("sucursales", sa.Column(
        "responsable", sa.String(length=120), nullable=True))
    op.add_column("sucursales", sa.Column(
        "estado", sa.String(length=30), nullable=True))
    op.add_column("sucursales", sa.Column(
        "codigo", sa.String(length=20), nullable=True))
    op.add_column(
        "sucursales",
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    _populate_branch_metadata(bind)

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "sucursales",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "estado",
                existing_type=sa.String(length=30),
                nullable=False,
            )
            batch_op.alter_column(
                "codigo",
                existing_type=sa.String(length=20),
                nullable=False,
            )
    else:
        op.alter_column(
            "sucursales",
            "estado",
            nullable=False,
            existing_type=sa.String(length=30),
        )
        op.alter_column(
            "sucursales",
            "codigo",
            nullable=False,
            existing_type=sa.String(length=20),
        )

    op.create_index("ix_sucursales_nombre", "sucursales",
                    ["nombre"], unique=True)
    op.create_index("ix_sucursales_estado", "sucursales", ["estado"])
    op.create_index("ix_sucursales_codigo", "sucursales",
                    ["codigo"], unique=True)

    if inspector.has_table("devices"):
        with op.batch_alter_table(
            "devices",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if "ix_devices_store_id" in index_snapshot.get("devices", set()):
                batch_op.drop_index("ix_devices_store_id")
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_devices_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="CASCADE",
                )
        op.create_index("ix_devices_sucursal_id", "devices", ["sucursal_id"])

    if inspector.has_table("inventory_movements"):
        with op.batch_alter_table(
            "inventory_movements",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "tienda_destino_id",
                new_column_name="sucursal_destino_id",
                existing_type=sa.Integer(),
            )
            batch_op.alter_column(
                "tienda_origen_id",
                new_column_name="sucursal_origen_id",
                existing_type=sa.Integer(),
            )
            if "ix_inventory_movements_tienda_destino_id" in index_snapshot.get("inventory_movements", set()):
                batch_op.drop_index("ix_inventory_movements_tienda_destino_id")
            if "ix_inventory_movements_tienda_origen_id" in index_snapshot.get("inventory_movements", set()):
                batch_op.drop_index("ix_inventory_movements_tienda_origen_id")
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_inventory_movements_sucursal_destino_id",
                    "sucursales",
                    ["sucursal_destino_id"],
                    ["id_sucursal"],
                    ondelete="CASCADE",
                )
                batch_op.create_foreign_key(
                    "fk_inventory_movements_sucursal_origen_id",
                    "sucursales",
                    ["sucursal_origen_id"],
                    ["id_sucursal"],
                    ondelete="SET NULL",
                )
        op.create_index(
            "ix_inventory_movements_sucursal_destino_id",
            "inventory_movements",
            ["sucursal_destino_id"],
        )
        op.create_index(
            "ix_inventory_movements_sucursal_origen_id",
            "inventory_movements",
            ["sucursal_origen_id"],
        )

    if inspector.has_table("sync_sessions"):
        with op.batch_alter_table(
            "sync_sessions",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if "ix_sync_sessions_store_id" in index_snapshot.get("sync_sessions", set()):
                batch_op.drop_index("ix_sync_sessions_store_id")
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_sync_sessions_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="SET NULL",
                )
        op.create_index(
            "ix_sync_sessions_sucursal_id",
            "sync_sessions",
            ["sucursal_id"],
        )

    if inspector.has_table("supplier_batches"):
        with op.batch_alter_table(
            "supplier_batches",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if "ix_supplier_batches_store_id" in index_snapshot.get("supplier_batches", set()):
                batch_op.drop_index("ix_supplier_batches_store_id")
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_supplier_batches_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="SET NULL",
                )
        op.create_index(
            "ix_supplier_batches_sucursal_id",
            "supplier_batches",
            ["sucursal_id"],
        )

    if inspector.has_table("purchase_orders"):
        with op.batch_alter_table(
            "purchase_orders",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if "ix_purchase_orders_store_id" in index_snapshot.get("purchase_orders", set()):
                batch_op.drop_index("ix_purchase_orders_store_id")
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_purchase_orders_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="RESTRICT",
                )
        op.create_index(
            "ix_purchase_orders_sucursal_id",
            "purchase_orders",
            ["sucursal_id"],
        )

    if inspector.has_table("sales"):
        with op.batch_alter_table(
            "sales",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if "ix_sales_store_id" in index_snapshot.get("sales", set()):
                batch_op.drop_index("ix_sales_store_id")
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_sales_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="RESTRICT",
                )
        op.create_index("ix_sales_sucursal_id", "sales", ["sucursal_id"])

    if inspector.has_table("repair_orders"):
        with op.batch_alter_table(
            "repair_orders",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_repair_orders_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="RESTRICT",
                )

    if inspector.has_table("cash_register_sessions"):
        with op.batch_alter_table(
            "cash_register_sessions",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_cash_sessions_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="RESTRICT",
                )

    if inspector.has_table("pos_configs"):
        with op.batch_alter_table(
            "pos_configs",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_pos_configs_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="CASCADE",
                )

    if inspector.has_table("pos_draft_sales"):
        with op.batch_alter_table(
            "pos_draft_sales",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_pos_draft_sales_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="CASCADE",
                )

    if inspector.has_table("store_memberships"):
        with op.batch_alter_table(
            "store_memberships",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if "ix_store_memberships_store_id" in index_snapshot.get("store_memberships", set()):
                batch_op.drop_index("ix_store_memberships_store_id")
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_store_memberships_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="CASCADE",
                )
        op.create_index(
            "ix_store_memberships_sucursal_id",
            "store_memberships",
            ["sucursal_id"],
        )

    if inspector.has_table("recurring_orders"):
        with op.batch_alter_table(
            "recurring_orders",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.alter_column(
                "store_id",
                new_column_name="sucursal_id",
                existing_type=sa.Integer(),
            )
            if "ix_recurring_orders_store_id" in index_snapshot.get("recurring_orders", set()):
                batch_op.drop_index("ix_recurring_orders_store_id")
            if is_sqlite:
                batch_op.create_foreign_key(
                    "fk_recurring_orders_sucursal_id",
                    "sucursales",
                    ["sucursal_id"],
                    ["id_sucursal"],
                    ondelete="SET NULL",
                )
        op.create_index(
            "ix_recurring_orders_sucursal_id",
            "recurring_orders",
            ["sucursal_id"],
        )

    if inspector.has_table("transfer_orders") and is_sqlite:
        with op.batch_alter_table(
            "transfer_orders",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.create_foreign_key(
                "fk_transfer_orders_origin_sucursal_id",
                "sucursales",
                ["origin_store_id"],
                ["id_sucursal"],
                ondelete="RESTRICT",
            )
            batch_op.create_foreign_key(
                "fk_transfer_orders_destination_sucursal_id",
                "sucursales",
                ["destination_store_id"],
                ["id_sucursal"],
                ondelete="RESTRICT",
            )

    op.add_column(
        "users",
        sa.Column("sucursal_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_users_sucursal_id", "users",
                    ["sucursal_id"], unique=False)

    if is_sqlite:
        with op.batch_alter_table(
            "users",
            reflect_kwargs={"resolve_fks": False},
        ) as batch_op:
            batch_op.create_foreign_key(
                "fk_users_sucursal_id",
                "sucursales",
                ["sucursal_id"],
                ["id_sucursal"],
                ondelete="SET NULL",
            )

    if not is_sqlite:
        op.create_foreign_key(
            "fk_devices_sucursal_id",
            "devices",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "fk_inventory_movements_sucursal_destino_id",
            "inventory_movements",
            "sucursales",
            ["sucursal_destino_id"],
            ["id_sucursal"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "fk_inventory_movements_sucursal_origen_id",
            "inventory_movements",
            "sucursales",
            ["sucursal_origen_id"],
            ["id_sucursal"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_sync_sessions_sucursal_id",
            "sync_sessions",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_supplier_batches_sucursal_id",
            "supplier_batches",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_purchase_orders_sucursal_id",
            "purchase_orders",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_sales_sucursal_id",
            "sales",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_repair_orders_sucursal_id",
            "repair_orders",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_cash_sessions_sucursal_id",
            "cash_register_sessions",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_pos_configs_sucursal_id",
            "pos_configs",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "fk_pos_draft_sales_sucursal_id",
            "pos_draft_sales",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "fk_store_memberships_sucursal_id",
            "store_memberships",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "fk_recurring_orders_sucursal_id",
            "recurring_orders",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_transfer_orders_origin_sucursal_id",
            "transfer_orders",
            "sucursales",
            ["origin_store_id"],
            ["id_sucursal"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_transfer_orders_destination_sucursal_id",
            "transfer_orders",
            "sucursales",
            ["destination_store_id"],
            ["id_sucursal"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_users_sucursal_id",
            "users",
            "sucursales",
            ["sucursal_id"],
            ["id_sucursal"],
            ondelete="SET NULL",
        )

    create_valor_inventario_view(bind)
    create_movimientos_inventario_view(bind)


def downgrade() -> None:
    bind = op.get_bind()

    drop_movimientos_inventario_view(bind)
    drop_valor_inventario_view(bind)

    op.drop_constraint("fk_users_sucursal_id", "users", type_="foreignkey")
    op.drop_index("ix_users_sucursal_id", table_name="users")
    op.drop_column("users", "sucursal_id")

    op.drop_constraint("fk_transfer_orders_destination_sucursal_id",
                       "transfer_orders", type_="foreignkey")
    op.drop_constraint("fk_transfer_orders_origin_sucursal_id",
                       "transfer_orders", type_="foreignkey")
    op.drop_constraint("fk_recurring_orders_sucursal_id",
                       "recurring_orders", type_="foreignkey")
    op.drop_constraint("fk_store_memberships_sucursal_id",
                       "store_memberships", type_="foreignkey")
    op.drop_constraint("fk_pos_draft_sales_sucursal_id",
                       "pos_draft_sales", type_="foreignkey")
    op.drop_constraint("fk_pos_configs_sucursal_id",
                       "pos_configs", type_="foreignkey")
    op.drop_constraint("fk_cash_sessions_sucursal_id",
                       "cash_register_sessions", type_="foreignkey")
    op.drop_constraint("fk_repair_orders_sucursal_id",
                       "repair_orders", type_="foreignkey")
    op.drop_constraint("fk_sales_sucursal_id", "sales", type_="foreignkey")
    op.drop_constraint("fk_purchase_orders_sucursal_id",
                       "purchase_orders", type_="foreignkey")
    op.drop_constraint("fk_supplier_batches_sucursal_id",
                       "supplier_batches", type_="foreignkey")
    op.drop_constraint("fk_sync_sessions_sucursal_id",
                       "sync_sessions", type_="foreignkey")
    op.drop_constraint("fk_inventory_movements_sucursal_origen_id",
                       "inventory_movements", type_="foreignkey")
    op.drop_constraint("fk_inventory_movements_sucursal_destino_id",
                       "inventory_movements", type_="foreignkey")
    op.drop_constraint("fk_devices_sucursal_id", "devices", type_="foreignkey")

    with op.batch_alter_table("recurring_orders") as batch_op:
        batch_op.drop_index("ix_recurring_orders_sucursal_id")
        batch_op.alter_column("sucursal_id", new_column_name="store_id")
        batch_op.create_index("ix_recurring_orders_store_id", ["store_id"])

    with op.batch_alter_table("store_memberships") as batch_op:
        batch_op.drop_index("ix_store_memberships_sucursal_id")
        batch_op.alter_column("sucursal_id", new_column_name="store_id")
        batch_op.create_index("ix_store_memberships_store_id", ["store_id"])

    with op.batch_alter_table("pos_draft_sales") as batch_op:
        batch_op.alter_column("sucursal_id", new_column_name="store_id")

    with op.batch_alter_table("pos_configs") as batch_op:
        batch_op.alter_column("sucursal_id", new_column_name="store_id")

    with op.batch_alter_table("cash_register_sessions") as batch_op:
        batch_op.alter_column("sucursal_id", new_column_name="store_id")

    with op.batch_alter_table("repair_orders") as batch_op:
        batch_op.alter_column("sucursal_id", new_column_name="store_id")

    with op.batch_alter_table("sales") as batch_op:
        batch_op.drop_index("ix_sales_sucursal_id")
        batch_op.alter_column("sucursal_id", new_column_name="store_id")
        batch_op.create_index("ix_sales_store_id", ["store_id"])

    with op.batch_alter_table("purchase_orders") as batch_op:
        batch_op.drop_index("ix_purchase_orders_sucursal_id")
        batch_op.alter_column("sucursal_id", new_column_name="store_id")
        batch_op.create_index("ix_purchase_orders_store_id", ["store_id"])

    with op.batch_alter_table("supplier_batches") as batch_op:
        batch_op.drop_index("ix_supplier_batches_sucursal_id")
        batch_op.alter_column("sucursal_id", new_column_name="store_id")
        batch_op.create_index("ix_supplier_batches_store_id", ["store_id"])

    with op.batch_alter_table("sync_sessions") as batch_op:
        batch_op.drop_index("ix_sync_sessions_sucursal_id")
        batch_op.alter_column("sucursal_id", new_column_name="store_id")
        batch_op.create_index("ix_sync_sessions_store_id", ["store_id"])

    with op.batch_alter_table("inventory_movements") as batch_op:
        batch_op.drop_index("ix_inventory_movements_sucursal_destino_id")
        batch_op.drop_index("ix_inventory_movements_sucursal_origen_id")
        batch_op.alter_column("sucursal_destino_id",
                              new_column_name="tienda_destino_id")
        batch_op.alter_column("sucursal_origen_id",
                              new_column_name="tienda_origen_id")
        batch_op.create_index("ix_inventory_movements_tienda_destino_id", [
                              "tienda_destino_id"])
        batch_op.create_index("ix_inventory_movements_tienda_origen_id", [
                              "tienda_origen_id"])

    with op.batch_alter_table("devices") as batch_op:
        batch_op.drop_index("ix_devices_sucursal_id")
        batch_op.alter_column("sucursal_id", new_column_name="store_id")
        batch_op.create_index("ix_devices_store_id", ["store_id"])

    op.drop_index("ix_sucursales_codigo", table_name="sucursales")
    op.drop_index("ix_sucursales_estado", table_name="sucursales")
    op.drop_index("ix_sucursales_nombre", table_name="sucursales")

    op.drop_column("sucursales", "fecha_creacion")
    op.drop_column("sucursales", "codigo")
    op.drop_column("sucursales", "estado")
    op.drop_column("sucursales", "responsable")
    op.drop_column("sucursales", "telefono")

    op.alter_column("sucursales", "direccion", new_column_name="location")
    op.alter_column("sucursales", "nombre", new_column_name="name")
    op.alter_column("sucursales", "id_sucursal", new_column_name="id")

    op.rename_table("sucursales", "stores")

    op.create_index("ix_stores_id", "stores", ["id"], unique=False)
    op.create_index("ix_stores_name", "stores", ["name"], unique=True)

    op.create_foreign_key("fk_devices_store_id", "devices", "stores", [
                          "store_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key(
        "fk_inventory_movements_store_id",
        "inventory_movements",
        "stores",
        ["tienda_destino_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_inventory_movements_source_store_id",
        "inventory_movements",
        "stores",
        ["tienda_origen_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_sync_sessions_store_id",
        "sync_sessions",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_supplier_batches_store_id",
        "supplier_batches",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_purchase_orders_store_id",
        "purchase_orders",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_sales_store_id",
        "sales",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_repair_orders_store_id",
        "repair_orders",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_cash_sessions_store_id",
        "cash_register_sessions",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_pos_configs_store_id",
        "pos_configs",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_pos_draft_sales_store_id",
        "pos_draft_sales",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_store_memberships_store_id",
        "store_memberships",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_recurring_orders_store_id",
        "recurring_orders",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_transfer_orders_origin_store_id",
        "transfer_orders",
        "stores",
        ["origin_store_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_transfer_orders_destination_store_id",
        "transfer_orders",
        "stores",
        ["destination_store_id"],
        ["id"],
        ondelete="RESTRICT",
    )
