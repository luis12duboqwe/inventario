"""Utilidades de acceso a datos para la autenticación ligera."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from backend.app.core.transactions import flush_session, transactional_session
from backend.database import Base, SessionLocal, get_db, init_db
from backend.models.user import User


def get_db_session() -> Iterator[Session]:
    """Provee sesiones de base de datos para tareas fuera de FastAPI."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Recupera un usuario a partir de su correo electrónico normalizado."""

    return db.query(User).filter(User.email == email.lower().strip()).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Devuelve el usuario identificado por ``user_id`` o ``None`` si no existe."""

    return db.query(User).filter(User.id == user_id).first()


def create_user(
    db: Session,
    *,
    email: str,
    hashed_password: str,
    username: str | None = None,
) -> User:
    """Crea un nuevo usuario persistiendo el hash proporcionado."""

    normalized_email = email.strip().lower()
    normalized_username = (username or normalized_email).strip().lower()
    user = User(
        email=normalized_email,
        username=normalized_username,
        hashed_password=hashed_password,
    )
    with transactional_session(db):
        db.add(user)
        flush_session(db)
        db.refresh(user)
    return user


__all__ = [
    "Base",
    "SessionLocal",
    "create_user",
    "get_db",
    "get_db_session",
    "get_user_by_email",
    "get_user_by_id",
    "init_db",
]
