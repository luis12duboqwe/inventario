"""Unifica cabeceras tras agregar listas de precios.

Revision ID: 202511070004a
Revises: 202511070004, 202511070003
Create Date: 2025-11-07 13:35:00 UTC

Nota: Compatible con v2.2.0 sin alterar etiquetas de versión del producto.
"""
from __future__ import annotations

from alembic import op  # noqa: F401  - mantenido para coherencia de plantillas


revision = "202511070004a"
down_revision = ("202511070004", "202511070003")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Revision de fusión sin operaciones adicionales."""
    # Esta revisión actúa únicamente como punto de convergencia entre ramas.
    pass
def downgrade() -> None:  # pragma: no cover - fusión no reversible automáticamente
    raise NotImplementedError(
        "La revisión de fusión 202511070004a no admite downgrade automático."
    )
