"""Pruebas para las rutas cargadas dinámicamente en el arranque."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_auth_status_route_returns_success() -> None:
    """La ruta de estado de autenticación debe responder con el mensaje esperado."""

    response = client.get("/auth/status")

    assert response.status_code == 200
    assert response.json() == {"message": "Módulo de autenticación operativo ✅"}


def test_example_ping_route_returns_success() -> None:
    """La ruta de ejemplo debe confirmar que está activa."""

    response = client.get("/ejemplo/ping")

    assert response.status_code == 200
    assert response.json() == {"detail": "Ruta de ejemplo activa ✅"}

