"""Crear tabla de validaciones de importación."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202503010013"
down_revision = "202503010012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "validaciones_importacion",
        sa.Column("id_validacion", sa.Integer(), primary_key=True),
        sa.Column("producto_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(length=80), nullable=False),
        sa.Column("severidad", sa.String(length=20), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "corregido",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.ForeignKeyConstraint(["producto_id"], ["devices.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_validaciones_importacion_producto_id",
        "validaciones_importacion",
        ["producto_id"],
        unique=False,
    )
    op.create_index(
        "ix_validaciones_importacion_tipo",
        "validaciones_importacion",
        ["tipo"],
        unique=False,
    )
    op.create_index(
        "ix_validaciones_importacion_severidad",
        "validaciones_importacion",
        ["severidad"],
        unique=False,
    )
    op.create_index(
        "ix_validaciones_importacion_fecha",
        "validaciones_importacion",
        ["fecha"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_validaciones_importacion_fecha",
        table_name="validaciones_importacion",
    )
    op.drop_index(
        "ix_validaciones_importacion_severidad",
        table_name="validaciones_importacion",
    )
    op.drop_index(
        "ix_validaciones_importacion_tipo",
        table_name="validaciones_importacion",
    )
    op.drop_index(
        "ix_validaciones_importacion_producto_id",
        table_name="validaciones_importacion",
    )
    op.drop_table("validaciones_importacion")
