"""Extiende tabla backup_jobs con rutas y metadatos faltantes.

Agrega columnas: json_path, sql_path, config_path, metadata_path,
critical_directory y components (JSON), para alinear el esquema con
backend.app.models.BackupJob y evitar errores sqlite3.OperationalError
por columnas inexistentes al consultar /backups/history.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import NoSuchTableError


# Revisiones Alembic
revision = "202511270001"
# Encadenar después de la última migración conocida para evitar múltiples heads
down_revision = "20251126_add_supervisor_pin_hash"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        cols = [c["name"] for c in insp.get_columns(table)]
    except NoSuchTableError:
        return False
    return column in cols


def upgrade() -> None:
    # Crear tabla si no existe
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = {t.lower(): t for t in inspector.get_table_names()}
    table_name = tables.get("backup_jobs")
    if table_name is None:
        op.create_table(
            "backup_jobs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("mode", sa.Enum("manual", "automatic",
                      name="backup_mode"), nullable=False),
            sa.Column("executed_at", sa.DateTime(
                timezone=True), nullable=True),
            sa.Column("pdf_path", sa.String(length=255), nullable=False),
            sa.Column("archive_path", sa.String(length=255), nullable=False),
            sa.Column("json_path", sa.String(length=255), nullable=True),
            sa.Column("sql_path", sa.String(length=255), nullable=True),
            sa.Column("config_path", sa.String(length=255), nullable=True),
            sa.Column("metadata_path", sa.String(length=255), nullable=True),
            sa.Column("critical_directory", sa.String(
                length=255), nullable=True),
            sa.Column("components", sa.JSON(), nullable=True),
            sa.Column("total_size_bytes", sa.Integer,
                      nullable=False, server_default="0"),
            sa.Column("notes", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("triggered_by_id", sa.Integer, nullable=True),
        )
        return

    # Agregar columnas si faltan
    if not _has_column("backup_jobs", "json_path"):
        op.add_column("backup_jobs", sa.Column(
            "json_path", sa.String(length=255), nullable=True))
    if not _has_column("backup_jobs", "sql_path"):
        op.add_column("backup_jobs", sa.Column(
            "sql_path", sa.String(length=255), nullable=True))
    if not _has_column("backup_jobs", "config_path"):
        op.add_column("backup_jobs", sa.Column(
            "config_path", sa.String(length=255), nullable=True))
    if not _has_column("backup_jobs", "metadata_path"):
        op.add_column("backup_jobs", sa.Column(
            "metadata_path", sa.String(length=255), nullable=True))
    if not _has_column("backup_jobs", "critical_directory"):
        op.add_column("backup_jobs", sa.Column(
            "critical_directory", sa.String(length=255), nullable=True))
    if not _has_column("backup_jobs", "components"):
        op.add_column("backup_jobs", sa.Column(
            "components", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remover columnas añadidas (idempotente si existen)
    for col in (
        "components",
        "critical_directory",
        "metadata_path",
        "config_path",
        "sql_path",
        "json_path",
    ):
        if _has_column("backup_jobs", col):
            op.drop_column("backup_jobs", col)
