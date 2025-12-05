"""
Utilidades de filtrado para reportes.

Extraídas desde crud_legacy.py para separación de responsabilidades.
"""

from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

from backend.app import models


def apply_sales_base_filters(
    statement,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    store_id: int | None,
):
    """Aplica filtros base para consultas de ventas."""
    statement = statement.where(func.upper(models.Sale.status) != "CANCELADA")
    if store_id is not None:
        statement = statement.where(models.Sale.store_id == store_id)
    if date_from is not None:
        statement = statement.where(models.Sale.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(models.Sale.created_at < date_to)
    return statement


def sales_returns_totals(
    db: Session,
    *,
    date_from: datetime | None,
    date_to: datetime | None,
    store_id: int | None,
):
    """Calcula totales de devoluciones para reutilizar en reportes de ventas."""
    returns_stmt = (
        select(
            func.coalesce(
                func.sum(
                    (models.SaleItem.total_line /
                     func.nullif(models.SaleItem.quantity, 0))
                    * models.SaleReturn.quantity
                ),
                0,
            ).label("refund_total"),
            func.count(models.SaleReturn.id).label("return_count"),
        )
        .select_from(models.SaleReturn)
        .join(models.SaleItem, models.SaleReturn.sale_item_id == models.SaleItem.id)
        .join(models.Sale, models.SaleItem.sale_id == models.Sale.id)
    )
    
    returns_stmt = apply_sales_base_filters(
        returns_stmt,
        date_from=date_from,
        date_to=date_to,
        store_id=store_id,
    )
    
    result = db.execute(returns_stmt).one_or_none()
    if result is None:
        return {"refund_total": 0, "return_count": 0}
    return {"refund_total": float(result.refund_total), "return_count": result.return_count}


def apply_system_log_filters(
    statement,
    *,
    user_id: int | None,
    module: str | None,
    level: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
):
    """Aplica filtros a consultas de logs del sistema."""
    if user_id is not None:
        statement = statement.where(models.SystemLog.user_id == user_id)
    if module is not None:
        statement = statement.where(models.SystemLog.module == module)
    if level is not None:
        statement = statement.where(models.SystemLog.level == level)
    if date_from is not None:
        statement = statement.where(models.SystemLog.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(models.SystemLog.created_at < date_to)
    return statement


def apply_system_error_filters(
    statement,
    *,
    module: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
):
    """Aplica filtros a consultas de errores del sistema."""
    if module is not None:
        statement = statement.where(models.SystemError.module == module)
    if date_from is not None:
        statement = statement.where(models.SystemError.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(models.SystemError.created_at < date_to)
    return statement
