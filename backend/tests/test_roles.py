"""Pruebas para la normalización de roles RBAC."""
from __future__ import annotations

import pytest

from backend.app.core.roles import (
    ADMIN,
    GERENTE,
    OPERADOR,
    normalize_role,
    normalize_roles,
)


def test_normalize_role_accepts_legacy_aliases() -> None:
    """Las entradas históricas deben mapearse a los roles oficiales."""

    assert normalize_role("admin") == ADMIN
    assert normalize_role("manager") == GERENTE
    assert normalize_role("auditor") == OPERADOR


def test_normalize_roles_deduplicates_aliases() -> None:
    """Las colecciones deben resolver alias y evitar duplicados."""

    normalized = normalize_roles({"manager", "GERENTE", "auditor"})
    assert normalized == {GERENTE, OPERADOR}


def test_normalize_role_rejects_unknown_values() -> None:
    """Se debe notificar cuando el rol no existe."""

    with pytest.raises(ValueError):
        normalize_role("inventado")
