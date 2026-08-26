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

from ..crud_legacy import *  # noqa: F401,F403

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
from .pos import *  # noqa: F401,F403
from .analytics import *  # noqa: F401,F403
from .transfers import *  # noqa: F401,F403
from .invoicing import *  # noqa: F401,F403
from .recovery_compat import *  # noqa: F401,F403

import json as _json
import math as _math
from collections import defaultdict as _defaultdict
from datetime import datetime as _datetime, timezone as _timezone
from pathlib import Path as _Path
from sqlalchemy.exc import NoResultFound as _NoResultFound
from sqlalchemy.orm import joinedload as _joinedload

from .. import crud_legacy as _legacy
from . import analytics as _analytics
from . import devices as _devices
from . import inventory as _inventory
from . import recovery_compat as _recovery_compat
from . import sales as _sales
from . import transfers as _transfers
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
from ..utils.payload_serializers import transfer_order_payload as _transfer_order_payload
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

_analytics.math = _math
_analytics.defaultdict = _defaultdict

_devices._recalculate_sale_price = _recovery_compat._recalculate_sale_price
_sales.release_reservation = _recovery_compat.release_reservation

_transfers._require_store_permission = _legacy._require_store_permission
_transfers._user_can_override_transfer = _legacy._user_can_override_transfer
_transfers.expire_reservations = _inventory.expire_reservations
_transfers.get_inventory_reservation = _inventory.get_inventory_reservation
_transfers.datetime = _datetime
_transfers.timezone = _timezone
_transfers._log_action = _legacy._log_action
_transfers.json = _json
_transfers.enqueue_sync_outbox = _legacy.enqueue_sync_outbox
_transfers.transfer_order_payload = _transfer_order_payload
_transfers.joinedload = _joinedload
_transfers.NoResultFound = _NoResultFound
_transfers._apply_transfer_dispatch = _legacy._apply_transfer_dispatch
_transfers._normalize_reception_quantities = _legacy._normalize_reception_quantities
_transfers._apply_transfer_reception = _legacy._apply_transfer_reception

from ..utils.system_log_helpers import purge_system_logs  # noqa: F401
