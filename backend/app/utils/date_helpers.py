"""Utilidades para normalización y manejo de fechas/tiempos."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


def normalize_date_range(
    date_from: date | datetime | None, date_to: date | datetime | None
) -> tuple[datetime, datetime]:
    """Normaliza un rango de fechas asegurando valores válidos y cobertura completa.
    
    Args:
        date_from: Fecha inicial (None = últimos 30 días)
        date_to: Fecha final (None = ahora)
        
    Returns:
        Tupla (start_dt, end_dt) con datetimes timezone-aware completos
        
    Notas:
        - Convierte dates a datetimes con horario completo (00:00:00 - 23:59:59)
        - Si date_from > date_to, los intercambia
        - Amplía fechas recibidas como dates al día completo
        - Rango por defecto: últimos 30 días hasta ahora
    """
    now = datetime.now(timezone.utc)

    if isinstance(date_from, datetime):
        start_dt = date_from
        if start_dt.time() == datetime.min.time():
            start_dt = start_dt.replace(
                hour=0, minute=0, second=0, microsecond=0)
    elif isinstance(date_from, date):
        start_dt = datetime.combine(date_from, datetime.min.time())
    else:
        start_dt = now - timedelta(days=30)

    if isinstance(date_to, datetime):
        end_dt = date_to
        if end_dt.time() == datetime.min.time():
            end_dt = end_dt.replace(
                hour=23, minute=59, second=59, microsecond=999999)
    elif isinstance(date_to, date):
        end_dt = datetime.combine(date_to, datetime.max.time())
    else:
        end_dt = now

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    # Salvaguarda adicional: si tras reordenar el rango el extremo superior
    # quedó en inicio de día (00:00:00), amplíalo al final del día para no
    # perder movimientos registrados durante la jornada destino.
    if end_dt.time() == datetime.min.time():
        end_dt = end_dt.replace(
            hour=23, minute=59, second=59, microsecond=999999)

    return start_dt, end_dt
