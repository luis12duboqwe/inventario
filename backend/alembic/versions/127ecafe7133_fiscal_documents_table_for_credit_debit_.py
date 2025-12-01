"""fiscal_documents table for credit debit notes

Revision ID: 127ecafe7133
Revises: 202511080004
Create Date: 2025-11-26 18:02:42.599228
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '127ecafe7133'
down_revision = '202511080004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'fiscal_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=30), nullable=False),
        sa.Column('document_number', sa.String(length=64), nullable=True),
        sa.Column('reference_sale_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['reference_sale_id'], [
                                'ventas.id_venta'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fiscal_documents_id'),
                    'fiscal_documents', ['id'], unique=False)
    op.create_index(op.f('ix_fiscal_documents_document_type'),
                    'fiscal_documents', ['document_type'], unique=False)
    op.create_index(op.f('ix_fiscal_documents_document_number'),
                    'fiscal_documents', ['document_number'], unique=False)
    op.create_index(op.f('ix_fiscal_documents_reference_sale_id'),
                    'fiscal_documents', ['reference_sale_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_fiscal_documents_reference_sale_id'),
                  table_name='fiscal_documents')
    op.drop_index(op.f('ix_fiscal_documents_document_number'),
                  table_name='fiscal_documents')
    op.drop_index(op.f('ix_fiscal_documents_document_type'),
                  table_name='fiscal_documents')
    op.drop_index(op.f('ix_fiscal_documents_id'),
                  table_name='fiscal_documents')
    op.drop_table('fiscal_documents')
