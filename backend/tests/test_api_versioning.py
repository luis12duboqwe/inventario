"""Verifica la disponibilidad de rutas versionadas sin romper compatibilidad."""
from __future__ import annotations

import pytest

from backend.app.config import settings


def test_health_endpoint_available_under_versioned_prefix(client) -> None:
    """El endpoint de salud debe responder bajo el prefijo versionado."""

    api_prefix = settings.api_v1_prefix.strip()
    if not api_prefix or api_prefix == "/":
        pytest.skip("El prefijo de API está deshabilitado en la configuración actual.")

    normalized_prefix = api_prefix if api_prefix.startswith("/") else f"/{api_prefix}"
    response = client.get(f"{normalized_prefix}/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
