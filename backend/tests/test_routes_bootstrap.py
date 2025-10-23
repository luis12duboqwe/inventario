"""Pruebas para las rutas cargadas dinámicamente en el arranque."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.database import SessionLocal, init_db
from backend.main import app
from backend.models import User


def _reset_database() -> None:
    """Limpia las tablas antes de ejecutar los escenarios de autenticación."""

    init_db()
    with SessionLocal() as session:
        session.query(User).delete()
        session.commit()


_reset_database()
client = TestClient(app)


def test_auth_status_route_returns_success() -> None:
    """La ruta de estado de autenticación debe responder con el mensaje esperado."""

    response = client.get("/auth/status")

    assert response.status_code == 200
    assert response.json() == {"message": "Autenticación lista y conectada a SQLite ✅"}


def test_register_login_and_verify_flow() -> None:
    """Permite registrar un usuario, iniciar sesión y validar el token emitido."""

    register_payload = {
        "username": "soporte",
        "email": "soporte@example.com",
        "password": "contraseña_segura",
    }
    register_response = client.post("/auth/register", json=register_payload)

    assert register_response.status_code == 200
    registered = register_response.json()
    assert registered["username"] == register_payload["username"]
    assert registered["email"] == register_payload["email"]

    login_response = client.post(
        "/auth/login",
        json={
            "username": register_payload["username"],
            "password": register_payload["password"],
        },
    )

    assert login_response.status_code == 200
    token_payload = login_response.json()
    assert "access_token" in token_payload

    verify_response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )

    assert verify_response.status_code == 200
    verification = verify_response.json()
    assert verification["valid"] is True
    assert verification["user"]["username"] == register_payload["username"]


def test_register_repeated_user_is_rejected() -> None:
    """Registrar dos veces el mismo usuario debe devolver un error 400."""

    payload = {
        "username": "soporte",
        "email": "soporte@example.com",
        "password": "contraseña_segura",
    }

    conflict_response = client.post("/auth/register", json=payload)

    assert conflict_response.status_code == 400
    assert conflict_response.json()["detail"] == "El nombre de usuario o correo ya están registrados."


__all__ = [
    "test_auth_status_route_returns_success",
    "test_register_login_and_verify_flow",
    "test_register_repeated_user_is_rejected",
]
