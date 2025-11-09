"""Agregar tablas de garantías y columna de estado.

Revision ID: 202511070007_warranty_structures
Revises: 202511070006_return_dispositions
Create Date: 2025-11-07 12:30:00 UTC

Nota: Compatible con v2.2.0 sin alterar etiquetas de versión del producto.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202511070007_warranty_structures"
down_revision = "202511070006_return_dispositions"
branch_labels = None
depends_on = None


warranty_status_enum = sa.Enum(
    "SIN_GARANTIA",
    "ACTIVA",
    "VENCIDA",
    "RECLAMO",
    "RESUELTA",
    name="warranty_status",
)

warranty_claim_type_enum = sa.Enum(
    "REPARACION",
    "REEMPLAZO",
    name="warranty_claim_type",
)

warranty_claim_status_enum = sa.Enum(
    "ABIERTO",
    "EN_PROCESO",
    "RESUELTO",
    "CANCELADO",
    name="warranty_claim_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    warranty_status_enum.create(bind, checkfirst=True)
    warranty_claim_type_enum.create(bind, checkfirst=True)
    warranty_claim_status_enum.create(bind, checkfirst=True)

    with op.batch_alter_table("detalle_ventas", reflect_kwargs={"resolve_fks": False}) as batch_op:
        batch_op.add_column(
            sa.Column("warranty_status", warranty_status_enum.copy(), nullable=True)
        )

    op.create_table(
        "warranty_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sale_item_id",
            sa.Integer(),
            sa.ForeignKey("detalle_ventas.id_detalle", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Integer(),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "coverage_months",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("activation_date", sa.Date(), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            warranty_status_enum.copy(),
            nullable=False,
            server_default="ACTIVA",
        ),
        sa.Column("serial_number", sa.String(length=120), nullable=True),
        sa.Column("activation_channel", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("sale_item_id", name="uq_warranty_sale_item"),
    )
    op.create_index(
        "ix_warranty_assignments_device_id",
        "warranty_assignments",
        ["device_id"],
        unique=False,
    )

    op.create_table(
        "warranty_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "assignment_id",
            sa.Integer(),
            sa.ForeignKey("warranty_assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "claim_type",
            warranty_claim_type_enum.copy(),
            nullable=False,
        ),
        sa.Column(
            "status",
            warranty_claim_status_enum.copy(),
            nullable=False,
            server_default="ABIERTO",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "performed_by_id",
            sa.Integer(),
            sa.ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "repair_order_id",
            sa.Integer(),
            sa.ForeignKey("repair_orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_warranty_claim_assignment_id",
        "warranty_claims",
        ["assignment_id"],
        unique=False,
    )
    op.create_index(
        "ix_warranty_claim_repair_order_id",
        "warranty_claims",
        ["repair_order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_warranty_claim_repair_order_id",
        table_name="warranty_claims",
    )
    op.drop_index(
        "ix_warranty_claim_assignment_id",
        table_name="warranty_claims",
    )
    op.drop_table("warranty_claims")

    op.drop_index(
        "ix_warranty_assignments_device_id",
        table_name="warranty_assignments",
    )
    op.drop_table("warranty_assignments")

    with op.batch_alter_table("detalle_ventas", reflect_kwargs={"resolve_fks": False}) as batch_op:
        batch_op.drop_column("warranty_status")

    bind = op.get_bind()
    warranty_claim_status_enum.drop(bind, checkfirst=True)
    warranty_claim_type_enum.drop(bind, checkfirst=True)
    warranty_status_enum.drop(bind, checkfirst=True)
