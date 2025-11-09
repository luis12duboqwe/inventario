"""Agregar columna promotions_config a POS"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202511070006"
down_revision = "202511070005"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    default = sa.text("'{}'") if is_sqlite else sa.text("'{}'::jsonb")

    op.add_column(
        "pos_configs",
        sa.Column(
            "promotions_config",
            json_type,
            nullable=False,
            server_default=default,
        ),
    )

    if not is_sqlite:
        op.alter_column("pos_configs", "promotions_config", server_default=None)


def downgrade() -> None:
    op.drop_column("pos_configs", "promotions_config")
