"""Inicialización de la base de datos y utilidades comunes."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings

Base = declarative_base()


def create_engine_from_url(url: str) -> Engine:
    """Crea un motor de SQLAlchemy listo para usarse."""

    engine_kwargs: dict[str, object] = {"future": True}
    connect_args: dict[str, object] = {}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if url == "sqlite:///:memory:":
            engine_kwargs["poolclass"] = StaticPool

    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return create_engine(url, **engine_kwargs)


engine: Engine = create_engine_from_url(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator:
    """Entrega sesiones de base de datos gestionadas para FastAPI."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
