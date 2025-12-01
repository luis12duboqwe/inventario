"""Unifica los heads de reservas de inventario y verificación de usuarios."""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "202511070003"
down_revision = ("202511070002", "202511070002a")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Migración de fusión sin operaciones adicionales."""
    pass


def downgrade() -> None:
    """No se admite reversión para migraciones de fusión."""
    pass
