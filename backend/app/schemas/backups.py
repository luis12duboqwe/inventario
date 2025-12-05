from __future__ import annotations
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models import BackupComponent, BackupMode


class BackupRunRequest(BaseModel):
    nota: str | None = Field(default=None, max_length=255)
    componentes: set[BackupComponent] | None = Field(
        default=None,
        description=(
            "Componentes específicos a incluir en el respaldo. Si se omite se respaldan todos."
        ),
    )


class BackupJobResponse(BaseModel):
    id: int
    mode: BackupMode
    executed_at: datetime
    pdf_path: str
    archive_path: str
    json_path: str
    sql_path: str
    config_path: str
    metadata_path: str
    critical_directory: str
    components: list[BackupComponent]
    total_size_bytes: int
    notes: str | None
    triggered_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BackupRestoreRequest(BaseModel):
    componentes: set[BackupComponent] | None = Field(
        default=None,
        description="Componentes a restaurar. Si no se especifica se usarán todos los disponibles.",
    )
    destino: str | None = Field(
        default=None,
        max_length=255,
        description="Directorio destino para los archivos restaurados. Se crea si no existe.",
    )
    aplicar_base_datos: bool = Field(
        default=False,
        description=(
            "Cuando es verdadero ejecuta el volcado SQL directamente sobre la base de datos activa."
        ),
    )


class BackupRestoreResponse(BaseModel):
    job_id: int
    componentes: list[BackupComponent]
    destino: str | None
    resultados: dict[str, str]
