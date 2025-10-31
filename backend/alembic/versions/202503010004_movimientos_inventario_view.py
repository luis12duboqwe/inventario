"""Crea vista movimientos_inventario para compatibilidad heredada."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from backend.app.db.movimientos_inventario_view import (
    CREATE_MOVIMIENTOS_INVENTARIO_VIEW_SQL,
    DROP_MOVIMIENTOS_INVENTARIO_VIEW_SQL,
)

# revision identifiers, used by Alembic.
revision = "202503010004"
down_revision = "202503010003"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute(sa.text(DROP_MOVIMIENTOS_INVENTARIO_VIEW_SQL))
    op.execute(sa.text(CREATE_MOVIMIENTOS_INVENTARIO_VIEW_SQL))


def downgrade() -> None:
    op.execute(sa.text(DROP_MOVIMIENTOS_INVENTARIO_VIEW_SQL))
