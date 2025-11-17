"""Pruebas unitarias para la dependencia require_roles."""
from __future__ import annotations

import asyncio
import types

import pytest
from fastapi import HTTPException
from starlette.requests import Request

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
        store_id: int | None = None,
    ) -> None:
        self.rol = rol
        self.roles = assignments or []
        self.store_id = store_id


class _DummyPermission:
    def __init__(self, module: str, *, can_view: bool = False, can_edit: bool = False, can_delete: bool = False) -> None:
        self.module = module
        self.can_view = can_view
        self.can_edit = can_edit
        self.can_delete = can_delete


def _request_with_store(store_id: int, method: str = "GET") -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "method": method,
        "scheme": "http",
        "path": f"/stores/{store_id}",
        "raw_path": f"/stores/{store_id}".encode(),
        "query_string": b"",
        "headers": [],
        "client": ("test", 5000),
        "server": ("testserver", 80),
        "path_params": {"store_id": store_id},
        "app": None,
    }
    return Request(scope)


def _basic_request() -> Request:
    return _request_with_store(0)


def test_require_roles_accepts_primary_role_column() -> None:
    dependency = require_roles("GERENTE")
    user = _DummyUser(rol="gerente", assignments=[])

    result = asyncio.run(dependency(current_user=user, request=_basic_request()))

    assert result is user


def test_require_roles_allows_admin_without_assignments() -> None:
    dependency = require_roles("OPERADOR")
    user = _DummyUser(rol="admin", assignments=[])

    result = asyncio.run(dependency(current_user=user, request=_basic_request()))

    assert result is user


def test_require_roles_rejects_when_no_matching_role() -> None:
    dependency = require_roles("GERENTE")
    user = _DummyUser(rol="OPERADOR", assignments=[_DummyAssignment("OPERADOR")])

    with pytest.raises(HTTPException):
        asyncio.run(dependency(current_user=user, request=_basic_request()))


def test_require_roles_uses_relationship_assignments() -> None:
    dependency = require_roles("OPERADOR")
    user = _DummyUser(assignments=[_DummyAssignment("operador")])

    result = asyncio.run(dependency(current_user=user, request=_basic_request()))

    assert result is user


def test_require_roles_rejects_cross_store_access() -> None:
    dependency = require_roles("OPERADOR")
    user = _DummyUser(assignments=[_DummyAssignment("operador")], store_id=1)
    request = _request_with_store(2)

    with pytest.raises(HTTPException):
        asyncio.run(dependency(current_user=user, request=request))


def test_require_roles_allows_same_store_access() -> None:
    dependency = require_roles("OPERADOR")
    user = _DummyUser(assignments=[_DummyAssignment("operador")], store_id=3)
    request = _request_with_store(3)

    result = asyncio.run(dependency(current_user=user, request=request))

    assert result is user


def test_require_roles_rejects_missing_sensitive_permission() -> None:
    dependency = require_roles("OPERADOR", module="inventario", action="delete")
    role_assignment = _DummyAssignment("operador")
    role_assignment.role.permissions = [_DummyPermission("inventario", can_view=True, can_edit=True)]
    user = _DummyUser(assignments=[role_assignment])
    request = _request_with_store(1, method="DELETE")

    with pytest.raises(HTTPException):
        asyncio.run(dependency(current_user=user, request=request, db=None))


def test_require_roles_accepts_sensitive_permission() -> None:
    dependency = require_roles("OPERADOR", module="inventario", action="delete")
    role_assignment = _DummyAssignment("operador")
    role_assignment.role.permissions = [_DummyPermission("inventario", can_delete=True)]
    user = _DummyUser(assignments=[role_assignment])
    request = _request_with_store(1, method="DELETE")

    result = asyncio.run(dependency(current_user=user, request=request, db=None))

    assert result is user
