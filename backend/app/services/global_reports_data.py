"""Capa de datos para el reporte global, responsable de producir DTO listos para renderizar."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .. import crud, schemas


@dataclass(frozen=True, slots=True)
class GlobalReportDataset:
    """Contenedor inmutable con la información necesaria para renderizar el reporte global."""

    overview: schemas.GlobalReportOverview
    dashboard: schemas.GlobalReportDashboard


def get_overview(
    db: Session,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    module: Optional[str] = None,
    severity: Optional[schemas.SystemLogLevel] = None,
) -> schemas.GlobalReportOverview:
    """Obtiene el resumen del reporte global aplicando los filtros solicitados."""

    return crud.build_global_report_overview(
        db,
        date_from=date_from,
        date_to=date_to,
        module=module,
        severity=severity,
    )


def get_dashboard(
    db: Session,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    module: Optional[str] = None,
    severity: Optional[schemas.SystemLogLevel] = None,
) -> schemas.GlobalReportDashboard:
    """Obtiene la vista de tablero del reporte global aplicando los filtros solicitados."""

    return crud.build_global_report_dashboard(
        db,
        date_from=date_from,
        date_to=date_to,
        module=module,
        severity=severity,
    )


def build_dataset(
    db: Session,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    module: Optional[str] = None,
    severity: Optional[schemas.SystemLogLevel] = None,
) -> GlobalReportDataset:
    """Construye la estructura de datos completa para renderizar el reporte global."""

    overview = get_overview(
        db,
        date_from=date_from,
        date_to=date_to,
        module=module,
        severity=severity,
    )
    dashboard = get_dashboard(
        db,
        date_from=date_from,
        date_to=date_to,
        module=module,
        severity=severity,
    )
    return GlobalReportDataset(overview=overview, dashboard=dashboard)


__all__ = [
    "GlobalReportDataset",
    "get_overview",
    "get_dashboard",
    "build_dataset",
]
