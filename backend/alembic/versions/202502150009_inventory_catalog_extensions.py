"""Ampliar catálogo de dispositivos con campos descriptivos."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202502150009_inventory_catalog_extensions"
down_revision = "202502150008_operations_recurring_and_history"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("categoria", sa.String(length=80), nullable=True))
    op.add_column("devices", sa.Column("condicion", sa.String(length=60), nullable=True))
    op.add_column("devices", sa.Column("capacidad", sa.String(length=80), nullable=True))
    op.add_column(
        "devices",
        sa.Column("estado", sa.String(length=40), nullable=False, server_default="disponible"),
    )
    op.add_column("devices", sa.Column("fecha_ingreso", sa.Date(), nullable=True))
    op.add_column("devices", sa.Column("ubicacion", sa.String(length=120), nullable=True))
    op.add_column("devices", sa.Column("descripcion", sa.Text(), nullable=True))
    op.add_column("devices", sa.Column("imagen_url", sa.String(length=255), nullable=True))

    op.execute("UPDATE devices SET estado = 'disponible' WHERE estado IS NULL")
    op.alter_column("devices", "estado", server_default=None)


def downgrade() -> None:
    op.drop_column("devices", "imagen_url")
    op.drop_column("devices", "descripcion")
    op.drop_column("devices", "ubicacion")
    op.drop_column("devices", "fecha_ingreso")
    op.drop_column("devices", "estado")
    op.drop_column("devices", "capacidad")
    op.drop_column("devices", "condicion")
    op.drop_column("devices", "categoria")
