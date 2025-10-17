"""Pruebas para las utilidades de seguridad."""
from __future__ import annotations

import asyncio
from enum import Enum
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app.security import require_roles


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"


def _user_with_roles(*role_names: str) -> SimpleNamespace:
    assignments = [
        SimpleNamespace(role=SimpleNamespace(name=name)) for name in role_names
    ]
    return SimpleNamespace(roles=assignments)


def test_require_roles_accepts_legacy_lowercase_roles() -> None:
    user = _user_with_roles("admin", "operador")
    dependency = require_roles("ADMIN")

    result = asyncio.run(dependency(current_user=user))

    assert result is user


def test_require_roles_handles_lowercase_requirements() -> None:
    user = _user_with_roles("ADMIN")
    dependency = require_roles("admin")

    result = asyncio.run(dependency(current_user=user))

    assert result is user


def test_require_roles_rejects_missing_role() -> None:
    user = _user_with_roles("gerente")
    dependency = require_roles("ADMIN")

    with pytest.raises(HTTPException):
        asyncio.run(dependency(current_user=user))


def test_require_roles_accepts_enum_values() -> None:
    user = _user_with_roles("ADMIN")
    dependency = require_roles(RoleEnum.ADMIN)

    result = asyncio.run(dependency(current_user=user))

    assert result is user


def test_require_roles_rejects_invalid_arguments() -> None:
    with pytest.raises(ValueError):
        require_roles(None)
