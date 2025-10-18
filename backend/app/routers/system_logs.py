"""Rutas para consultar logs y errores del sistema corporativo."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..core.roles import ADMIN
from ..database import get_db
from ..security import require_roles

router = APIRouter(prefix="/logs", tags=["logs y auditoría"])


def _parse_iso_datetime(value: str | None, *, field: str) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - validación defensiva
        raise HTTPException(
            status_code=422,
            detail=f"Formato de fecha inválido para {field}. Usa ISO 8601.",
        ) from exc


@router.get("/sistema", response_model=list[schemas.SystemLogEntry])
def get_system_logs(
    usuario: str | None = Query(default=None, max_length=120, description="Usuario responsable"),
    modulo: str | None = Query(default=None, max_length=80, description="Nombre del módulo"),
    nivel: schemas.SystemLogLevel | None = Query(
        default=None, description="Nivel de severidad (info, warning, error, critical)"
    ),
    fecha_desde: str | None = Query(default=None, description="Fecha mínima en formato ISO 8601"),
    fecha_hasta: str | None = Query(default=None, description="Fecha máxima en formato ISO 8601"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),  # noqa: ANN001
):
    start = _parse_iso_datetime(fecha_desde, field="fecha_desde")
    end = _parse_iso_datetime(fecha_hasta, field="fecha_hasta")
    logs = crud.list_system_logs(
        db,
        usuario=usuario,
        modulo=modulo,
        nivel=nivel,
        date_from=start,
        date_to=end,
    )
    return [schemas.SystemLogEntry.model_validate(item) for item in logs]


@router.get("/errores", response_model=list[schemas.SystemErrorEntry])
def get_system_errors(
    usuario: str | None = Query(default=None, max_length=120, description="Usuario afectado"),
    modulo: str | None = Query(default=None, max_length=80, description="Módulo donde ocurrió"),
    fecha_desde: str | None = Query(default=None, description="Fecha mínima en formato ISO 8601"),
    fecha_hasta: str | None = Query(default=None, description="Fecha máxima en formato ISO 8601"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN)),  # noqa: ANN001
):
    start = _parse_iso_datetime(fecha_desde, field="fecha_desde")
    end = _parse_iso_datetime(fecha_hasta, field="fecha_hasta")
    errors = crud.list_system_errors(
        db,
        usuario=usuario,
        modulo=modulo,
        date_from=start,
        date_to=end,
    )
    return [schemas.SystemErrorEntry.model_validate(item) for item in errors]


__all__ = ["router"]
