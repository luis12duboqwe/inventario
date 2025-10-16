# Bitácora de cambios

## Actualización Inventario - Movimientos de Stock
- Renombramos columnas de `inventory_movements` (`producto_id`, `tienda_origen_id`, `tienda_destino_id`, `comentario`, `usuario_id`, `fecha`) y añadimos la migración `202502150010_inventory_movements_enhancements` para preservar integridad y nuevos índices.
- El endpoint de movimientos valida la sucursal destino, impide saldos negativos y devuelve las nuevas claves en `MovementResponse` junto con el valor de inventario actualizado.
- Operaciones de compras, ventas, devoluciones, reparaciones y recepciones de transferencias recalculan el valor de inventario por sucursal y anotan origen/destino con comentarios corporativos.
- `MovementForm.tsx` y el contexto de dashboard envían `producto_id`, `tipo_movimiento`, `cantidad` y `comentario`, reutilizando el motivo como cabecera `X-Reason`.
- `build_inventory_snapshot` refleja los campos `tienda_origen_id`, `tienda_destino_id`, `comentario`, `usuario_id` y `fecha` en cada movimiento y las pruebas de backend cubren saldos negativos y la actualización contable tras una venta.

## Actualización Inventario - Catálogo de Productos (27/03/2025 23:45 UTC)
- Se añadieron los alias `costo_compra` y `precio_venta` al modelo `Device`, esquemas Pydantic y servicios CRUD para reflejar el lenguaje financiero corporativo sin romper la compatibilidad con `costo_unitario` y `unit_price`.
- `inventory_import.py` sincroniza los alias en exportaciones CSV, omite `garantia_meses` vacía y garantiza resúmenes correctos (`created=1`, `updated=1`, `skipped=0`).
- La UI de inventario muestra columnas de costo y precio de venta y permite editarlos en `DeviceEditDialog`, enviando ambos alias para mantener auditoría completa.
- Pruebas actualizadas (`backend/tests/test_catalog_pro.py`, `AdvancedSearch.test.tsx`, `InventoryPage.test.tsx`) cubren los nuevos campos y validan el flujo corregido de importación.

## Actualización Inventario - Catálogo de Productos (27/03/2025 18:00 UTC)
- Se agregaron campos descriptivos al modelo `Device` y al snapshot de inventario (`categoria`, `condicion`, `capacidad`, `estado`, `fecha_ingreso`, `ubicacion`, `descripcion`, `imagen_url`) junto con la migración `202502150009_inventory_catalog_extensions`.
- Nuevos endpoints `/inventory/stores/{store_id}/devices/export` y `/inventory/stores/{store_id}/devices/import` permiten gestionar el catálogo vía CSV con validaciones y resumen de filas creadas/actualizadas.
- La UI de inventario muestra los campos ampliados, habilita edición completa y ofrece un panel para importar/exportar el catálogo con motivo corporativo obligatorio.
- Se actualizaron las pruebas de backend y Vitest para cubrir filtros avanzados, columnas extras y el flujo de importación/exportación.
