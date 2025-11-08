"""Pruebas E2E del flujo de importación de inventario."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterator

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

# Configuración mínima del entorno para reutilizar la aplicación del backend
sys.path.append(str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("CORS_ORIGINS", "[\"http://testserver\"]")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("SOFTMOBILE_BOOTSTRAP_TOKEN", "test-bootstrap-token")

from backend.app.config import settings
from backend.app.core.roles import ADMIN
from backend.app.database import Base, create_engine_from_url, get_db
from backend.app.db.movimientos_inventario_view import (
    create_movimientos_inventario_view,
    drop_movimientos_inventario_view,
)
from backend.app.db.valor_inventario_view import (
    create_valor_inventario_view,
    drop_valor_inventario_view,
)
from backend.app.main import create_app


@pytest.fixture()
def db_engine() -> Iterator:
    test_url = os.getenv("SOFTMOBILE_TEST_DATABASE", "sqlite:///:memory:")
    engine = create_engine_from_url(test_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Iterator[Session]:
    Base.metadata.create_all(bind=db_engine)
    with db_engine.connect() as setup_connection:
        create_valor_inventario_view(setup_connection)
        create_movimientos_inventario_view(setup_connection)

    connection = db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autocommit=False, autoflush=False, future=True)
    session = session_factory()
    try:
        yield session
    finally:
        if session.is_active:
            session.rollback()
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        with db_engine.connect() as cleanup_connection:
            drop_movimientos_inventario_view(cleanup_connection)
            drop_valor_inventario_view(cleanup_connection)
        Base.metadata.drop_all(bind=db_engine)


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    settings.enable_background_scheduler = False
    settings.enable_backup_scheduler = False

    app = create_app()

    def override_get_db() -> Iterator[Session]:
        try:
            yield db_session
        finally:
            db_session.expunge_all()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        if settings.bootstrap_token:
            test_client.headers.update({"X-Bootstrap-Token": settings.bootstrap_token})
        yield test_client

    app.dependency_overrides.clear()


def _auth_headers(client: TestClient) -> dict[str, str]:
    payload = {
        "username": "inventario_import",
        "password": "ClaveSegura123",
        "full_name": "Inventario Import",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    token = token_response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Reason": "Carga de inventario de prueba",
    }


def test_inventory_import_invalid_quantity_returns_csv_error(client: TestClient) -> None:
    headers = _auth_headers(client)

    store_resp = client.post(
        "/stores",
        json={"name": "Sucursal Import", "location": "MX", "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_resp.status_code == status.HTTP_201_CREATED
    store_id = store_resp.json()["id"]

    csv_content = "sku,name,quantity,unit_price\nSKU-ERR,Dispositivo prueba,-5,1200\n"
    response = client.post(
        f"/inventory/stores/{store_id}/devices/import",
        files={"file": ("inventario.csv", csv_content, "text/csv")},
        headers=headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    payload = response.json()
    assert payload["detail"]["code"] == "csv_import_error"
    assert payload["detail"].get("errors")
    first_error = payload["detail"]["errors"][0]
    assert first_error["row"] == 2
    assert isinstance(first_error["message"], str) and first_error["message"]
