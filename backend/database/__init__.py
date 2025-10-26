"""Herramientas de base de datos para el backend de Softmobile."""
from __future__ import annotations

import os
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "softmobile.db"
"""Ruta predeterminada hacia la base de datos SQLite local."""


def _resolve_database_configuration() -> tuple[str, dict[str, object], Path | None]:
    """Obtiene la configuración de conexión a la base de datos desde el entorno."""

    env_url = os.getenv("DATABASE_URL") or os.getenv("SOFTMOBILE_DATABASE_URL")
    database_url = env_url or f"sqlite:///{DEFAULT_DATABASE_PATH}"

    engine_kwargs: dict[str, object] = {"future": True}
    connect_args: dict[str, object] = {}
    database_path: Path | None = None

    url = make_url(database_url)
    if url.drivername.startswith("sqlite"):
        database_is_memory = url.database == ":memory:"
        database_uses_uri = bool(url.database and url.database.startswith("file:"))

        if url.database and not database_is_memory and not database_uses_uri:
            database_path = Path(url.database)
            if not database_path.is_absolute():
                database_path = (Path.cwd() / database_path).resolve()
            database_url = url.set(database=str(database_path)).render_as_string(
                hide_password=False
            )
        elif not url.database:
            database_path = DEFAULT_DATABASE_PATH
            database_url = url.set(database=str(database_path)).render_as_string(
                hide_password=False
            )

        connect_args["check_same_thread"] = False

    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return database_url, engine_kwargs, database_path


SQLALCHEMY_DATABASE_URL, _ENGINE_KWARGS, DATABASE_PATH = _resolve_database_configuration()
_engine = create_engine(SQLALCHEMY_DATABASE_URL, **_ENGINE_KWARGS)
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)
_SQLALCHEMY_URL = make_url(SQLALCHEMY_DATABASE_URL)
_IS_SQLITE = _SQLALCHEMY_URL.drivername.startswith("sqlite")
Base = declarative_base()


def init_db() -> None:
    """Crea la carpeta, el archivo y las tablas necesarias si aún no existen."""

    if DATABASE_PATH is not None:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not DATABASE_PATH.exists():
            DATABASE_PATH.touch()

    # Importamos explícitamente los modelos para registrar sus metadatos.
    import_module("backend.models.user")
    import_module("backend.models.pos")

    Base.metadata.create_all(bind=_engine)

    if _IS_SQLITE:
        with _engine.connect() as connection:
            with connection.begin():
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
