"""Configurar secuencia autoincremental para borradores POS."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202502150008"
down_revision = "202502150007"
branch_labels = None
depends_on = None


SEQUENCE_NAME = "pos_draft_sales_id_seq"
TABLE_NAME = "pos_draft_sales"
COLUMN_NAME = "id"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.sequences
                    WHERE sequence_schema = 'public'
                      AND sequence_name = :seq_name
                ) THEN
                    EXECUTE format('CREATE SEQUENCE %I', :seq_name);
                END IF;
            END;
            $$
            """
        ),
        {"seq_name": SEQUENCE_NAME},
    )

    op.execute(
        sa.text(
            f"""
            SELECT setval(
                :seq_name,
                COALESCE((SELECT MAX({COLUMN_NAME}) FROM {TABLE_NAME}), 0)
            )
            """
        ),
        {"seq_name": SEQUENCE_NAME},
    )

    op.execute(
        sa.text(
            f"ALTER TABLE {TABLE_NAME} ALTER COLUMN {COLUMN_NAME} SET DEFAULT nextval(:seq_name)"
        ),
        {"seq_name": SEQUENCE_NAME},
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"ALTER TABLE {TABLE_NAME} ALTER COLUMN {COLUMN_NAME} DROP DEFAULT"
        )
    )

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.sequences
                    WHERE sequence_schema = 'public'
                      AND sequence_name = :seq_name
                ) THEN
                    EXECUTE format('DROP SEQUENCE %I', :seq_name);
                END IF;
            END;
            $$
            """
        ),
        {"seq_name": SEQUENCE_NAME},
    )
