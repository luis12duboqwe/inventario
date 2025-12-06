# Plan de Migración Fase 2 - Extraer Funciones de crud_legacy.py

**Fecha**: 2025-12-05  
**Estado**: EN PROGRESO - Módulos creados, migración pendiente  
**Riesgo**: MEDIO - Estructura preparada, migración controlada

## Resumen Ejecutivo

Fase 2 propone migrar las 50 funciones más usadas de `crud_legacy.py` (16,493 líneas, 264 funciones) a módulos especializados nuevos y existentes, reduciendo el archivo legacy a ~10K líneas.

## Análisis de Uso

### Top 50 Funciones por Frecuencia de Uso

| Rank | Función | Usos | Módulo Destino Propuesto |
|------|---------|------|--------------------------|
| 1 | get_pos_config | 10 | crud/pos.py (nuevo) |
| 2 | get_sale | 6 | crud/sales.py (existente) |
| 3 | get_store | 5 | crud/stores.py (existente) |
| 4 | get_dte_document | 3 | crud/invoicing.py (nuevo) |
| 5 | get_cash_session | 3 | crud/pos.py (nuevo) |
| 6 | create_inventory_movement | 3 | crud/inventory.py (existente) |
| 7-12 | Funciones analytics | 12 | crud/analytics.py (nuevo) |
| 13-17 | Funciones transferencias | 10 | crud/transfers.py (nuevo) |
| 18-25 | Funciones DTE/facturación | 8 | crud/invoicing.py (nuevo) |

**Total**: 50 funciones que representan ~179 usos en 31 routers

## Módulos Nuevos Propuestos

### 1. crud/pos.py - Punto de Venta
**Funciones a migrar** (15 funciones):
- `get_pos_config`, `update_pos_config`, `get_pos_config_by_store`
- `get_cash_session`, `open_cash_session`, `close_cash_session`
- `save_pos_draft`, `get_pos_draft`, `delete_pos_draft`
- `register_pos_sale`, `resolve_device_for_pos`
- `get_pos_promotions`, `update_pos_promotions`
- `trigger_cash_drawer_open`, `print_receipt`

**Dependencias**:
- sales.py (para register_pos_sale)
- inventory.py (para movimientos)
- devices.py (para resolve_device)

### 2. crud/analytics.py - Analítica y Reportes
**Funciones a migrar** (12 funciones):
- `calculate_rotation_analytics`
- `calculate_aging_analytics`
- `calculate_stockout_forecast`
- `calculate_store_comparatives`
- `calculate_profit_margin`
- `calculate_sales_projection`
- `calculate_realtime_store_widget`
- `calculate_reorder_suggestions`
- `calculate_sales_by_product_report`
- `calculate_store_sales_forecast`
- `build_cash_close_report`
- `build_sales_summary_report`

**Dependencias**:
- sales.py
- inventory.py
- stores.py

### 3. crud/transfers.py - Transferencias entre Sucursales
**Funciones a migrar** (10 funciones):
- `create_transfer_order`
- `get_transfer_order`
- `list_transfer_orders`
- `dispatch_transfer_order`
- `receive_transfer_order`
- `cancel_transfer_order`
- `get_transfer_report`
- `validate_transfer_inventory`
- `register_transfer_movement`
- `resolve_transfer_conflicts`

**Dependencias**:
- inventory.py
- stores.py

### 4. crud/invoicing.py - Facturación Electrónica (DTE)
**Funciones a migrar** (13 funciones):
- `get_dte_document`, `list_dte_documents`
- `create_dte_document`, `update_dte_document`
- `list_dte_authorizations`, `create_dte_authorization`, `update_dte_authorization`
- `list_dte_dispatch_queue`, `dispatch_dte_document`
- `get_dte_credentials`, `update_dte_credentials`
- `validate_dte_document`, `cancel_dte_document`

**Dependencias**:
- sales.py
- customers.py

## Estrategia de Migración

### Opción A: Migración Completa (RIESGOSO)
**Pros:**
- Refactorización completa inmediata
- Reduce crud_legacy.py significativamente

**Contras:**
- Alto riesgo de breaking changes
- Requiere testing extensivo
- Afecta 31 routers simultáneamente
- Difícil de revertir si algo falla

**Pasos:**
1. Crear 4 módulos nuevos con funciones migradas
2. Agregar __all__ a cada módulo nuevo
3. Mantener aliases en crud_legacy.py apuntando a nuevas ubicaciones
4. Actualizar crud/__init__.py para importar módulos nuevos
5. Testing completo (50+ tests)
6. Un solo commit grande

### Opción B: Migración Incremental (RECOMENDADO)
**Pros:**
- Riesgo controlado por módulo
- Fácil de revertir si hay problemas
- Testing incremental
- Permite validación por etapas

**Contras:**
- Requiere múltiples PRs
- Proceso más largo

**Pasos:**
1. **PR 1**: Crear crud/pos.py (15 funciones)
   - Mover funciones POS
   - Mantener aliases en crud_legacy
   - Testing: módulo POS
   
2. **PR 2**: Crear crud/analytics.py (12 funciones)
   - Mover funciones analytics
   - Mantener aliases
   - Testing: reportes y analytics

3. **PR 3**: Crear crud/transfers.py (10 funciones)
   - Mover funciones transferencias
   - Mantener aliases
   - Testing: transferencias

4. **PR 4**: Crear crud/invoicing.py (13 funciones)
   - Mover funciones DTE
   - Mantener aliases
   - Testing: facturación

5. **PR 5**: Limpiar aliases obsoletos (después de validación en producción)

### Opción C: Preparación Sin Migración (MÁS SEGURO)
**Pros:**
- Sin riesgo inmediato
- Establece estructura para futuro
- Documenta plan claramente

**Contras:**
- No reduce crud_legacy.py aún
- Trabajo de refactorización pospuesto

**Pasos:**
1. Crear módulos vacíos con docstrings y __all__ = []
2. Documentar qué funciones irían en cada módulo
3. Agregar TODOs con tracking issues
4. Actualizar documentación de arquitectura
5. Dejar migración real para PRs futuras individuales

## Patrón de Compatibilidad

Para mantener compatibilidad durante migración, usar aliases:

```python
# En crud_legacy.py después de migrar función
from .crud.pos import get_pos_config as _get_pos_config_new

def get_pos_config(*args, **kwargs):
    """DEPRECATED: Use crud.pos.get_pos_config. Alias maintained for compatibility."""
    return _get_pos_config_new(*args, **kwargs)
```

## Testing Requerido por Opción

### Opción A (Completa):
- 50+ tests funcionales
- Tests de integración para 31 routers
- Tests de regresión completos
- ~2-3 horas de ejecución

### Opción B (Incremental):
- 10-15 tests por PR
- Tests focalizados por módulo
- ~30 minutos por PR
- Total: ~2 horas distribuidas

### Opción C (Preparación):
- Tests de imports
- Tests de estructura
- ~5 minutos

## Recomendación

**Opción C (Preparación)** para esta PR, seguida de **Opción B (Incremental)** en PRs futuras.

**Razones:**
1. Esta PR ya tiene 9 commits con cambios significativos
2. Agregar migración completa aumenta riesgo
3. Permite validar Fase 1 en producción primero
4. Migración incremental es más segura y testeable
5. Cada PR puede revisarse independientemente

## Siguiente Paso Propuesto

**Para esta PR**: Implementar Opción C
- Crear 4 módulos vacíos con documentación
- Agregar plan detallado de migración
- Sin mover código aún

**Para PRs futuras**: Implementar Opción B
- Un módulo por vez
- Validación incremental
- Minimizar riesgo

## Estimación de Esfuerzo

| Opción | Tiempo | Riesgo | Commits | PRs |
|--------|--------|--------|---------|-----|
| A - Completa | 4-6 horas | Alto | 1 grande | Esta PR |
| B - Incremental | 6-8 horas | Bajo | 4-5 medianos | 4-5 PRs |
| C - Preparación | 30 minutos | Muy bajo | 1 pequeño | Esta PR |

## Decisión Requerida

¿Qué opción prefiere implementar?
- [ ] Opción A: Migración completa ahora (riesgoso)
- [ ] Opción B: Migración incremental en PRs separadas (recomendado)
- [ ] Opción C: Solo preparación en esta PR (más seguro)
