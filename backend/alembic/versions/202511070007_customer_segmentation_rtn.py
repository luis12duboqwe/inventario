"""Agrega columnas de segmentación y RTN para clientes."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202511070007_customer_segmentation_rtn"
down_revision = "202511070006_return_dispositions"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspector.get_columns(table)}


def _index_exists(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(index.get("name") == name for index in inspector.get_indexes(table))


def _unique_exists(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(uc.get("name") == name for uc in inspector.get_unique_constraints(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if not inspector.has_table("clientes"):
        return

    json_type = sa.JSON() if is_sqlite else postgresql.JSONB(astext_type=sa.Text())
    tags_default = sa.text("'[]'") if is_sqlite else sa.text("'[]'::jsonb")

    if not _has_column(inspector, "clientes", "segmento_categoria"):
        op.add_column(
            "clientes",
            sa.Column("segmento_categoria", sa.String(length=60), nullable=True),
        )
        inspector = sa.inspect(bind)

    if not _index_exists(inspector, "clientes", "ix_clientes_segmento_categoria"):
        op.create_index(
            "ix_clientes_segmento_categoria",
            "clientes",
            ["segmento_categoria"],
            unique=False,
        )
        inspector = sa.inspect(bind)

    if not _has_column(inspector, "clientes", "segmento_etiquetas"):
        op.add_column(
            "clientes",
            sa.Column(
                "segmento_etiquetas",
                json_type,
                nullable=False,
                server_default=tags_default,
            ),
        )
        if is_sqlite:
            op.execute(sa.text("UPDATE clientes SET segmento_etiquetas = '[]'"))
        else:
            op.execute(sa.text("UPDATE clientes SET segmento_etiquetas = '[]'::jsonb"))
        if not is_sqlite:
            op.alter_column(
                "clientes",
                "segmento_etiquetas",
                existing_type=json_type,
                server_default=None,
            )
        inspector = sa.inspect(bind)

    if not _has_column(inspector, "clientes", "rtn"):
        op.add_column(
            "clientes",
            sa.Column("rtn", sa.String(length=30), nullable=True),
        )
        op.execute(
            sa.text(
                "UPDATE clientes SET rtn = 'RTN-' || CAST(id_cliente AS TEXT) "
                "WHERE rtn IS NULL OR TRIM(rtn) = ''"
            )
        )
        op.alter_column(
            "clientes",
            "rtn",
            existing_type=sa.String(length=30),
            nullable=False,
        )
        inspector = sa.inspect(bind)

    if not _index_exists(inspector, "clientes", "ix_clientes_rtn"):
        op.create_index("ix_clientes_rtn", "clientes", ["rtn"], unique=False)
        inspector = sa.inspect(bind)

    if not _unique_exists(inspector, "clientes", "uq_clientes_rtn"):
        if is_sqlite:
            op.create_index("uq_clientes_rtn", "clientes", ["rtn"], unique=True)
        else:
            op.create_unique_constraint("uq_clientes_rtn", "clientes", ["rtn"])
        inspector = sa.inspect(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    is_sqlite = bind.dialect.name == "sqlite"

    if not inspector.has_table("clientes"):
        return

    if _unique_exists(inspector, "clientes", "uq_clientes_rtn"):
        if is_sqlite:
            op.drop_index("uq_clientes_rtn", table_name="clientes")
        else:
            op.drop_constraint("uq_clientes_rtn", "clientes", type_="unique")
        inspector = sa.inspect(bind)

    if _index_exists(inspector, "clientes", "ix_clientes_rtn"):
        op.drop_index("ix_clientes_rtn", table_name="clientes")
        inspector = sa.inspect(bind)

    if _has_column(inspector, "clientes", "rtn"):
        op.drop_column("clientes", "rtn")
        inspector = sa.inspect(bind)

    if _index_exists(inspector, "clientes", "ix_clientes_segmento_categoria"):
        op.drop_index("ix_clientes_segmento_categoria", table_name="clientes")
        inspector = sa.inspect(bind)

    if _has_column(inspector, "clientes", "segmento_categoria"):
        op.drop_column("clientes", "segmento_categoria")
        inspector = sa.inspect(bind)

    if _has_column(inspector, "clientes", "segmento_etiquetas"):
        op.drop_column("clientes", "segmento_etiquetas")
