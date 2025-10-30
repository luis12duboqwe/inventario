"""Tabla audit_ui para bitácora de interacciones."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202503010013"
down_revision = "202503010012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # // [PACK32-33-BE] Tabla para persistir la bitácora de UI.
    op.create_table(
        "audit_ui",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=True),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index("ix_audit_ui_ts", "audit_ui", ["ts"], unique=False)
    op.create_index("ix_audit_ui_user_id", "audit_ui", ["user_id"], unique=False)
    op.create_index("ix_audit_ui_module", "audit_ui", ["module"], unique=False)
    op.create_index("ix_audit_ui_action", "audit_ui", ["action"], unique=False)
    op.create_index("ix_audit_ui_entity_id", "audit_ui", ["entity_id"], unique=False)


def downgrade() -> None:
    # // [PACK32-33-BE] Reversa de la tabla audit_ui.
    op.drop_index("ix_audit_ui_entity_id", table_name="audit_ui")
    op.drop_index("ix_audit_ui_action", table_name="audit_ui")
    op.drop_index("ix_audit_ui_module", table_name="audit_ui")
    op.drop_index("ix_audit_ui_user_id", table_name="audit_ui")
    op.drop_index("ix_audit_ui_ts", table_name="audit_ui")
    op.drop_table("audit_ui")
