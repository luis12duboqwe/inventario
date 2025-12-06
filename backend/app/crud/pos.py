"""Operaciones CRUD para Punto de Venta (POS).

ESTADO: Preparado para migración
Este módulo está estructurado para recibir funciones POS de crud_legacy.py

Funciones a migrar (15 total):
- get_pos_config (10 usos)
- update_pos_config
- get_pos_config_by_store
- get_cash_session (3 usos)
- open_cash_session
- close_cash_session
- save_pos_draft (1 uso)
- get_pos_draft
- delete_pos_draft
- register_pos_sale
- resolve_device_for_pos (2 usos)
- get_pos_promotions
- update_pos_promotions
- trigger_cash_drawer_open
- print_receipt

Dependencias:
- crud.sales (para register_pos_sale)
- crud.inventory (para movimientos)
- crud.devices (para resolve_device)
"""

from __future__ import annotations

# TODO: Migrar funciones POS desde crud_legacy.py
# Tracking: Fase 2 - Migración incremental

__all__: list[str] = []  # Vacío hasta que se migren las funciones

# Las funciones se migrarán desde crud_legacy.py manteniendo:
# - Firmas exactas
# - Lógica completa
# - Dependencias
# - Tests asociados
