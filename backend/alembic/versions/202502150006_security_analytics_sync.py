"""add security, analytics and sync outbox tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202502150006"
down_revision = "202502150005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_totp_secrets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("secret", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_totp_secrets_id"), "user_totp_secrets", ["id"], unique=False)
    op.create_index(op.f("ix_user_totp_secrets_user_id"), "user_totp_secrets", ["user_id"], unique=True)

    op.create_table(
        "active_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_id", sa.Integer(), nullable=True),
        sa.Column("revoke_reason", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["revoked_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_token", name="uq_active_session_token"),
    )
    op.create_index(op.f("ix_active_sessions_id"), "active_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_active_sessions_session_token"), "active_sessions", ["session_token"], unique=True)
    op.create_index(op.f("ix_active_sessions_user_id"), "active_sessions", ["user_id"], unique=False)

    op.create_table(
        "sync_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "SENT", "FAILED", name="sync_outbox_status"), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", name="uq_outbox_entity"),
    )
    op.create_index(op.f("ix_sync_outbox_entity_type"), "sync_outbox", ["entity_type"], unique=False)
    op.create_index(op.f("ix_sync_outbox_id"), "sync_outbox", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sync_outbox_id"), table_name="sync_outbox")
    op.drop_index(op.f("ix_sync_outbox_entity_type"), table_name="sync_outbox")
    op.drop_table("sync_outbox")
    op.execute("DROP TYPE sync_outbox_status")

    op.drop_index(op.f("ix_active_sessions_user_id"), table_name="active_sessions")
    op.drop_index(op.f("ix_active_sessions_session_token"), table_name="active_sessions")
    op.drop_index(op.f("ix_active_sessions_id"), table_name="active_sessions")
    op.drop_table("active_sessions")

    op.drop_index(op.f("ix_user_totp_secrets_user_id"), table_name="user_totp_secrets")
    op.drop_index(op.f("ix_user_totp_secrets_id"), table_name="user_totp_secrets")
    op.drop_table("user_totp_secrets")
