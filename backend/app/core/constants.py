"""Constantes globales del sistema Softmobile Central."""
from typing import Final
from .roles import ADMIN, GERENTE, OPERADOR, INVITADO

# Módulos de seguridad
DEFAULT_SECURITY_MODULES: Final[list[str]] = [
    "usuarios",
    "seguridad",
    "inventario",
    "precios",
    "ventas",
    "compras",
    "pos",
    "clientes",
    "proveedores",
    "reparaciones",
    "transferencias",
    "operaciones",
    "reportes",
    "auditoria",
    "sincronizacion",
    "respaldos",
    "tiendas",
    "actualizaciones",
]

# Restricciones de permisos por rol
RESTRICTED_DELETE_FOR_MANAGER: Final[set[str]] = {
    "seguridad", "respaldos", "usuarios", "actualizaciones"
}
RESTRICTED_EDIT_FOR_OPERATOR: Final[set[str]] = {
    "seguridad", "respaldos", "usuarios", "actualizaciones", "auditoria"
}
RESTRICTED_DELETE_FOR_OPERATOR: Final[set[str]] = RESTRICTED_EDIT_FOR_OPERATOR | {
    "reportes", "sincronizacion"
}

# Matriz de permisos por defecto
ROLE_MODULE_PERMISSION_MATRIX: Final[dict[str, dict[str, dict[str, bool]]]] = {
    ADMIN: {
        module: {"can_view": True, "can_edit": True, "can_delete": True}
        for module in DEFAULT_SECURITY_MODULES
    },
    GERENTE: {
        module: {
            "can_view": True,
            "can_edit": True,
            "can_delete": module not in RESTRICTED_DELETE_FOR_MANAGER,
        }
        for module in DEFAULT_SECURITY_MODULES
    },
    OPERADOR: {
        module: {
            "can_view": True,
            "can_edit": module not in RESTRICTED_EDIT_FOR_OPERATOR,
            "can_delete": module not in RESTRICTED_DELETE_FOR_OPERATOR,
        }
        for module in DEFAULT_SECURITY_MODULES
    },
    INVITADO: {
        module: {
            "can_view": module
            in {"inventario", "reportes", "clientes", "proveedores", "ventas"},
            "can_edit": False,
            "can_delete": False,
        }
        for module in DEFAULT_SECURITY_MODULES
    },
}

# Mapeo de rutas a módulos para permisos
MODULE_PERMISSION_PREFIXES: Final[tuple[tuple[str, str], ...]] = (
    ("/users", "usuarios"),
    ("/security", "seguridad"),
    ("/inventory", "inventario"),
    ("/stores", "tiendas"),
    ("/purchases", "compras"),
    ("/sales", "ventas"),
    ("/pos", "pos"),
    ("/customers", "clientes"),
    ("/payments", "ventas"),
    ("/store-credits", "clientes"),
    ("/loyalty", "lealtad"),
    ("/suppliers", "proveedores"),
    ("/repairs", "reparaciones"),
    ("/returns", "operaciones"),
    ("/transfers", "transferencias"),
    ("/operations", "operaciones"),
    ("/pricing", "precios"),
    ("/reports", "reportes"),
    ("/audit", "auditoria"),
    ("/sync", "sincronizacion"),
    ("/backups", "respaldos"),
    ("/updates", "actualizaciones"),
    ("/integrations", "integraciones"),
)
