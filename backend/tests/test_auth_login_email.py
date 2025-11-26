"""Pruebas específicas para validar inicio de sesión con correo o usuario."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.routers import auth as auth_router


def _build_test_app():
    """Crea una instancia de FastAPI con base de datos en memoria."""

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
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
    app.include_router(auth_router.router)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


def test_bootstrap_and_token_login_flow() -> None:
    """Permite registrar al primer administrador y obtener tokens válidos."""

    app = _build_test_app()

    with TestClient(app) as client:
        bootstrap_payload = {
            "username": "soporte",
            "email": "soporte@example.com",
            "password": "Credenciales123",
            "roles": ["ADMIN"],
        }
        bootstrap_response = client.post("/auth/bootstrap", json=bootstrap_payload)

        assert bootstrap_response.status_code == 201
        created_user = bootstrap_response.json()
        assert created_user["username"] == bootstrap_payload["username"]

        login_response = client.post(
            "/auth/token",
            data={
                "username": bootstrap_payload["username"],
                "password": bootstrap_payload["password"],
            },
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        assert login_response.status_code == 200
        token_payload = login_response.json()
        assert "access_token" in token_payload
