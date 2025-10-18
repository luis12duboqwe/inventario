"""Constantes y utilidades para la gestión de roles RBAC."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Final

ADMIN: Final[str] = "ADMIN"
GERENTE: Final[str] = "GERENTE"
OPERADOR: Final[str] = "OPERADOR"
INVITADO: Final[str] = "INVITADO"

DEFAULT_ROLES: Final[tuple[str, ...]] = (ADMIN, GERENTE, OPERADOR, INVITADO)
GESTION_ROLES: Final[tuple[str, ...]] = (ADMIN, GERENTE)
REPORTE_ROLES: Final[tuple[str, ...]] = (ADMIN, GERENTE)
AUDITORIA_ROLES: Final[tuple[str, ...]] = (ADMIN, GERENTE)
MOVEMENT_ROLES: Final[tuple[str, ...]] = (ADMIN, GERENTE, OPERADOR)
VALID_ROLES: Final[set[str]] = set(DEFAULT_ROLES)


def normalize_role(role_name: str) -> str:
    """Normaliza y valida un nombre de rol recibido externamente."""

    if not isinstance(role_name, str):
        raise ValueError("El nombre de rol debe ser una cadena de texto.")
    normalized = role_name.strip().upper()
    if normalized not in VALID_ROLES:
        raise ValueError(f"Rol desconocido: {role_name}")
    return normalized


def normalize_roles(role_names: Iterable[str] | None) -> set[str]:
    """Convierte una colección de roles arbitrarios a su representación estándar."""

    if role_names is None:
        return set()
    return {normalize_role(role_name) for role_name in role_names}

__all__ = [
    "ADMIN",
    "GERENTE",
    "OPERADOR",
    "INVITADO",
    "DEFAULT_ROLES",
    "GESTION_ROLES",
    "REPORTE_ROLES",
    "AUDITORIA_ROLES",
    "MOVEMENT_ROLES",
    "VALID_ROLES",
    "normalize_role",
    "normalize_roles",
]
