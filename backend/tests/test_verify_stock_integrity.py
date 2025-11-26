from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi import status

from backend.app.core.roles import ADMIN


def _auth_headers(client) -> dict[str, str]:
    payload = {
        "username": "admin",
        "password": "MuySegura123",
        "full_name": "Admin General",
        "roles": [ADMIN],
    }
    response = client.post("/auth/bootstrap", json=payload)
    assert response.status_code in {
        status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST}

    token_response = client.post(
        "/auth/token",
        data={"username": payload["username"],
              "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_response.status_code == status.HTTP_200_OK
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_verify_stock_integrity_script_runs(client, tmp_path) -> None:
    # Crear datos mínimos
    headers = _auth_headers(client)

    store_response = client.post(
        "/stores",
        json={"name": "Sucursal QA", "location": "CDMX",
              "timezone": "America/Mexico_City"},
        headers=headers,
    )
    assert store_response.status_code == status.HTTP_201_CREATED
    store_id = store_response.json()["id"]

    device_payload = {
        "sku": "INT-001",
        "name": "Dispositivo QA",
        "quantity": 2,
        "unit_price": 1000,
    }
    device_response = client.post(
        f"/stores/{store_id}/devices",
        json=device_payload,
        headers=headers,
    )
    assert device_response.status_code == status.HTTP_201_CREATED

    # Ejecutar el script con el mismo entorno de pruebas
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(Path.cwd()))
    env.setdefault("DATABASE_URL", "sqlite:///./test_integrity.db")
    env.setdefault("JWT_SECRET_KEY", "secret_test")
    env.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "5")
    env.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "1")
    env.setdefault("CORS_ORIGINS", "[\"http://localhost\"]")
    env.setdefault("ENABLE_BACKGROUND_SCHEDULER", "0")
    env.setdefault("TESTING_MODE", "1")

    proc = subprocess.run(
        [sys.executable, "backend/scripts/verify_stock_integrity.py"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Resumen corporativo:" in proc.stdout
    # El script debe imprimir un bloque JSON del resumen
    assert "Sucursales:" in proc.stdout
