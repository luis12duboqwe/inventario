"""Utilidades de acceso a datos para la autenticación ligera."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.app import crud, models, schemas
from backend.app.core.roles import OPERADOR
from backend.app.core.transactions import flush_session, transactional_session
from backend.app.database import Base, SessionLocal, get_db
from backend.database import run_migrations


def get_db_session() -> Iterator[Session]:
    """Provee sesiones de base de datos para tareas fuera de FastAPI."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_by_email(db: Session, email: str) -> models.User | None:
    """Recupera un usuario a partir de su correo electrónico normalizado."""

    _ensure_core_user_tables(db)
    normalized_email = email.lower().strip()
    return crud.get_user_by_username(db, normalized_email)


def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    """Devuelve el usuario identificado por ``user_id`` o ``None`` si no existe."""

    try:
        return crud.get_user(db, user_id)
    except LookupError:
        return None


def create_user(
    db: Session,
    *,
    email: str,
    hashed_password: str,
    username: str | None = None,
    display_name: str | None = None,
) -> models.User:
    """Crea un nuevo usuario persistiendo el hash proporcionado."""

    _ensure_core_user_tables(db)
    normalized_email = email.strip().lower()
    normalized_username = (username or normalized_email).strip().lower()
    display_label = (display_name or username or normalized_email).strip()
    payload = schemas.UserCreate(
        username=normalized_username,
        full_name=display_label,
        password="placeholder",
        roles=[OPERADOR],
        store_id=None,
    )
    user = crud.create_user(
        db,
        payload,
        password_hash=hashed_password,
        role_names=payload.roles,
        performed_by_id=None,
        reason="legacy_auth_migration",
    )
    return user


def _ensure_core_user_tables(db: Session) -> None:
    """Garantiza que las tablas del modelo unificado existan en el motor activo."""

    engine = db.get_bind()
    if engine is None:
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "usuarios" in tables and "roles" in tables and "user_roles" in tables:
        return

    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError:
        # Si el motor no permite la creación directa, dejar que la llamada original falle.
        return


__all__ = [
    "Base",
    "SessionLocal",
    "create_user",
    "get_db",
    "get_db_session",
    "get_user_by_email",
    "get_user_by_id",
    "run_migrations",
]
