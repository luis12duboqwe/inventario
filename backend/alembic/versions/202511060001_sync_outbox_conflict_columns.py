"""Agregar columnas conflict_flag y version a sync_outbox.

Revision ID: 202511060001
Revises: 202503010015
Create Date: 2025-11-06 22:10:00 UTC

Nota: Mantener compatibilidad v2.2.0 sin alterar etiquetas de versión del producto.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202511060001"
down_revision = "202503010015_pack37_repairs_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sync_outbox") as batch:
        batch.add_column(sa.Column("conflict_flag", sa.Boolean(),
                         nullable=False, server_default=sa.text("0")))
        batch.add_column(sa.Column("version", sa.Integer(),
                         nullable=False, server_default="1"))
        batch.create_index("ix_sync_outbox_conflict_flag", ["conflict_flag"])
        batch.create_index("ix_sync_outbox_version", ["version"])


def downgrade() -> None:
    with op.batch_alter_table("sync_outbox") as batch:
        batch.drop_index("ix_sync_outbox_version")
        batch.drop_index("ix_sync_outbox_conflict_flag")
        batch.drop_column("version")
        batch.drop_column("conflict_flag")
