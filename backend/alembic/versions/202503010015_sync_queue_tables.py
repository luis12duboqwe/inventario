"""Cola híbrida de sincronización para Pack 35."""
# // [PACK35-backend]

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "202503010015"
down_revision: str | None = "202503010014"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


SYNC_QUEUE_STATUS = sa.Enum("PENDING", "SENT", "FAILED", name="sync_queue_status")


def upgrade() -> None:
    bind = op.get_bind()
    SYNC_QUEUE_STATUS.create(bind, checkfirst=True)

    op.create_table(
        "sync_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True, unique=True),
        sa.Column(
            "status",
            SYNC_QUEUE_STATUS,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_sync_queue_event_type", "sync_queue", ["event_type"], unique=False)
    op.create_index("ix_sync_queue_status", "sync_queue", ["status"], unique=False)

    op.create_table(
        "sync_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("queue_id", sa.Integer(), nullable=False),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["queue_id"], ["sync_queue.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sync_attempts_queue_id", "sync_attempts", ["queue_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sync_attempts_queue_id", table_name="sync_attempts")
    op.drop_table("sync_attempts")

    op.drop_index("ix_sync_queue_status", table_name="sync_queue")
    op.drop_index("ix_sync_queue_event_type", table_name="sync_queue")
    op.drop_constraint("sync_queue_idempotency_key_key", "sync_queue", type_="unique")
    op.drop_table("sync_queue")

    bind = op.get_bind()
    SYNC_QUEUE_STATUS.drop(bind, checkfirst=True)
