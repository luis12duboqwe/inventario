"""Pruebas unitarias para las utilidades de roles RBAC."""
from __future__ import annotations

import pytest

from backend.app.core import roles


def test_normalize_role_accepts_variants() -> None:
    assert roles.normalize_role(" admin ") == roles.ADMIN
    assert roles.normalize_role("gerente") == roles.GERENTE
    assert roles.normalize_role("Operador") == roles.OPERADOR


def test_normalize_role_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        roles.normalize_role("guest")


def test_normalize_roles_handles_iterables() -> None:
    normalized = roles.normalize_roles(["admin", "operador", "operador"])
    assert normalized == {roles.ADMIN, roles.OPERADOR}


def test_normalize_roles_with_none() -> None:
    assert roles.normalize_roles(None) == set()
