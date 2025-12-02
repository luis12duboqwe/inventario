"""Agrega columna updated_at a inventory_movements si falta.

Corrige errores en consultas de snapshot que ordenan/seleccionan updated_at.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import NoSuchTableError


revision = "202511270002"
down_revision = "202511270001"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        cols = [c["name"] for c in insp.get_columns(table)]
    except NoSuchTableError:
        return False
    return column in cols


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table in insp.get_table_names()


def upgrade() -> None:
    if _has_table("inventory_movements") and not _has_column("inventory_movements", "updated_at"):
        op.add_column(
            "inventory_movements",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if _has_column("inventory_movements", "updated_at"):
        op.drop_column("inventory_movements", "updated_at")
