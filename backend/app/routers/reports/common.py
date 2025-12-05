from __future__ import annotations
from datetime import date, datetime, timedelta
from fastapi import HTTPException, status
from backend.app.config import settings


def ensure_analytics_enabled() -> None:
    if not settings.enable_analytics_adv or not settings.enable_purchases_sales:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analítica avanzada no disponible",
        )


def ensure_fiscal_reports_enabled() -> None:
    if not settings.enable_purchases_sales:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reportes fiscales no disponibles",
        )


def coerce_datetime(value: datetime | date | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time())


def normalize_sales_range(
    date_from: datetime | date | None,
    date_to: datetime | date | None,
) -> tuple[datetime | None, datetime | None]:
    normalized_from = coerce_datetime(date_from)
    normalized_to = coerce_datetime(date_to)
    if isinstance(date_to, date) and not isinstance(date_to, datetime):
        normalized_to = normalized_to + \
            timedelta(days=1) if normalized_to else None
    elif isinstance(date_to, datetime) and normalized_to is not None:
        normalized_to = normalized_to + timedelta(microseconds=1)
    return normalized_from, normalized_to


def format_range_value(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()
