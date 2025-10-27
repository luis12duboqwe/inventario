"""Pruebas específicas para validar inicio de sesión con correo o usuario."""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.routes import auth as auth_module

_SQLITE_DSN = "sqlite+pysqlite:///:memory:"


def _sqlite_engine_options(database_url: str) -> tuple[str, dict[str, Any]]:
    """Devuelve el DSN definitivo y las opciones seguras para SQLite."""

    engine_kwargs: dict[str, Any] = {
        "future": True,
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    return database_url, engine_kwargs


def _resolve_database_url() -> tuple[str, dict[str, Any]]:
    """Selecciona un DSN aislado para las pruebas de autenticación."""

    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        return _sqlite_engine_options(_SQLITE_DSN)

    try:
        parsed_url = make_url(raw_url)
    except ArgumentError:
        parsed_url = None

    if parsed_url and parsed_url.drivername.startswith("sqlite") and "aiosqlite" not in parsed_url.drivername:
        return _sqlite_engine_options(raw_url)

    return _sqlite_engine_options(_SQLITE_DSN)


def _build_test_app():
    """Crea una instancia de FastAPI con base de datos aislada en SQLite."""

    database_url, engine_kwargs = _resolve_database_url()
    engine = create_engine(database_url, **engine_kwargs)
    testing_session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(auth_module.router)

    def override_get_db():
        db = testing_session()
        try:
            assert str(db.bind.url) == database_url, "Sesión inesperada"
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


def test_login_allows_email_or_username() -> None:
    """Verifica que el inicio de sesión acepte usuario o correo electrónico."""

    app = _build_test_app()
    client = TestClient(app)

    register_payload = {
        "username": "soporte",
        "email": "soporte@example.com",
        "password": "Credenciales123",
    }
    response = client.post("/auth/register", json=register_payload)
    assert response.status_code == 200

    login_with_username = client.post(
        "/auth/login",
        json={"username": "soporte", "password": "Credenciales123"},
    )
    assert login_with_username.status_code == 200

    login_with_email = client.post(
        "/auth/login",
        json={"username": "soporte@example.com", "password": "Credenciales123"},
    )
    assert login_with_email.status_code == 200
