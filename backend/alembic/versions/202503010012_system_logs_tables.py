"""Tablas de logs y errores del sistema."""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202503010012"
down_revision = "202503010011"
branch_labels = None
depends_on = None


SYSTEM_LOG_LEVEL = sa.Enum(
    "info", "warning", "error", "critical", name="system_log_level"
)


def upgrade() -> None:
    bind = op.get_bind()
    SYSTEM_LOG_LEVEL.create(bind, checkfirst=True)

    op.create_table(
        "logs_sistema",
        sa.Column("id_log", sa.Integer(), primary_key=True),
        sa.Column("usuario", sa.String(length=120), nullable=True),
        sa.Column("modulo", sa.String(length=80), nullable=False),
        sa.Column("accion", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("nivel", SYSTEM_LOG_LEVEL, nullable=False, server_default="info"),
        sa.Column("ip_origen", sa.String(length=45), nullable=True),
        sa.Column("audit_log_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["audit_log_id"], ["audit_logs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("audit_log_id", name="uq_logs_sistema_audit"),
    )
    op.create_index("ix_logs_sistema_usuario", "logs_sistema", ["usuario"], unique=False)
    op.create_index("ix_logs_sistema_modulo", "logs_sistema", ["modulo"], unique=False)
    op.create_index("ix_logs_sistema_fecha", "logs_sistema", ["fecha"], unique=False)
    op.create_index("ix_logs_sistema_nivel", "logs_sistema", ["nivel"], unique=False)

    op.create_table(
        "errores_sistema",
        sa.Column("id_error", sa.Integer(), primary_key=True),
        sa.Column("mensaje", sa.String(length=255), nullable=False),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("modulo", sa.String(length=80), nullable=False),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("usuario", sa.String(length=120), nullable=True),
    )
    op.create_index("ix_errores_sistema_modulo", "errores_sistema", ["modulo"], unique=False)
    op.create_index("ix_errores_sistema_fecha", "errores_sistema", ["fecha"], unique=False)
    op.create_index("ix_errores_sistema_usuario", "errores_sistema", ["usuario"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_errores_sistema_usuario", table_name="errores_sistema")
    op.drop_index("ix_errores_sistema_fecha", table_name="errores_sistema")
    op.drop_index("ix_errores_sistema_modulo", table_name="errores_sistema")
    op.drop_table("errores_sistema")

    op.drop_index("ix_logs_sistema_nivel", table_name="logs_sistema")
    op.drop_index("ix_logs_sistema_fecha", table_name="logs_sistema")
    op.drop_index("ix_logs_sistema_modulo", table_name="logs_sistema")
    op.drop_index("ix_logs_sistema_usuario", table_name="logs_sistema")
    op.drop_constraint("uq_logs_sistema_audit", "logs_sistema", type_="unique")
    op.drop_table("logs_sistema")

    bind = op.get_bind()
    SYSTEM_LOG_LEVEL.drop(bind, checkfirst=True)
