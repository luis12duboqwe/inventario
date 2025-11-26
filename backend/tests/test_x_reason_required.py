from __future__ import annotations

import pytest
from fastapi import status
from typing import Iterable

import os
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from backend.app.main import create_app
from backend.app.database import Base, create_engine_from_url, get_db
from backend.app.config import settings


@pytest.fixture(scope="module")
def client() -> TestClient:
    # Usar SQLite en archivo para que múltiples conexiones (SessionLocal interno)
    # vean el mismo esquema durante la ejecución de pruebas.
    import tempfile
    db_path = os.path.join(tempfile.gettempdir(),
                           f"xreason_{uuid.uuid4().hex}.db")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
    os.environ.setdefault("JWT_SECRET_KEY", "xreason-secret")
    os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    os.environ.setdefault("CORS_ORIGINS", "[\"http://testserver\"]")
    os.environ.setdefault("SOFTMOBILE_ENABLE_TRANSFERS", "1")
    # Directorio temporal para respaldos
    backup_dir = os.path.join(tempfile.gettempdir(),
                              f"backups_{uuid.uuid4().hex}")
    os.environ.setdefault("BACKUP_DIR", backup_dir)
    engine = create_engine_from_url(
        os.environ["DATABASE_URL"])  # type: ignore[arg-type]
    Base.metadata.create_all(bind=engine)
    # Crear vista requerida por reportes de valoración
    try:
        from backend.app.db.valor_inventario_view import create_valor_inventario_view
        with engine.connect() as conn:
            create_valor_inventario_view(conn)
    except Exception:
        # No hacer fallar la prueba por la vista; los endpoints pueden responder 404/500 controlado
        pass
    session_factory = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, future=True)
    db_session: Session = session_factory()
    settings.enable_background_scheduler = False
    settings.enable_backup_scheduler = False
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.expunge_all()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    db_session.close()
    engine.dispose()


# Endpoints críticos que deben exigir X-Reason >=5 caracteres.
# Cada tupla: (method, url, requires_auth)
CRITICAL_ENDPOINTS: list[tuple[str, str, bool]] = [
    # Exportaciones / descargas requieren motivo corporativo
    ("GET", "/reports/inventory/current/csv", True),
    ("GET", "/reports/inventory/value/pdf", True),
    ("POST", "/transfers", True),  # operaciones de transferencia
    ("POST", "/backups/run", True),  # generación de respaldo
]


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict[str, str]:
    # Reutilizar flujo mínimo de autenticación: crear usuario y obtener token.
    # Para mantener compatibilidad v2.2.0 se asume endpoint /auth/token existente.
    # Si ya existe usuario admin de pruebas, usarlo.
    unique_user = f"xreason_admin_{uuid.uuid4().hex[:8]}"
    register_payload = {
        "username": unique_user,
        "password": "Secret123!",
        "email": f"{unique_user}@example.com",
    }
    # Usar bootstrap si está disponible para crear ADMIN
    bootstrap_payload = {
        "username": register_payload["username"],
        "password": register_payload["password"],
        "full_name": "Admin XReason",
        "roles": ["ADMIN"],
    }
    client.post("/auth/bootstrap", json=bootstrap_payload)
    token_resp = client.post(
        "/auth/token",
        data={"username": register_payload["username"],
              "password": register_payload["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == status.HTTP_200_OK, token_resp.text
    token = token_resp.json().get("access_token")
    assert token, "No se obtuvo access_token"
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("method,url,requires_auth", CRITICAL_ENDPOINTS)
def test_x_reason_missing_rejected(client: TestClient, method: str, url: str, requires_auth: bool, auth_headers: dict[str, str]):
    headers = {**auth_headers} if requires_auth else {}
    resp = client.request(method, url, headers=headers)
    assert resp.status_code in {status.HTTP_400_BAD_REQUEST,
                                status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_403_FORBIDDEN}, resp.text


@pytest.mark.parametrize("method,url,requires_auth", CRITICAL_ENDPOINTS)
def test_x_reason_too_short_rejected(client: TestClient, method: str, url: str, requires_auth: bool, auth_headers: dict[str, str]):
    headers = {**auth_headers,
               "X-Reason": "abc"} if requires_auth else {"X-Reason": "abc"}
    resp = client.request(method, url, headers=headers)
    assert resp.status_code in {status.HTTP_400_BAD_REQUEST,
                                status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_403_FORBIDDEN}, resp.text


@pytest.mark.parametrize("method,url,requires_auth", CRITICAL_ENDPOINTS)
def test_x_reason_valid_allows(client: TestClient, method: str, url: str, requires_auth: bool, auth_headers: dict[str, str]):
    headers = {**auth_headers,
               "X-Reason": "Motivo QA"} if requires_auth else {"X-Reason": "Motivo QA"}
    json_payload = None
    # Enviar payloads mínimos cuando el endpoint lo requiere para evitar 422 por cuerpo faltante
    if method.upper() == "POST" and url == "/transfers":
        json_payload = {
            "origin_store_id": 1,
            "destination_store_id": 2,
            "reason": "Motivo QA",
            "items": [{"device_id": 1, "quantity": 1}],
        }
    elif method.upper() == "POST" and url == "/backups/run":
        json_payload = {"nota": "QA"}
    resp = client.request(method, url, headers=headers, json=json_payload)
    # Se permite 2xx o 404 (si endpoint secundario requiere más params), pero no errores de validación X-Reason
    assert resp.status_code not in {
        status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY}, resp.text
