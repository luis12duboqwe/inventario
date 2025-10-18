"""Ajustar longitud de correo en usuarios"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202503010009"
down_revision = "202503010008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "usuarios",
        "correo",
        existing_type=sa.String(length=80),
        type_=sa.String(length=120),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "usuarios",
        "correo",
        existing_type=sa.String(length=120),
        type_=sa.String(length=80),
        existing_nullable=False,
    )
