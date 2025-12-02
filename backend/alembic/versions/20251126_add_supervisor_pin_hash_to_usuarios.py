"""Agregar columna supervisor_pin_hash a usuarios si no existe.

Revision ID: 20251126_add_supervisor_pin_hash
Revises: 202511070003_merge_inventory_reservations_and_user_verification_heads
Create Date: 2025-11-26
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251126_add_supervisor_pin_hash"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = {t.lower(): t for t in inspector.get_table_names()}
    usuarios_table = tables.get("usuarios")
    if usuarios_table is None:
        return
    columns = {c["name"] for c in inspector.get_columns(usuarios_table)}
    if "supervisor_pin_hash" not in columns:
        with op.batch_alter_table(usuarios_table, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("supervisor_pin_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = {t.lower(): t for t in inspector.get_table_names()}
    usuarios_table = tables.get("usuarios")
    if usuarios_table is None:
        return
    columns = {c["name"] for c in inspector.get_columns(usuarios_table)}
    if "supervisor_pin_hash" in columns:
        with op.batch_alter_table(usuarios_table, schema=None) as batch_op:
            batch_op.drop_column("supervisor_pin_hash")
