"""Pruebas unitarias para la dependencia require_roles."""
from __future__ import annotations

import asyncio
import types

import pytest
from fastapi import HTTPException

from backend.app.security import require_roles


class _DummyAssignment:
    def __init__(self, name: str | None = None) -> None:
        self.name = name
        self.role = types.SimpleNamespace(name=name) if name else None


class _DummyUser:
    def __init__(
        self,
        *,
        rol: str | None = None,
        assignments: list[_DummyAssignment] | None = None,
    ) -> None:
        self.rol = rol
        self.roles = assignments or []


def test_require_roles_accepts_primary_role_column() -> None:
    dependency = require_roles("GERENTE")
    user = _DummyUser(rol="gerente", assignments=[])

    result = asyncio.run(dependency(current_user=user))

    assert result is user


def test_require_roles_allows_admin_without_assignments() -> None:
    dependency = require_roles("OPERADOR")
    user = _DummyUser(rol="admin", assignments=[])

    result = asyncio.run(dependency(current_user=user))

    assert result is user


def test_require_roles_rejects_when_no_matching_role() -> None:
    dependency = require_roles("GERENTE")
    user = _DummyUser(rol="OPERADOR", assignments=[_DummyAssignment("OPERADOR")])

    with pytest.raises(HTTPException):
        asyncio.run(dependency(current_user=user))


def test_require_roles_uses_relationship_assignments() -> None:
    dependency = require_roles("OPERADOR")
    user = _DummyUser(assignments=[_DummyAssignment("operador")])

    result = asyncio.run(dependency(current_user=user))

    assert result is user
