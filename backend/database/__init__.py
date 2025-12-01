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
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base as AppBase

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
Base = AppBase
# Asegurar que los modelos principales estén registrados en la metadata compartida.
import backend.app.models  # noqa: F401  # pragma: no cover


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
    _migrate_lightweight_users()
    _ensure_core_user_columns()
    Base.metadata.create_all(bind=_engine)


def _ensure_core_user_columns() -> None:
    """Garantiza columnas críticas del núcleo cuando existen tablas corporativas."""

    inspector = inspect(_engine)
    if "usuarios" not in inspector.get_table_names():
        return

    with _engine.begin() as connection:
        inspector = inspect(connection)
        usuarios_columns = {
            column["name"] for column in inspector.get_columns("usuarios")
        }

        column_definitions = {
            "nombre": "ALTER TABLE usuarios ADD COLUMN nombre VARCHAR(120) NOT NULL DEFAULT ''",
            "password_hash": "ALTER TABLE usuarios ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''",
            "rol": "ALTER TABLE usuarios ADD COLUMN rol VARCHAR(30) NOT NULL DEFAULT 'OPERADOR'",
            "estado": "ALTER TABLE usuarios ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'",
            "is_active": "ALTER TABLE usuarios ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
            "fecha_creacion": "ALTER TABLE usuarios ADD COLUMN fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "failed_login_attempts": "ALTER TABLE usuarios ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0",
            "last_login_attempt_at": "ALTER TABLE usuarios ADD COLUMN last_login_attempt_at DATETIME",
            "locked_until": "ALTER TABLE usuarios ADD COLUMN locked_until DATETIME",
        }

        for column, definition in column_definitions.items():
            if column not in usuarios_columns:
                connection.execute(text(definition))


def _migrate_lightweight_users() -> None:
    """Migra registros desde la tabla ``users`` hacia ``usuarios``.

    El modelo ligero almacenaba credenciales básicas en la tabla ``users``. Esta
    rutina garantiza que dichos registros se sincronicen con el modelo principal
    con roles y campos extendidos sin duplicar usuarios existentes.
    """

    inspector = inspect(_engine)
    table_names = set(inspector.get_table_names())
    if "usuarios" not in table_names:
        usuarios_table = Base.metadata.tables.get("usuarios")
        if usuarios_table is None:
            return

        usuarios_table.create(bind=_engine, checkfirst=True)
        table_names = set(inspect(_engine).get_table_names())

    if "users" not in table_names:
        return

    _ensure_core_user_columns()

    with _engine.begin() as connection:
        inspector = inspect(connection)
        if "usuarios" not in set(inspector.get_table_names()):
            return

        available_columns = {
            column["name"] for column in inspector.get_columns("users")
        }
        projected_columns = []
        for column in (
            "id",
            "username",
            "email",
            "hashed_password",
            "is_active",
            "created_at",
            "role",
            "rol",
            "failed_login_attempts",
            "last_login_attempt_at",
            "locked_until",
        ):
            if column in available_columns:
                projected_columns.append(column)
            else:
                projected_columns.append(f"NULL AS {column}")

        legacy_rows = list(
            connection.execute(
                text(
                    f"SELECT {', '.join(projected_columns)} FROM users"
                )
            ).mappings()
        )

        available_roles: dict[str, int] = {}
        if "roles" in table_names:
            role_rows = connection.execute(
                text("SELECT id, name FROM roles")
            ).mappings()
            available_roles = {row["name"].upper(): row["id"] for row in role_rows}

        for row in legacy_rows:
            correo = (row.get("email") or row.get("username") or "").strip().lower()
            if not correo:
                continue

            existing_user = connection.execute(
                text("SELECT id_usuario FROM usuarios WHERE correo = :correo"),
                {"correo": correo},
            ).scalar_one_or_none()
            if existing_user is not None:
                user_id = existing_user
            else:
                nombre = (row.get("username") or "").strip()
                is_active = row.get("is_active")
                estado = "ACTIVO" if is_active is None or bool(is_active) else "INACTIVO"
                primary_role = (
                    row.get("role")
                    or row.get("rol")
                    or "OPERADOR"
                )
                primary_role = primary_role.strip().upper() or "OPERADOR"

                connection.execute(
                    text(
                        "INSERT INTO usuarios (correo, nombre, password_hash, rol, estado, "
                        "is_active, fecha_creacion, failed_login_attempts, last_login_attempt_at, "
                        "locked_until) VALUES (:correo, :nombre, :password, :rol, :estado, "
                        ":is_active, COALESCE(:fecha_creacion, CURRENT_TIMESTAMP), :failed_attempts, "
                        ":last_attempt, :locked_until)"
                    ),
                    {
                        "correo": correo,
                        "nombre": nombre or correo,
                        "password": row.get("hashed_password") or "",
                        "rol": primary_role,
                        "estado": estado,
                        "is_active": bool(True if is_active is None else is_active),
                        "fecha_creacion": row.get("created_at"),
                        "failed_attempts": int(row.get("failed_login_attempts") or 0),
                        "last_attempt": row.get("last_login_attempt_at"),
                        "locked_until": row.get("locked_until"),
                    },
                )
                user_id = connection.execute(
                    text(
                        "SELECT id_usuario FROM usuarios WHERE correo = :correo"
                    ),
                    {"correo": correo},
                ).scalar_one()

            role_name = (
                row.get("role")
                or row.get("rol")
                or "OPERADOR"
            )
            role_name = role_name.strip().upper() or "OPERADOR"
            role_id = available_roles.get(role_name) or available_roles.get("OPERADOR")

            if role_id and "user_roles" in table_names:
                connection.execute(
                    text(
                        "INSERT INTO user_roles (user_id, role_id)"
                        " SELECT :user_id, :role_id"
                        " WHERE NOT EXISTS ("
                        "   SELECT 1 FROM user_roles"
                        "   WHERE user_id = :user_id AND role_id = :role_id"
                        " )"
                    ),
                    {"user_id": user_id, "role_id": role_id},
                )

        connection.execute(text("DROP TABLE users"))


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
