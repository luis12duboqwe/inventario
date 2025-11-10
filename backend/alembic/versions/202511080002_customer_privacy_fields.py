"""Customer privacy fields and requests"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "202511080002"
down_revision = "202511080001"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


PRIVACY_REQUEST_TYPE = sa.Enum(
    "consent",
    "anonymization",
    name="privacy_request_type",
)

PRIVACY_REQUEST_STATUS = sa.Enum(
    "registrada",
    "procesada",
    name="privacy_request_status",
)


def _json_type(bind: sa.engine.Connection) -> sa.types.TypeEngine:
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def _json_default(bind: sa.engine.Connection, *, as_array: bool) -> sa.sql.elements.TextClause:
    if bind.dialect.name == "sqlite":
        return sa.text("'[]'") if as_array else sa.text("'{}'")
    return sa.text("'[]'::jsonb") if as_array else sa.text("'{}'::jsonb")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    json_type = _json_type(bind)
    json_array_default = _json_default(bind, as_array=True)
    json_object_default = _json_default(bind, as_array=False)

    if inspector.has_table("clientes"):
        columns = {column["name"] for column in inspector.get_columns("clientes")}

        if "history" not in columns:
            op.add_column(
                "clientes",
                sa.Column(
                    "history",
                    json_type,
                    nullable=False,
                    server_default=json_array_default,
                ),
            )
        if "privacy_consents" not in columns:
            op.add_column(
                "clientes",
                sa.Column(
                    "privacy_consents",
                    json_type,
                    nullable=False,
                    server_default=json_object_default,
                ),
            )
        if "privacy_metadata" not in columns:
            op.add_column(
                "clientes",
                sa.Column(
                    "privacy_metadata",
                    json_type,
                    nullable=False,
                    server_default=json_object_default,
                ),
            )
        if "privacy_last_request_at" not in columns:
            op.add_column(
                "clientes",
                sa.Column(
                    "privacy_last_request_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                ),
            )

    if not inspector.has_table("customer_privacy_requests"):
        PRIVACY_REQUEST_TYPE.create(bind, checkfirst=True)
        PRIVACY_REQUEST_STATUS.create(bind, checkfirst=True)

        op.create_table(
            "customer_privacy_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("customer_id", sa.Integer(), nullable=False),
            sa.Column("request_type", PRIVACY_REQUEST_TYPE, nullable=False),
            sa.Column(
                "status",
                PRIVACY_REQUEST_STATUS,
                nullable=False,
                server_default=sa.text("'procesada'"),
            ),
            sa.Column("details", sa.String(length=255), nullable=True),
            sa.Column(
                "consent_snapshot",
                json_type,
                nullable=False,
                server_default=json_object_default,
            ),
            sa.Column(
                "masked_fields",
                json_type,
                nullable=False,
                server_default=json_array_default,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text(
                    "CURRENT_TIMESTAMP"
                    if bind.dialect.name == "sqlite"
                    else "timezone('utc', now())"
                ),
            ),
            sa.Column(
                "processed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column("processed_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["customer_id"],
                ["clientes.id_cliente"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["processed_by_id"],
                ["usuarios.id_usuario"],
                ondelete="SET NULL",
            ),
        )
        op.create_index(
            op.f("ix_customer_privacy_requests_customer_id"),
            "customer_privacy_requests",
            ["customer_id"],
        )
        op.create_index(
            op.f("ix_customer_privacy_requests_processed_by_id"),
            "customer_privacy_requests",
            ["processed_by_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(
        op.f("ix_customer_privacy_requests_processed_by_id"),
        table_name="customer_privacy_requests",
    )
    op.drop_index(
        op.f("ix_customer_privacy_requests_customer_id"),
        table_name="customer_privacy_requests",
    )
    op.drop_table("customer_privacy_requests")

    PRIVACY_REQUEST_STATUS.drop(bind, checkfirst=True)
    PRIVACY_REQUEST_TYPE.drop(bind, checkfirst=True)

    op.drop_column("clientes", "privacy_last_request_at")
    op.drop_column("clientes", "privacy_metadata")
    op.drop_column("clientes", "privacy_consents")
    op.drop_column("clientes", "history")
