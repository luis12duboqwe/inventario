"""Herramientas de base de datos para el backend de Softmobile."""
from __future__ import annotations

import os
from collections.abc import Iterator
import logging
from importlib import import_module
from pathlib import Path

from alembic import command
from alembic.util.exc import CommandError
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

# Cargar variables de entorno desde .env antes de configurar la base de datos
try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).resolve().parents[1] / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass  # python-dotenv no está disponible, usar variables de entorno del sistema


def _resolve_database_configuration() -> tuple[str, dict[str, object], Path | None]:
    """Obtiene la configuración de conexión a la base de datos desde el entorno."""

    env_url = os.getenv("DATABASE_URL") or os.getenv("SOFTMOBILE_DATABASE_URL")
    if not env_url:
        raise RuntimeError(
            "Define la variable de entorno DATABASE_URL o SOFTMOBILE_DATABASE_URL "
            "con la cadena de conexión completa."
        )
    database_url = env_url

    engine_kwargs: dict[str, object] = {"future": True}
    connect_args: dict[str, object] = {}
    database_path: Path | None = None

    url = make_url(database_url)
    if url.drivername.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if url.database in {None, "", ":memory:"}:
            engine_kwargs["poolclass"] = StaticPool
        else:
            database_path = Path(url.database)
            if not database_path.is_absolute():
                database_path = (Path.cwd() / database_path).resolve()
            database_url = url.set(database=str(database_path)).render_as_string(
                hide_password=False
            )

    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return database_url, engine_kwargs, database_path


SQLALCHEMY_DATABASE_URL, _ENGINE_KWARGS, DATABASE_PATH = _resolve_database_configuration()
_engine = create_engine(SQLALCHEMY_DATABASE_URL, **_ENGINE_KWARGS)
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def _prepare_sqlite_database_file() -> None:
    """Asegura la existencia del archivo SQLite cuando aplica."""

    if DATABASE_PATH is None:
        return

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATABASE_PATH.exists():
        DATABASE_PATH.touch()


def _build_alembic_config() -> Config:
    """Genera la configuración de Alembic con la URL activa."""

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
    return config


def run_migrations() -> None:
    """Ejecuta las migraciones de Alembic hasta la cabeza actual."""

    _prepare_sqlite_database_file()
    import_module("backend.models.user")
    import_module("backend.models.pos")
    config = _build_alembic_config()
    logger = logging.getLogger(__name__)

    def _safe_upgrade(target: str) -> None:
        try:
            command.upgrade(config, target)
        except OperationalError as exc:
            message = str(exc).lower()
            if "already exists" in message:
                logger.warning(
                    "Migración %s omitida: %s", target, exc, exc_info=False
                )
                return
            raise

    _safe_upgrade("heads")
    try:
        _safe_upgrade("head")
    except CommandError as exc:
        if "Multiple head revisions" in str(exc):
            _safe_upgrade("heads")
        else:
            raise
    _ensure_core_user_columns()
    Base.metadata.create_all(bind=_engine)


def _ensure_core_user_columns() -> None:
    """Garantiza columnas críticas del núcleo cuando existen tablas corporativas."""

    inspector = inspect(_engine)
    if "usuarios" not in inspector.get_table_names():
        return

    usuarios_columns = {
        column["name"] for column in inspector.get_columns("usuarios")
    }

    with _engine.begin() as connection:
        if "failed_login_attempts" not in usuarios_columns:
            connection.execute(
                text(
                    "ALTER TABLE usuarios ADD COLUMN failed_login_attempts INTEGER "
                    "NOT NULL DEFAULT 0"
                )
            )
        if "last_login_attempt_at" not in usuarios_columns:
            connection.execute(
                text(
                    "ALTER TABLE usuarios ADD COLUMN last_login_attempt_at DATETIME"
                )
            )
        if "locked_until" not in usuarios_columns:
            connection.execute(
                text("ALTER TABLE usuarios ADD COLUMN locked_until DATETIME")
            )


def init_db() -> None:
    """Compatibilidad retroactiva: delega en ``run_migrations``."""

    run_migrations()


def get_db() -> Iterator[Session]:
    """Genera sesiones de base de datos para dependencias FastAPI."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["Base", "SessionLocal", "run_migrations", "init_db", "get_db", "DATABASE_PATH"]
