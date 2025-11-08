"""Servicios de dominio para operaciones de caja en el POS."""
from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from .. import crud, models, schemas


def _normalize_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    normalized = reason.strip()
    return normalized or None


def open_session(
    db: Session,
    payload: schemas.CashSessionOpenRequest,
    *,
    opened_by_id: int | None,
    reason: str | None,
) -> models.CashRegisterSession:
    """Abre una nueva sesión de caja y entrega el modelo persistido."""

    session = crud.open_cash_session(
        db,
        payload,
        opened_by_id=opened_by_id,
        reason=_normalize_reason(reason),
    )
    return session


def close_session(
    db: Session,
    payload: schemas.CashSessionCloseRequest,
    *,
    closed_by_id: int | None,
    reason: str | None,
) -> models.CashRegisterSession:
    """Cierra la sesión indicada y devuelve el modelo actualizado."""

    session = crud.close_cash_session(
        db,
        payload,
        closed_by_id=closed_by_id,
        reason=_normalize_reason(reason),
    )
    return session


def last_session_for_store(db: Session, *, store_id: int) -> models.CashRegisterSession:
    """Obtiene la última sesión registrada para la sucursal."""

    return crud.get_last_cash_session_for_store(db, store_id=store_id)


def list_sessions(
    db: Session,
    *,
    store_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[models.CashRegisterSession]:
    """Lista sesiones de caja recientes para la sucursal indicada."""

    sessions: Iterable[models.CashRegisterSession] = crud.list_cash_sessions(
        db, store_id=store_id, limit=limit, offset=offset
    )
    return list(sessions)


def to_summary(session: models.CashRegisterSession) -> schemas.POSSessionSummary:
    """Convierte un modelo de sesión a su representación resumida."""

    return schemas.POSSessionSummary.from_model(session)


__all__ = [
    "open_session",
    "close_session",
    "last_session_for_store",
    "list_sessions",
    "to_summary",
]
