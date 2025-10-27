"""Utilidades para manejo seguro de transacciones de base de datos."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session


@contextmanager
def transactional_session(session: Session) -> Iterator[Session]:
    """Ejecuta operaciones dentro de una transacción controlada."""

    existing = session.get_transaction()
    if existing is not None:
        with session.begin_nested():
            yield session
        return

    with session.begin():
        yield session


def commit_session(session: Session) -> None:
    """Confirma la transacción actual realizando rollback ante errores."""

    if session.get_transaction() is not None:
        raise RuntimeError(
            "commit_session no debe invocarse con una transacción activa; "
            "usa transactional_session para manejar el contexto."
        )
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise


def flush_session(session: Session) -> None:
    """Sincroniza cambios pendientes garantizando rollback en caso de fallo."""

    try:
        session.flush()
    except Exception:
        session.rollback()
        raise
