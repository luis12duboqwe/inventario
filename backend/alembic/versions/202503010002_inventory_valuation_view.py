"""Crea vista valor_inventario con costos y márgenes agregados."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from backend.app.db.valor_inventario_view import (
    CREATE_VALOR_INVENTARIO_VIEW_SQL,
    DROP_VALOR_INVENTARIO_VIEW_SQL,
)

# revision identifiers, used by Alembic.
revision = "202503010002"
down_revision = "202503010001"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute(sa.text(DROP_VALOR_INVENTARIO_VIEW_SQL))
    op.execute(sa.text(CREATE_VALOR_INVENTARIO_VIEW_SQL))


def downgrade() -> None:
    op.execute(sa.text(DROP_VALOR_INVENTARIO_VIEW_SQL))
