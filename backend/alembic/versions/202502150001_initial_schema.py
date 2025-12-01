"""Esquema inicial de Softmobile Central.

Revision ID: 202502150001
Revises:
Create Date: 2025-02-15 00:01:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202502150001"
down_revision = None
branch_labels = None
depends_on = None


movement_type_enum = sa.Enum(
    "entrada", "salida", "ajuste", name="movement_type")
sync_mode_enum = sa.Enum("automatico", "manual", name="sync_mode")
sync_status_enum = sa.Enum("exitoso", "fallido", name="sync_status")
backup_mode_enum = sa.Enum("automatico", "manual", name="backup_mode")


def upgrade() -> None:
    movement_type_enum.create(op.get_bind(), checkfirst=True)
    sync_mode_enum.create(op.get_bind(), checkfirst=True)
    sync_status_enum.create(op.get_bind(), checkfirst=True)
    backup_mode_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("timezone", sa.String(length=50),
                  nullable=False, server_default="UTC"),
    )
    op.create_index("ix_stores_id", "stores", ["id"], unique=False)
    op.create_index("ix_stores_name", "stores", ["name"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )
    op.create_index("ix_roles_id", "roles", ["id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                  server_default=sa.sql.expression.true()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "store_id",
            sa.Integer(),
            sa.ForeignKey(
                "stores.id",
                ondelete="CASCADE",
                name="fk_devices_store_id",
            ),
            nullable=False,
        ),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("quantity", sa.Integer(),
                  nullable=False, server_default="0"),
        sa.UniqueConstraint("store_id", "sku", name="uq_devices_store_sku"),
    )
    op.create_index("ix_devices_id", "devices", ["id"], unique=False)
    op.create_index("ix_devices_store_id", "devices",
                    ["store_id"], unique=False)

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
                name="fk_user_roles_user_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey(
                "roles.id",
                ondelete="CASCADE",
                name="fk_user_roles_role_id",
            ),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles",
                    ["user_id"], unique=False)
    op.create_index("ix_user_roles_role_id", "user_roles",
                    ["role_id"], unique=False)

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "store_id",
            sa.Integer(),
            sa.ForeignKey(
                "stores.id",
                ondelete="CASCADE",
                name="fk_inventory_movements_store_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Integer(),
            sa.ForeignKey(
                "devices.id",
                ondelete="CASCADE",
                name="fk_inventory_movements_device_id",
            ),
            nullable=False,
        ),
        sa.Column("movement_type", movement_type_enum, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "performed_by_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="SET NULL",
                name="fk_inventory_movements_performed_by",
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_inventory_movements_id",
                    "inventory_movements", ["id"], unique=False)
    op.create_index("ix_inventory_movements_store_id",
                    "inventory_movements", ["store_id"], unique=False)
    op.create_index("ix_inventory_movements_device_id",
                    "inventory_movements", ["device_id"], unique=False)
    op.create_index(
        "ix_inventory_movements_performed_by_id",
        "inventory_movements",
        ["performed_by_id"],
        unique=False,
    )

    op.create_table(
        "sync_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "store_id",
            sa.Integer(),
            sa.ForeignKey(
                "stores.id",
                ondelete="SET NULL",
                name="fk_sync_sessions_store_id",
            ),
            nullable=True,
        ),
        sa.Column("mode", sync_mode_enum, nullable=False),
        sa.Column("status", sync_status_enum, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "triggered_by_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="SET NULL",
                name="fk_sync_sessions_triggered_by",
            ),
            nullable=True,
        ),
    )
    op.create_index("ix_sync_sessions_id",
                    "sync_sessions", ["id"], unique=False)
    op.create_index("ix_sync_sessions_store_id",
                    "sync_sessions", ["store_id"], unique=False)
    op.create_index("ix_sync_sessions_triggered_by_id",
                    "sync_sessions", ["triggered_by_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "performed_by_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="SET NULL",
                name="fk_audit_logs_performed_by",
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"], unique=False)
    op.create_index("ix_audit_logs_performed_by_id", "audit_logs", [
                    "performed_by_id"], unique=False)

    op.create_table(
        "backup_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("mode", backup_mode_enum, nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("pdf_path", sa.String(length=255), nullable=False),
        sa.Column("archive_path", sa.String(length=255), nullable=False),
        sa.Column("total_size_bytes", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column(
            "triggered_by_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="SET NULL",
                name="fk_backup_jobs_triggered_by",
            ),
            nullable=True,
        ),
    )
    op.create_index("ix_backup_jobs_id", "backup_jobs", ["id"], unique=False)
    op.create_index("ix_backup_jobs_triggered_by_id",
                    "backup_jobs", ["triggered_by_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_backup_jobs_triggered_by_id", table_name="backup_jobs")
    op.drop_index("ix_backup_jobs_id", table_name="backup_jobs")
    op.drop_table("backup_jobs")

    op.drop_index("ix_audit_logs_performed_by_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_sync_sessions_triggered_by_id",
                  table_name="sync_sessions")
    op.drop_index("ix_sync_sessions_store_id", table_name="sync_sessions")
    op.drop_index("ix_sync_sessions_id", table_name="sync_sessions")
    op.drop_table("sync_sessions")

    op.drop_index("ix_inventory_movements_performed_by_id",
                  table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_device_id",
                  table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_store_id",
                  table_name="inventory_movements")
    op.drop_index("ix_inventory_movements_id",
                  table_name="inventory_movements")
    op.drop_table("inventory_movements")

    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("ix_devices_store_id", table_name="devices")
    op.drop_index("ix_devices_id", table_name="devices")
    op.drop_table("devices")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_roles_id", table_name="roles")
    op.drop_table("roles")

    op.drop_index("ix_stores_name", table_name="stores")
    op.drop_index("ix_stores_id", table_name="stores")
    op.drop_table("stores")

    backup_mode_enum.drop(op.get_bind(), checkfirst=True)
    sync_status_enum.drop(op.get_bind(), checkfirst=True)
    sync_mode_enum.drop(op.get_bind(), checkfirst=True)
    movement_type_enum.drop(op.get_bind(), checkfirst=True)
