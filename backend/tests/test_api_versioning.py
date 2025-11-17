"""Verifica la disponibilidad de rutas versionadas sin romper compatibilidad."""
from __future__ import annotations

import pytest

from backend.app.config import settings


def test_health_endpoint_available_under_versioned_prefix(light_client) -> None:
    """El endpoint de salud debe responder bajo el prefijo versionado."""

    api_prefix = settings.api_v1_prefix.strip()
    if not api_prefix or api_prefix == "/":
        pytest.skip("El prefijo de API está deshabilitado en la configuración actual.")

    normalized_prefix = api_prefix if api_prefix.startswith("/") else f"/{api_prefix}"
    response = light_client.get(f"{normalized_prefix}/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_available_under_alias_prefixes(light_client) -> None:
    """Los alias de prefijo deben continuar resolviendo el endpoint de salud."""

    normalized_aliases = []
    for alias in settings.api_alias_prefixes:
        stripped = alias.strip()
        if not stripped or stripped == "/":
            continue
        normalized_aliases.append(
            stripped if stripped.startswith("/") else f"/{stripped}"
        )

    if not normalized_aliases:
        pytest.skip("No se configuraron alias de prefijo para la API.")

    for alias_prefix in normalized_aliases:
        response = light_client.get(f"{alias_prefix}/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
