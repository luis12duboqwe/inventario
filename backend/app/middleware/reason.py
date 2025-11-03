"""Validaciones de cabecera corporativa `X-Reason`.

Este módulo centraliza las reglas de endurecimiento para garantizar que todas
las rutas sensibles exijan y normalicen el motivo corporativo sin duplicar
lógica en los middlewares.
"""

from __future__ import annotations

import re

SENSITIVE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})
SENSITIVE_PREFIXES: tuple[str, ...] = (
    "/inventory",
    "/purchases",
    "/sales",
    "/pos",
    "/backups",
    "/customers",
    "/reports",
    "/payments",
    "/suppliers",
    "/repairs",
    "/transfers",
    "/security",
    "/sync/outbox",
    "/operations",
)
READ_SENSITIVE_PREFIXES: tuple[str, ...] = ("/pos", "/reports", "/customers")

_MAX_REASON_LENGTH = 200
_INVALID_REASON_PATTERN = re.compile(r"[\r\n\t]")


class ReasonHeaderError(ValueError):
    """Error de validación del encabezado corporativo."""


def requires_reason_header(method: str, path: str) -> bool:
    """Determina si la solicitud requiere `X-Reason`.

    El objetivo es reutilizar la misma lógica entre middlewares y pruebas.
    """

    method_upper = method.upper()
    if method_upper in SENSITIVE_METHODS:
        return any(path.startswith(prefix) for prefix in SENSITIVE_PREFIXES)
    if method_upper == "GET":
        return any(path.startswith(prefix) for prefix in READ_SENSITIVE_PREFIXES)
    return False


def _validate_length(reason: str) -> None:
    if len(reason) < 5:
        raise ReasonHeaderError(
            "Proporciona el encabezado X-Reason con al menos 5 caracteres."
        )
    if len(reason) > _MAX_REASON_LENGTH:
        raise ReasonHeaderError(
            "El encabezado X-Reason no puede exceder 200 caracteres."
        )


def _validate_content(reason: str) -> None:
    if _INVALID_REASON_PATTERN.search(reason):
        raise ReasonHeaderError(
            "El encabezado X-Reason no debe contener saltos de línea ni tabulaciones."
        )
    if not any(char.isalnum() for char in reason):
        raise ReasonHeaderError(
            "El encabezado X-Reason debe incluir caracteres alfanuméricos descriptivos."
        )
    if any(ord(char) < 32 for char in reason):
        raise ReasonHeaderError(
            "El encabezado X-Reason contiene caracteres de control no permitidos."
        )


def ensure_reason_header(header_value: str | None) -> str:
    """Valida y normaliza el valor recibido en `X-Reason`.

    Devuelve la cadena saneada lista para registrarse en los `request.state`
    que consumen el motivo corporativo.
    """

    if header_value is None:
        raise ReasonHeaderError(
            "Proporciona el encabezado X-Reason con al menos 5 caracteres."
        )
    sanitized = header_value.strip()
    _validate_length(sanitized)
    _validate_content(sanitized)
    return sanitized
