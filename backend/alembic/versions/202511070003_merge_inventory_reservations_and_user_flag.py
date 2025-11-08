"""Unifica cabeceras paralelas de reservaciones e indicador de usuario verificado."""
from __future__ import annotations

from alembic import op  # noqa: F401  - mantenido para coherencia de plantillas


revision = "202511070003"
down_revision = ("202511070002", "202511070002a")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Revision de fusión sin operaciones adicionales."""
    # Esta revisión actúa únicamente como punto de convergencia entre ramas.
    pass


def downgrade() -> None:  # pragma: no cover - fusión no reversible automáticamente
    raise NotImplementedError("La revisión de fusión 202511070003 no admite downgrade automático.")
