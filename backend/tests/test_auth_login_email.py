"""Pruebas específicas para validar inicio de sesión con correo o usuario."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.routes import auth as auth_module


def _build_test_app():
    """Crea una instancia de FastAPI con base de datos en memoria."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        future=True,
        poolclass=StaticPool,
    )
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
            assert str(db.bind.url) == "sqlite://", "Sesión inesperada"
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
    assert response.status_code == 201

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
