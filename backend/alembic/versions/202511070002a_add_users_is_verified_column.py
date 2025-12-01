"""Añade la columna is_verified a users garantizando idempotencia."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "202511070002a"
down_revision = "202511070001"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = {name.lower(): name for name in inspector.get_table_names()}
    target_table = tables.get("users")

    if target_table is None:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("username", sa.String(length=255), nullable=False, unique=True),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            sa.Column(
                "is_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=False),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sqlite_autoincrement=True,
        )
        op.create_index("ix_users_id", "users", ["id"], unique=False)
        op.create_index("ix_users_username", "users", ["username"], unique=True)
        op.create_index("ix_users_email", "users", ["email"], unique=True)
    else:
        column_names = {column["name"] for column in inspector.get_columns(target_table)}

        if "is_verified" not in column_names:
            with op.batch_alter_table(target_table, schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "is_verified",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("0"),
                    )
                )

            op.execute(
                sa.text(
                    f"UPDATE {target_table} SET is_verified = 0 WHERE is_verified IS NULL"
                )
            )

            with op.batch_alter_table(target_table, schema=None) as batch_op:
                batch_op.alter_column(
                    "is_verified",
                    server_default=None,
                    existing_type=sa.Boolean(),
                )

    usuarios_table = tables.get("usuarios")
    if usuarios_table is not None:
        usuarios_columns = {
            column["name"] for column in inspector.get_columns(usuarios_table)
        }

        if "failed_login_attempts" not in usuarios_columns:
            with op.batch_alter_table(usuarios_table, schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "failed_login_attempts",
                        sa.Integer(),
                        nullable=False,
                        server_default=sa.text("0"),
                    )
                )

            op.execute(
                sa.text(
                    f"UPDATE {usuarios_table} SET failed_login_attempts = 0 "
                    "WHERE failed_login_attempts IS NULL"
                )
            )

            with op.batch_alter_table(usuarios_table, schema=None) as batch_op:
                batch_op.alter_column(
                    "failed_login_attempts",
                    server_default=None,
                    existing_type=sa.Integer(),
                )

        if "last_login_attempt_at" not in usuarios_columns:
            with op.batch_alter_table(usuarios_table, schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "last_login_attempt_at",
                        sa.DateTime(timezone=True),
                        nullable=True,
                    )
                )

        if "locked_until" not in usuarios_columns:
            with op.batch_alter_table(usuarios_table, schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "locked_until",
                        sa.DateTime(timezone=True),
                        nullable=True,
                    )
                )

    active_sessions_table = tables.get("active_sessions")
    if active_sessions_table is not None:
        active_sessions_columns = {
            column["name"]
            for column in inspector.get_columns(active_sessions_table)
        }

        if "expires_at" not in active_sessions_columns:
            with op.batch_alter_table(active_sessions_table, schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "expires_at",
                        sa.DateTime(timezone=True),
                        nullable=True,
                    )
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = {name.lower(): name for name in inspector.get_table_names()}
    target_table = tables.get("users")

    if target_table is None:
        return

    column_names = {column["name"] for column in inspector.get_columns(target_table)}

    if "is_verified" in column_names:
        with op.batch_alter_table(target_table, schema=None) as batch_op:
            batch_op.drop_column("is_verified")

    usuarios_table = tables.get("usuarios")
    if usuarios_table is None:
        return

    usuarios_columns = {
        column["name"] for column in inspector.get_columns(usuarios_table)
    }

    if "locked_until" in usuarios_columns:
        with op.batch_alter_table(usuarios_table, schema=None) as batch_op:
            batch_op.drop_column("locked_until")

    if "last_login_attempt_at" in usuarios_columns:
        with op.batch_alter_table(usuarios_table, schema=None) as batch_op:
            batch_op.drop_column("last_login_attempt_at")

    if "failed_login_attempts" in usuarios_columns:
        with op.batch_alter_table(usuarios_table, schema=None) as batch_op:
            batch_op.drop_column("failed_login_attempts")

    active_sessions_table = tables.get("active_sessions")
    if active_sessions_table is None:
        return

    active_sessions_columns = {
        column["name"] for column in inspector.get_columns(active_sessions_table)
    }

    if "expires_at" in active_sessions_columns:
        with op.batch_alter_table(active_sessions_table, schema=None) as batch_op:
            batch_op.drop_column("expires_at")
