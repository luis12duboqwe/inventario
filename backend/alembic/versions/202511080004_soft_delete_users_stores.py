"""
Añade columnas de borrado lógico para usuarios y sucursales.

Revision ID: 202511080004
Revises: 202511080003
Create Date: 2025-11-08 02:30:00 UTC

Nota: Compatible con v2.2.0 sin alterar etiquetas de versión del producto.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202511080004"
down_revision = "202511080003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sucursales",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "sucursales",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_sucursales_is_deleted", "sucursales", ["is_deleted"], unique=False
    )

    op.add_column(
        "usuarios",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "usuarios",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_usuarios_is_deleted", "usuarios", ["is_deleted"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_usuarios_is_deleted", table_name="usuarios")
    op.drop_column("usuarios", "deleted_at")
    op.drop_column("usuarios", "is_deleted")

    op.drop_index("ix_sucursales_is_deleted", table_name="sucursales")
    op.drop_column("sucursales", "deleted_at")
    op.drop_column("sucursales", "is_deleted")
