# Bitácora de cambios

## Actualización Inventario - Ajustes y Auditorías
- Se amplía `crud.create_inventory_movement` para registrar stock previo, stock actualizado y motivo corporativo en la bitácora, vinculando el ajuste al usuario autenticado.
- Se introducen los umbrales `SOFTMOBILE_LOW_STOCK_THRESHOLD` y `SOFTMOBILE_ADJUSTMENT_VARIANCE_THRESHOLD` para disparar automáticamente los eventos `inventory_low_stock_alert` (crítica) e `inventory_adjustment_alert` (preventiva).
- `backend/app/utils/audit.py` reconoce nuevas palabras clave (`stock bajo`, `ajuste manual`, `inconsistencia`) que alimentan resúmenes y recordatorios de seguridad.
- La prueba `backend/tests/test_stores.py::test_manual_adjustment_triggers_alerts` cubre el flujo completo desde el ajuste manual hasta la generación de alertas y verificación del inventario resultante.

## Actualización Inventario - Valoraciones y Costos
- Se crea la vista `valor_inventario` a través de la migración `202503010002_inventory_valuation_view.py`, consolidando costo promedio ponderado, valores totales por sucursal y márgenes por producto y categoría.
- Se añaden métricas comparativas (`valor_costo_producto`, `valor_costo_tienda`, `valor_costo_general`, `valor_total_categoria`, `margen_total_tienda`, `margen_total_general`) para contrastar el valor de venta contra el costo y la rentabilidad acumulada.
- Se añade el servicio `calculate_inventory_valuation` y el esquema `InventoryValuation` para consultar la vista con filtros opcionales por sucursal y categoría desde el backend.
- `backend/tests/test_inventory_valuation.py` valida el cálculo de promedios ponderados, márgenes y filtros, mientras que `backend/tests/conftest.py` prepara la vista en entornos de prueba.

## Actualización Inventario - Reportes y Estadísticas (30/03/2025)
- Se amplía `reports.py` con rutas `GET /reports/inventory/current`, `/value`, `/movements` y `/top-products`, además de sus exportaciones CSV. Cada descarga exige cabecera `X-Reason` y roles de reporte.
- `crud.py` incorpora agregadores dedicados para existencias actuales, valoración consolidada, movimientos por periodo y ranking de productos más vendidos, reutilizados por los nuevos endpoints.
- `_normalize_date_range` reconoce fechas sin hora y extiende el cierre del periodo hasta las 23:59:59 para que los filtros diarios incluyan todos los movimientos registrados.
- `backend/tests/test_reports_inventory.py` cubre los nuevos reportes validando filtros, totales y contenido de los CSV generados.
- `frontend/src/api.ts` expone helpers (`getInventoryCurrentReport`, `getInventoryMovementsReport`, `downloadInventoryMovementsCsv`, etc.) consumidos por `inventoryService.ts`.
- `InventoryPage.tsx` añade el tab **Reportes** mediante `InventoryReportsPanel.tsx`, mostrando métricas y botones de exportación. `InventoryPage.test.tsx` verifica la interacción y las solicitudes de motivo corporativo.
- Se documenta que las cabeceras `X-Reason` deben enviarse en ASCII para evitar errores de codificación durante las exportaciones CSV.

## Actualización Inventario - Gestión de IMEI y Series
- Se crea la tabla `device_identifiers` (migración `202503010001_device_identifiers.py`) con los campos `producto_id`, `imei_1`, `imei_2`, `numero_serie`, `estado_tecnico` y `observaciones`, vinculada uno a uno con `devices` y con restricciones de unicidad.
- Nuevos endpoints `GET/PUT /inventory/stores/{store_id}/devices/{device_id}/identifier` permiten consultar y actualizar los identificadores extendidos exigiendo cabecera `X-Reason` y roles de gestión.
- `_ensure_unique_identifiers` y el helper `_ensure_unique_identifier_payload` bloquean cualquier IMEI/serie duplicado entre `devices` y `device_identifiers`, devolviendo el error `device_identifier_conflict` cuando existe una colisión.
- `test_device_creation_rejects_conflicts_from_identifier_table` asegura que la API impide registrar dispositivos con IMEI o número de serie presentes en `device_identifiers`, retornando `409` con el código `device_identifier_conflict`.
- Se registran auditorías `device_identifier_created` y `device_identifier_updated` incluyendo el motivo corporativo recibido para cada operación.
- El SDK web (`frontend/src/api.ts`) agrega los métodos `getDeviceIdentifier`/`upsertDeviceIdentifier` y `InventoryTable.tsx` muestra IMEI dual, número de serie extendido, estado técnico y observaciones.
- Nueva suite `backend/tests/test_device_identifiers.py` cubre el flujo de alta, consultas posteriores, conflictos de IMEI/serie y la respuesta 404 cuando un dispositivo aún no cuenta con identificadores extendidos.

## Actualización Inventario - Movimientos de Stock
- Renombramos columnas de `inventory_movements` (`producto_id`, `tienda_origen_id`, `tienda_destino_id`, `comentario`, `usuario_id`, `fecha`) y añadimos la migración `202502150010_inventory_movements_enhancements` para preservar integridad y nuevos índices.
- El endpoint de movimientos valida la sucursal destino, impide saldos negativos y devuelve las nuevas claves en `MovementResponse` junto con el valor de inventario actualizado.
- El esquema `MovementCreate` ahora exige el comentario, lo normaliza, rechaza motivos corporativos con menos de 5 caracteres y valida que coincida con la cabecera `X-Reason` en cada registro.
- El endpoint de movimientos devuelve `422` cuando el motivo difiere del encabezado `X-Reason`; la prueba `test_inventory_movement_requires_comment_matching_reason` cubre este escenario.
- Operaciones de compras, ventas, devoluciones, reparaciones y recepciones de transferencias recalculan el valor de inventario por sucursal y anotan origen/destino con comentarios corporativos.
- `MovementForm.tsx` y el contexto de dashboard envían `producto_id`, `tipo_movimiento`, `cantidad` y `comentario`, reutilizando el motivo como cabecera `X-Reason`.
- `build_inventory_snapshot` refleja los campos `tienda_origen_id`, `tienda_destino_id`, `comentario`, `usuario_id` y `fecha` en cada movimiento y las pruebas de backend cubren saldos negativos y la actualización contable tras una venta.
- Operaciones de compras, ventas, devoluciones y reparaciones anotan el origen/destino del movimiento y comentarios corporativos, sincronizando el costo promedio y el valor contable de la tienda.
- `MovementForm.tsx` y el contexto de dashboard envían `producto_id`, `tipo_movimiento`, `cantidad` y `comentario`, reutilizando el motivo como cabecera `X-Reason`.
- Las respuestas de la API incluyen `usuario`, `tienda_origen` y `tienda_destino` además de los identificadores numéricos para alinear reportes y paneles con los requerimientos corporativos.

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
