"""Crea tabla de permisos base para roles de usuarios."""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202503010011"
down_revision = "202503010008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "permisos",
        sa.Column("id_permiso", sa.Integer(), primary_key=True),
        sa.Column("rol", sa.String(length=50), nullable=False),
        sa.Column("modulo", sa.String(length=120), nullable=False),
        sa.Column(
            "puede_ver",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "puede_editar",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "puede_borrar",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.ForeignKeyConstraint(["rol"], ["roles.name"], ondelete="CASCADE"),
        sa.UniqueConstraint("rol", "modulo", name="uq_permisos_rol_modulo"),
    )
    op.create_index("ix_permisos_rol", "permisos", ["rol"], unique=False)
    op.create_index("ix_permisos_modulo", "permisos", ["modulo"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_permisos_modulo", table_name="permisos")
    op.drop_index("ix_permisos_rol", table_name="permisos")
    op.drop_table("permisos")
