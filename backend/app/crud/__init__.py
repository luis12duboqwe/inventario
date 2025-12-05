"""CRUD operations module - Centraliza acceso a operaciones de base de datos.

NOTA DE ARQUITECTURA (2025-12-05):
Este módulo utiliza wildcard imports por razones históricas. El sistema tiene:
- 312 funciones en crud_legacy.py (16,493 líneas)
- 234 funciones únicas usadas en 31 routers
- 16 módulos CRUD especializados

MIGRACIÓN PLANIFICADA:
1. Fase actual: Wildcard imports con documentación (este archivo)
2. Fase 2 (corto plazo): Extraer funciones más usadas a módulos dedicados
3. Fase 3 (mediano plazo): Refactorizar crud_legacy.py en submódulos
4. Fase 4 (largo plazo): Eliminar wildcard imports completamente

Para agregar nuevas funciones CRUD:
- Preferir módulos especializados (users.py, devices.py, etc.)
- Evitar agregar más funciones a crud_legacy.py
- Usar imports explícitos en código nuevo

Módulos especializados disponibles:
- users: Gestión de usuarios, roles y permisos
- devices: Dispositivos e inventario básico
- stores: Sucursales y configuración
- warehouses: Almacenes y bins
- audit: Auditoría y logs
- inventory: Movimientos y valuaciones
- customers: Clientes y ledger
- sync: Sincronización híbrida
- sales: Ventas y devoluciones
- purchases: Compras y órdenes
- loyalty: Programas de lealtad
"""

# TODO: Migrar a imports explícitos. Tracking issue: [crear issue en GitHub]
# Nota: Los wildcard imports causan namespace pollution y dificultan debugging.
# Se mantienen temporalmente por compatibilidad con 31 routers existentes.

from ..crud_legacy import *  # noqa: F401,F403
from .users import *  # noqa: F401,F403
from .devices import *  # noqa: F401,F403
from .stores import *  # noqa: F401,F403
from .warehouses import *  # noqa: F401,F403
from .audit import *  # noqa: F401,F403
from .inventory import *  # noqa: F401,F403
from .customers import *  # noqa: F401,F403
from .sync import *  # noqa: F401,F403
from .sales import *  # noqa: F401,F403
from .purchases import *  # noqa: F401,F403
from .loyalty import *  # noqa: F401,F403
