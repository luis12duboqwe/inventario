"""Add smart inventory import structures"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202502150011_inventory_smart_import"
down_revision = "202502150010_inventory_movements_enhancements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column(
            "completo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_table(
        "importaciones_temp",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre_archivo", sa.String(length=255), nullable=False),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column("columnas_detectadas", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("registros_incompletos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_registros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nuevos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actualizados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("advertencias", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="'[]'::jsonb"),
        sa.Column("patrones_columnas", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="'{}'::jsonb"),
        sa.Column("duracion_segundos", sa.Numeric(10, 2), nullable=True),
    )
    op.create_index(
        "ix_importaciones_temp_fecha",
        "importaciones_temp",
        ["fecha"],
        unique=False,
    )

    op.execute("UPDATE devices SET completo = TRUE")
    op.alter_column("devices", "completo", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_importaciones_temp_fecha", table_name="importaciones_temp")
    op.drop_table("importaciones_temp")
    op.drop_column("devices", "completo")
