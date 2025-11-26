"""Archivo de configuración para las migraciones de Alembic."""
from __future__ import annotations
from backend.app.database import Base
from backend.app.config import settings

import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Agregar el directorio padre al path para que backend sea importable
_CURRENT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _CURRENT_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Cargar variables de entorno desde .env antes de importar configuración
try:
    from dotenv import load_dotenv
    _env_file = _BACKEND_DIR / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass  # python-dotenv no está disponible, usar variables de entorno del sistema

from backend.app import models  # noqa: F401 - necesario para detectar metadatos

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Respetar una URL ya inyectada (por pruebas/scripts) y solo usar la de settings
_configured_url = config.get_main_option("sqlalchemy.url")
if not _configured_url or _configured_url.strip() == "":
    config.set_main_option("sqlalchemy.url", settings.database_url)
    _configured_url = settings.database_url


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecuta las migraciones en modo offline."""

    # Usar la URL efectiva configurada (puede venir de pruebas)
    _effective_url = config.get_main_option(
        "sqlalchemy.url") or settings.database_url
    context.configure(
        url=_effective_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta las migraciones en modo online."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection,
                          target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
