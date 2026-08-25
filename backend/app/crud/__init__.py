"""CRUD operations module - Centraliza acceso a operaciones de base de datos.

NOTA DE ARQUITECTURA (2025-12-05):
Este módulo ahora utiliza imports explícitos controlados mediante __all__ en cada submódulo.
El sistema tiene:
- 312 funciones en crud_legacy.py (16,493 líneas)
- 234 funciones únicas usadas en 31 routers
- 16 módulos CRUD especializados (12 con __all__ definidos, 4 preparados)

ESTADO ACTUAL:
- ✅ Fase 1: __all__ exports agregados a 12 módulos especializados
- 🔄 Fase 2: 4 módulos nuevos creados (pos, analytics, transfers, invoicing) - preparados para migración
- ⏸️ Fase 3: Migrar funciones desde crud_legacy a módulos nuevos
- ⏸️ Fase 4: Eliminar wildcard de crud_legacy completamente

Para agregar nuevas funciones CRUD:
- Preferir módulos especializados (users.py, devices.py, etc.)
- Agregar función a __all__ del módulo correspondiente
- Evitar agregar más funciones a crud_legacy.py
- Usar imports explícitos en código nuevo

Módulos especializados con __all__ definidos (12):
- users (41 exports): Gestión de usuarios, roles y permisos
- devices (5 exports): Dispositivos e inventario básico
- stores (9 exports): Sucursales y configuración
- warehouses (4 exports): Almacenes y bins
- audit (18 exports): Auditoría y logs
- inventory (23 exports): Movimientos y valuaciones
- customers (5 exports): Clientes y ledger
- suppliers (13 exports): Proveedores y lotes de compra
- sync (2 exports): Sincronización híbrida
- sales (9 exports): Ventas y devoluciones
- purchases (21 exports): Compras y órdenes
- loyalty (8 exports): Programas de lealtad

Módulos nuevos preparados para migración (4):
- pos (0 exports): Punto de venta, caja, borradores (15 funciones planificadas)
- analytics (0 exports): Analítica, reportes, proyecciones (12 funciones planificadas)
- transfers (0 exports): Transferencias entre sucursales (10 funciones planificadas)
- invoicing (0 exports): Facturación electrónica DTE (13 funciones planificadas)
"""

# TODO: Migrar funciones desde crud_legacy.py a módulos especializados
# Nota: crud_legacy aún usa wildcard por compatibilidad con 31 routers.
# Se mantiene mientras se migran funciones a módulos especializados.
#
# Importamos legacy primero para que los módulos especializados sobrescriban
# cualquier firma obsoleta (por ejemplo list_sales/start_date, métricas).
from ..crud_legacy import *  # noqa: F401,F403

# Imports explícitos desde módulos especializados (sobrescriben legacy cuando coinciden)
# Nota: Los submódulos controlan sus exports mediante __all__
from .users import *  # noqa: F401,F403
from .devices import *  # noqa: F401,F403
from .stores import *  # noqa: F401,F403
from .warehouses import *  # noqa: F401,F403
from .audit import *  # noqa: F401,F403
from .inventory import *  # noqa: F401,F403
from .customers import *  # noqa: F401,F403
from .suppliers import *  # noqa: F401,F403
from .sync import *  # noqa: F401,F403
from .sales import *  # noqa: F401,F403
from .purchases import *  # noqa: F401,F403
from .loyalty import *  # noqa: F401,F403
from .backups import *  # noqa: F401,F403

# Módulos nuevos preparados para recibir funciones de crud_legacy
from .pos import *  # noqa: F401,F403
from .analytics import *  # noqa: F401,F403
from .transfers import *  # noqa: F401,F403
from .invoicing import *  # noqa: F401,F403
from .recovery_compat import *  # noqa: F401,F403

# Compatibilidad de recuperación REC-0004.
# El snapshot legacy intacto es anterior a varias extracciones de helpers. Esas
# extracciones sí son válidas; lo que se corrompió fueron los cuerpos comentados
# parcialmente dentro de crud_legacy.py. Reinyectamos aquí las implementaciones
# especializadas actuales para que las funciones legacy resueltas en runtime no
# dependan de imports que aún no existían en el snapshot histórico.
import math as _math
from collections import defaultdict as _defaultdict
from pathlib import Path as _Path
from .. import crud_legacy as _legacy
from . import analytics as _analytics
from .audit import log_audit_event as _legacy_log_audit_event
from .customers import (
    _create_customer_ledger_entry as _legacy_create_customer_ledger_entry,
    _ensure_debt_respects_limit as _legacy_ensure_debt_respects_limit,
    _sync_customer_ledger_entry as _legacy_sync_customer_ledger_entry,
)
from .devices import _ensure_unique_identifier_payload as _legacy_ensure_unique_identifier_payload
from .inventory import _hydrate_movement_references as _legacy_hydrate_movement_references
from .purchases import _register_purchase_status_event as _legacy_register_purchase_status_event
from ..utils.data_helpers import sync_supplier_ledger_entry as _legacy_sync_supplier_ledger_entry
from ..utils.ledger_helpers import create_supplier_ledger_entry as _legacy_create_supplier_ledger_entry
from ..utils.pos_helpers import pos_draft_payload as _legacy_pos_draft_payload

_legacy.Path = _Path
_legacy.log_audit_event = _legacy_log_audit_event
_legacy._create_customer_ledger_entry = _legacy_create_customer_ledger_entry
_legacy._ensure_debt_respects_limit = _legacy_ensure_debt_respects_limit
_legacy._sync_customer_ledger_entry = _legacy_sync_customer_ledger_entry
_legacy._ensure_unique_identifier_payload = _legacy_ensure_unique_identifier_payload
_legacy._hydrate_movement_references = _legacy_hydrate_movement_references
_legacy._register_purchase_status_event = _legacy_register_purchase_status_event
_legacy._sync_supplier_ledger_entry = _legacy_sync_supplier_ledger_entry
_legacy._create_supplier_ledger_entry = _legacy_create_supplier_ledger_entry
_legacy._pos_draft_payload = _legacy_pos_draft_payload

# El módulo analytics migrado usa estos símbolos pero la extracción no trasladó
# sus imports. Se reinyectan aquí para preservar el código actual sin duplicarlo.
_analytics.math = _math
_analytics.defaultdict = _defaultdict

# Utilidades adicionales expuestas para compatibilidad
from ..utils.system_log_helpers import purge_system_logs  # noqa: F401
