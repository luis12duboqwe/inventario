# Bitácora de cambios

## Verificación Global - Módulo de Inventario Softmobile 2025 v2.2.0 (17/10/2025 05:41 UTC)
- Validación corporativa sin incidencias que abarca catálogo avanzado, movimientos y alertas, gestión de IMEI y series, valuaciones financieras, reportes multiformato, roles RBAC e interfaz visual del inventario.
- Se confirmaron integraciones entre movimientos → productos → reportes → alertas mediante la suite `pytest` y las pruebas de frontend (Vitest), garantizando cálculos y referencias coherentes.
- Se verificó la disponibilidad de dependencias críticas de reportes (`openpyxl`) previo a la ejecución de pruebas para evitar fallos de importación.
- Recomendación: abordar las advertencias de `act(...)` en pruebas React en una iteración futura para mejorar la estabilidad de la suite de frontend.

## Actualización Compras - Parte 1 (Estructura y Relaciones) (17/10/2025 10:15 UTC)
- Se formalizan las tablas `proveedores`, `compras` y `detalle_compras` con las columnas requeridas (`id_proveedor`, `nombre`, `telefono`, `correo`, `direccion`, `tipo`, `estado`, `notas`, `id_compra`, `proveedor_id`, `usuario_id`, `fecha`, `total`, `impuesto`, `forma_pago`, `estado`, `id_detalle`, `compra_id`, `producto_id`, `cantidad`, `costo_unitario`, `subtotal`).
- La migración `202502150011_compras_estructura_relaciones.py` crea o ajusta estructuras faltantes, reforzando las claves foráneas `compras → proveedores`, `compras → users`, `detalle_compras → compras` y `detalle_compras → devices` con índices dedicados.
- Nuevos modelos ORM (`Proveedor`, `Compra`, `DetalleCompra`) y la prueba `backend/tests/test_compras_schema.py` validan tipos, índices y relaciones para prevenir regresiones en el módulo clásico de compras.
- **17/10/2025 10:45 UTC** — Revalidación periódica mediante `inspect(engine)` confirma que los tipos numéricos/fecha se conservan, que las claves foráneas aplican `RESTRICT`/`CASCADE` según lo previsto y que los índices `ix_proveedores_nombre`, `ix_compras_proveedor_id`, `ix_compras_usuario_id`, `ix_detalle_compras_compra_id` e `ix_detalle_compras_producto_id` permanecen activos.

## Actualización Compras - Parte 2 (Lógica e Integración con Inventario) (17/10/2025 11:30 UTC)
- Las recepciones de órdenes generan movimientos `entrada` en `inventory_movements` con comentarios que incluyen proveedor, motivo corporativo e identificadores IMEI/serie, garantizando trazabilidad junto al usuario responsable (`performed_by_id`).
- La cancelación de una orden revierte las unidades recibidas mediante movimientos `salida`, recalcula el costo promedio ponderado y registra los artículos revertidos en la auditoría.
- Las devoluciones al proveedor ajustan el stock y el costo ponderado antes de crear el movimiento, manteniendo sincronizado el valor del inventario por tienda.
- `backend/tests/test_purchases.py` agrega casos de recepción, devolución y cancelación para asegurar que stock, costos y movimientos se actualicen conforme a la política corporativa.
- Se publica la vista `movimientos_inventario` para reflejar `inventory_movements` y conservar compatibilidad con reportes y consultas históricas basadas en la nomenclatura en español.

## Actualización Compras - Parte 3 (Interfaz y Reportes) (17/10/2025 12:15 UTC)
- El módulo de Operaciones recibe un formulario de registro directo de compras con cálculo automático de subtotal, impuestos y total, validaciones de proveedor/producto y motivo corporativo antes de invocar `POST /purchases/records`.
- Se añade un historial corporativo con filtros por proveedor, usuario, fechas, estado y búsqueda libre, junto con exportaciones PDF y Excel que consumen `/purchases/records/export/{pdf|xlsx}` y respetan la cabecera `X-Reason`.
- Se publica un panel administrativo de proveedores que permite alta/edición, activación o desactivación y exportación CSV, además de un historial filtrable que consume `/purchases/vendors/{id}/history` para auditar desempeño y totales.
- El dashboard presenta métricas de compras totales, impuestos, ranking de proveedores/usuarios y acumulados mensuales mediante `GET /purchases/statistics`, alineando la UI con los servicios del backend.
- README, AGENTS y este CHANGELOG documentan la iteración bajo «Actualización Compras - Parte 3 (Interfaz y Reportes)» para preservar la trazabilidad corporativa.
- Referencia cruzada: la UI está centralizada en `frontend/src/modules/operations/components/Purchases.tsx` y depende de `backend/app/routers/purchases.py`; la prueba `backend/tests/test_purchases.py::test_purchase_records_and_vendor_statistics` confirma exportaciones PDF/Excel, filtros y métricas activas.

## Actualización Ventas - Parte 1 (Estructura y Relaciones) (17/10/2025 06:25 UTC)
- Tablas de ventas renombradas a `ventas` y `detalle_ventas` con columnas alineadas a la nomenclatura corporativa (`id_venta`, `cliente_id`, `usuario_id`, `fecha`, `forma_pago`, `impuesto`, `total`, `estado`, `venta_id`, `producto_id`, `precio_unitario`, `subtotal`).
- Migración `202503010003_sales_ventas_structure.py` garantiza claves foráneas activas hacia clientes, usuarios, ventas y dispositivos, creando índices solo cuando faltan en despliegues anteriores.
- Modelos ORM, esquemas Pydantic y flujo de creación de ventas incorporan el nuevo estado normalizado, preservando cálculos existentes de subtotal, impuesto y total.

## Actualización Ventas - Parte 2 (Lógica Funcional e Integración con Inventario) (17/10/2025 06:54 UTC)
- Se consolidó la integración entre ventas y movimientos de inventario registrando salidas `OUT`, descontando stock y marcando los dispositivos con IMEI/serie como `vendido` para impedir reprocesos.
- Las devoluciones, cancelaciones y ediciones de ventas generan entradas `IN`, restauran el estado `disponible` y recalculan el valor del inventario por sucursal de forma automática.
- Se añadieron los endpoints `PUT /sales/{id}` y `POST /sales/{id}/cancel` para editar o anular ventas con validaciones de stock, actualización de deudas a crédito y registro en `sync_outbox`.
- `backend/tests/test_sales.py` incorpora casos con múltiples productos, dispositivos identificados por IMEI, ediciones y anulaciones asegurando la coherencia entre ventas e inventario.

## Actualización Ventas - Parte 3 (Interfaz y Reportes) (17/10/2025 07:45 UTC)
- La interfaz de ventas ahora incluye carrito multiartículo con búsqueda por IMEI/SKU/modelo, selección de clientes y cálculo automático de subtotal, impuestos y total conforme a la configuración POS.
- Se añadieron filtros por fecha, cliente, usuario y texto libre en el listado de ventas, además de exportaciones PDF y Excel con motivo corporativo obligatorio y estilo oscuro corporativo.
- Nuevos endpoints `/sales/export/pdf|xlsx` y mejoras en `GET /sales` permiten generar reportes con totales y estadísticas diarias reutilizando los servicios centralizados de reportes.
- `backend/tests/test_sales.py` valida filtros y exportaciones para asegurar la integridad de datos y el uso correcto del encabezado `X-Reason`.
- **17/10/2025 08:30 UTC** — Se corrigió la asociación del botón "Guardar venta" con el formulario principal, evitando envíos nulos, y se agregaron estilos responsive/oscuros para tablas, totales y acciones del módulo de ventas.
- **17/10/2025 09:15 UTC** — Se añadieron tarjetas de ticket promedio y estadísticas diarias con promedios calculados, además de estilos oscuros reforzados (`metric-secondary`, `metric-primary`) para resaltar totales, impuestos y métricas del dashboard de ventas.

## Actualización Clientes - Parte 1 (Estructura y Relaciones) (17/10/2025 13:45 UTC)
- La migración `202503010005_clientes_estructura_relaciones.py` renombra `customers` a `clientes`, homologa columnas (`id_cliente`, `nombre`, `telefono`, `correo`, `direccion`, `tipo`, `estado`, `limite_credito`, `saldo`, `notas`) y vuelve obligatorio el teléfono, además de crear índices `ix_clientes_*` y la restricción `uq_clientes_correo`.
- Se actualizan las claves foráneas de `ventas.cliente_id` y `repair_orders.customer_id` para apuntar a `clientes.id_cliente`, preservando la asociación de facturas POS y órdenes de reparación con su cliente.
- Los esquemas FastAPI exigen teléfono, exponen tipo/estado/límite de crédito y normalizan saldos; `crud.py` amplía la exportación CSV y la prueba `backend/tests/test_clientes_schema.py` valida columnas, índices y relaciones.
- `frontend/src/modules/operations/components/Customers.tsx` incorpora selectores de tipo y estado, captura el límite de crédito y muestra los nuevos campos en la tabla, manteniendo la solicitud de motivo corporativo en altas, ediciones, notas y ajustes de saldo.
- **19/10/2025 14:30 UTC** — Revisión de integridad confirma que `limite_credito` y `saldo` permanecen no nulos, se documenta el índice `ix_ventas_cliente_id` y se refuerza `test_pos_sale_with_receipt_and_config` para exigir `customer_id` en ventas POS, garantizando que los recibos PDF muestren al cliente enlazado.
- **20/10/2025 11:30 UTC** — Se comprueba el `ondelete=SET NULL` de las claves foráneas hacia `clientes` y la prueba `test_factura_se_vincula_con_cliente` asegura que las facturas almacenadas mantienen el vínculo activo con el cliente asociado.
- **21/10/2025 09:00 UTC** — Se corrige la importación de `Decimal` y se amplían las pruebas de índices en `backend/tests/test_clientes_schema.py`, mientras que el modelo `Customer` marca `tipo` y `estado` como campos indexados para reforzar filtros y controles de crédito vinculados a las ventas.

## Actualización Clientes - Parte 2 (Lógica Funcional y Control) (20/10/2025 15:20 UTC)
- Nueva migración `202503010006_customer_ledger_entries.py` que incorpora la tabla `customer_ledger_entries`, enum de tipo de movimiento y sincronización automática vía `sync_outbox`.
- El backend suma `/customers/{id}/notes`, `/customers/{id}/payments` y `/customers/{id}/summary`; cada endpoint exige motivo corporativo, actualiza historial/ledger y ofrece un resumen financiero con ventas, facturas, pagos y movimientos recientes.
- Las ventas a crédito verifican el límite disponible antes de confirmarse, registran cargos y ajustes en la bitácora al crear/editar/cancelar/devolver y reducen saldos al aplicar pagos.
- Se normalizan `status` y `customer_type`, se rechazan límites de crédito o saldos negativos y cada entrada del ledger se serializa mediante `_customer_ledger_payload` para sincronizarse en `sync_outbox`.
- `frontend/src/modules/operations/components/Customers.tsx` permite registrar pagos, consultar un resumen financiero interactivo, añadir estados `moroso`/`vip` y gestionar notas dedicadas; el POS advierte cuando la venta agotará o excederá el crédito.
- Se renombra el campo `metadata` a `details` en las respuestas del ledger y en los consumidores de frontend para prevenir fallos de serialización detectados en las pruebas al consumir `/customers/{id}/summary`.
- Pruebas nuevas (`test_customer_credit_limit_blocks_sale`, `test_customer_payments_and_summary`) validan el bloqueo de ventas por sobreendeudamiento y que el resumen exponga ventas, facturas, pagos y notas con saldos consistentes tras registrar abonos.
- Corrección 22/10/2025 09:40 UTC: se serializa correctamente el campo `created_by` en las respuestas de pagos y se asocian las devoluciones POS a la persona que procesa cada asiento en el ledger, evitando errores `ResponseValidationError` en `/customers/{id}/payments`.
- Ajuste 23/10/2025 10:05 UTC: las rutas `/sales` y `/pos/sale` devuelven `409 Conflict` cuando la venta a crédito excede el límite aprobado y la prueba `test_credit_sale_rejected_when_limit_exceeded` garantiza que el inventario permanezca intacto tras el bloqueo.
- Mejora 24/10/2025 08:10 UTC: los ajustes manuales de saldo hechos desde `PUT /customers/{id}` generan asientos `adjustment` con detalle de saldo previo/posterior, se anexan al historial y quedan cubiertos por la prueba `test_customer_manual_debt_adjustment_creates_ledger_entry`.
- Validación 25/10/2025 11:05 UTC: se impide crear o actualizar clientes con deudas superiores a su límite de crédito, devolviendo `422` y mensaje descriptivo; la prueba `test_customer_debt_cannot_exceed_credit_limit` asegura la regla y mantiene congruente el control financiero.
- Refinamiento 26/10/2025 09:15 UTC: el listado de clientes acepta filtros explícitos por `status_filter` y `customer_type_filter`, sincronizados con la UI (`Customers.tsx`) para aislar rápidamente clientes morosos, VIP o corporativos; la prueba `test_customer_list_filters_by_status_and_type` respalda el comportamiento.

## Actualización Clientes - Parte 3 (Interfaz y Reportes) (26/10/2025 12:00 UTC)
- `frontend/src/modules/operations/components/Customers.tsx` se reorganiza en paneles oscuros: formulario, listado con búsqueda diferida y filtros combinados, perfil financiero con ventas/pagos/ledger, portafolio exportable y dashboard con barras y anillo de morosidad.
- `backend/app/routers/customers.py` incorpora `/customers/dashboard` para servir métricas consolidadas y extiende `/customers` con filtros `status`, `customer_type` y `has_debt` sin romper compatibilidad previa.
- `backend/app/routers/reports.py` añade `/reports/customers/portfolio` con entregas JSON/PDF/Excel protegidas por motivo corporativo, apoyándose en `backend/app/services/customer_reports.py` para aplicar estilos oscuros y consistentes.
- Nuevos modelos en `backend/app/schemas/__init__.py` describen portafolios, totales y rankings; `backend/app/crud.py` incorpora `build_customer_portfolio` y `get_customer_dashboard_metrics` para centralizar cálculos.
- `frontend/src/api.ts` actualiza `listCustomers` y `exportCustomersCsv` para aceptar filtros extendidos (`status`, `customer_type`, `has_debt`, `status_filter`, `customer_type_filter`) utilizados por POS, reparaciones y el nuevo listado.
- `backend/tests/test_customers.py` agrega escenarios de filtros, métricas y exportaciones (`test_customer_filters_and_reports`, `test_customer_portfolio_exports`) que validan cabeceras `X-Reason`, formatos PDF/Excel y coherencia del dashboard.

## Actualización Inventario - Roles y Permisos
- `require_roles` ahora concede acceso automático a quienes poseen el rol `ADMIN`, garantizando control total sobre rutas protegidas sin necesidad de enlistar el rol explícitamente en cada dependencia.
- Se actualizan `REPORTE_ROLES` y `AUDITORIA_ROLES` para limitar consultas de inventario, reportes y bitácoras a usuarios `ADMIN` y `GERENTE`, alineando la visibilidad con la jerarquía corporativa.
- Se introduce `MOVEMENT_ROLES` (ADMIN, GERENTE, OPERADOR) y se asigna al registro de movimientos de inventario, habilitando a operadores únicamente para capturar entradas/salidas sin exponer listados o reportes.
- Nuevas pruebas en `backend/tests/test_stores.py` validan que los operadores puedan registrar movimientos pero reciban `403` al consultar `/inventory/summary` o `/stores/{store_id}/devices`.

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
- Se amplía `reports.py` con rutas `GET /reports/inventory/current`, `/value`, `/movements` y `/top-products`, además de sus exportaciones CSV, PDF y Excel. Cada descarga exige cabecera `X-Reason` y roles de reporte.
- Se añade `GET /reports/inventory/current/{csv|pdf|xlsx}` para exportar existencias actuales por sucursal con totales de dispositivos, unidades y valor consolidado, reutilizado por el frontend mediante nuevas acciones "CSV", "PDF" y "Excel".
- `crud.py` incorpora agregadores dedicados para existencias actuales, valoración consolidada, movimientos por periodo y ranking de productos más vendidos, reutilizados por los nuevos endpoints.
- `_normalize_date_range` reconoce fechas sin hora y extiende el cierre del periodo hasta las 23:59:59 para que los filtros diarios incluyan todos los movimientos registrados.
- `backend/tests/test_reports_inventory.py` cubre los nuevos reportes validando filtros, totales y contenido de los CSV/PDF/Excel generados.
- Se refuerzan las validaciones automatizadas para impedir descargas CSV/PDF/Excel sin cabecera `X-Reason`, manteniendo los controles corporativos.
- `frontend/src/api.ts` expone helpers (`getInventoryCurrentReport`, `getInventoryMovementsReport`, `downloadInventoryMovements{Csv|Pdf|Xlsx}`, etc.) consumidos por `inventoryService.ts`.
- `InventoryPage.tsx` añade el tab **Reportes** mediante `InventoryReportsPanel.tsx`, mostrando métricas y botones de exportación multiformato. `InventoryPage.test.tsx` verifica la interacción y las solicitudes de motivo corporativo.
- Se agrega la dependencia `openpyxl` para construir archivos Excel con estilos corporativos en los reportes de inventario.
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
