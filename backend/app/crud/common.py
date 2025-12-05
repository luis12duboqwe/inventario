"""Funciones comunes y utilidades para los módulos CRUD."""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .. import models


def to_decimal(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def normalize_date_range(
    date_from: date | datetime | None, date_to: date | datetime | None
) -> tuple[datetime, datetime]:
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

    return start_dt, end_dt
