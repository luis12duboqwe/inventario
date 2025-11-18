"""Control de acceso básico para routers internos."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from fastapi import Depends, HTTPException, status

from .security import get_current_user

ALLOWED_ROLES: set[str] = {"ADMIN", "GERENTE", "OPERADOR", "INVITADO"}


def _extract_roles(user: Any) -> set[str]:
    """Obtiene el conjunto de roles asociados al usuario."""

    roles: set[str] = set()

    simple_role = getattr(user, "rol", None) or getattr(user, "role", None)
    if simple_role:
        roles.add(str(simple_role).upper())

    assignments: Iterable[Any] | None = getattr(user, "roles", None)
    if assignments:
        for assignment in assignments:
            assignment_role = getattr(assignment, "role", None)
            role_name = getattr(assignment_role, "name", None)
            if role_name:
                roles.add(str(role_name).upper())
                continue
            fallback_name = getattr(assignment, "name", None)
            if fallback_name:
                roles.add(str(fallback_name).upper())

    if not roles:
        roles.add("INVITADO")

    return roles


def require_roles(*roles: str) -> Callable[[Any], Any]:
    """Genera una dependencia que valida el rol del usuario autenticado."""

    allowed = {role.upper() for role in roles} if roles else ALLOWED_ROLES

    def _dependency(user: Any = Depends(get_current_user)) -> Any:
        user_roles = _extract_roles(user)
        if allowed and user_roles.isdisjoint(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No autorizado para esta operación",
            )
        return user

    return _dependency
