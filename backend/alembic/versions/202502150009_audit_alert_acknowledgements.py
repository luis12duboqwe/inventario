"""Crea tabla para acuses manuales de alertas críticas."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202502150009"
down_revision = "202502150008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_alert_acknowledgements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("acknowledged_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["acknowledged_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", name="uq_audit_ack_entity"),
    )
    op.create_index(
        op.f("ix_audit_alert_acknowledgements_id"),
        "audit_alert_acknowledgements",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_alert_acknowledgements_entity_type"),
        "audit_alert_acknowledgements",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_alert_acknowledgements_entity_id"),
        "audit_alert_acknowledgements",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_alert_acknowledgements_acknowledged_by_id"),
        "audit_alert_acknowledgements",
        ["acknowledged_by_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_audit_alert_acknowledgements_acknowledged_by_id"),
        table_name="audit_alert_acknowledgements",
    )
    op.drop_index(
        op.f("ix_audit_alert_acknowledgements_entity_id"),
        table_name="audit_alert_acknowledgements",
    )
    op.drop_index(
        op.f("ix_audit_alert_acknowledgements_entity_type"),
        table_name="audit_alert_acknowledgements",
    )
    op.drop_index(
        op.f("ix_audit_alert_acknowledgements_id"),
        table_name="audit_alert_acknowledgements",
    )
    op.drop_table("audit_alert_acknowledgements")
