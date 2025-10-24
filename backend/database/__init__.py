"""Herramientas de base de datos para el backend de Softmobile."""
from __future__ import annotations

from collections.abc import Iterator
from importlib import import_module
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_PATH = Path(__file__).resolve().parent / "softmobile.db"
"""Ruta predeterminada hacia la base de datos SQLite local."""

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def init_db() -> None:
    """Crea la carpeta, el archivo y las tablas necesarias si aún no existen."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATABASE_PATH.exists():
        DATABASE_PATH.touch()

    # Importamos explícitamente los modelos para registrar sus metadatos.
    import_module("backend.models.user")
    import_module("backend.models.pos")

    Base.metadata.create_all(bind=_engine)

    with _engine.connect() as connection:
        columns = connection.execute(text("PRAGMA table_info(users)")).fetchall()
        has_verified = any(column[1] == "is_verified" for column in columns)
        if not has_verified:
            connection.execute(
                text(
                    "ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0"
                )
            )


def get_db() -> Iterator[Session]:
    """Genera sesiones de base de datos para dependencias FastAPI."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["Base", "SessionLocal", "init_db", "get_db", "DATABASE_PATH"]
