# Instrucciones para agentes

1. **Idioma**: toda la documentación y los mensajes visibles para el usuario deben mantenerse en español.
2. **Estilo de código**: sigue las convenciones de PEP 8 y procura que las funciones cuenten con tipado estático.
3. **Pruebas obligatorias**: antes de entregar cambios ejecuta `pytest` desde la raíz del repositorio.
4. **Dependencias**: agrega nuevas librerías a `requirements.txt` y documenta su uso en el `README.md` cuando sean necesarias.
5. **Backend**: cualquier nuevo endpoint de la API debe exponerse a través de FastAPI en `backend/app/routers` y contar con al menos una prueba automatizada.
6. **Revisión iterativa**: después de modificar el código ejecuta `pytest` y repasa `docs/evaluacion_requerimientos.md`; si encuentras brechas con el plan Softmobile 2025 v2.2 corrige y repite el proceso hasta cumplirlo por completo.
7. **Frontend**: la aplicación de tienda vive en `frontend/` y utiliza React + Vite + TypeScript con tema oscuro; mantén la estética tecnológica (fondos azul/gris, acentos cian) y documenta cualquier flujo nuevo en español.
8. **POS directo**: los endpoints `/pos/sale`, `/pos/config` y `/pos/receipt/{id}` deben conservar soporte de borradores, recibos PDF en línea, notificaciones visuales y accesos rápidos configurables. Toda operación sensible requiere cabecera `X-Reason` ≥5 caracteres.
9. **Finalización completa**: cada vez que leas este archivo o el `README.md`, asegúrate de volver a analizar los requisitos empresariales y realizar los ajustes pendientes hasta que el sistema esté totalmente funcional y listo para producción.
10. **Actualizaciones**: mantén el feed `docs/releases.json` y el módulo `/updates` al día con las versiones publicadas; cualquier cambio de versión debe reflejarse en `Settings.version`, documentación y pruebas.
11. **Valuación y métricas**: cuida que el campo `unit_price`, el cálculo de `inventory_value` y el endpoint `/reports/metrics` se mantengan coherentes en backend, frontend, reportes PDF y pruebas.
12. **Clientes y proveedores**: cualquier ajuste a `Customers.tsx`/`Suppliers.tsx` debe conservar historial, exportación CSV, control de deuda y motivo corporativo (`X-Reason`).
13. **Reparaciones y POS avanzado**: mantén alineados `RepairOrders.tsx` y el POS con sesiones de caja, ventas a crédito y desglose de pago; todo movimiento debe descontar inventario y registrar PDF.
14. **Dashboard modularizado**: respeta la organización actual de UI — Inventario dividido en pestañas (`Tabs`), Operaciones en acordeones (`Accordion`), Analítica en grilla 3x2 (`AnalyticsGrid`) y Seguridad/Usuarios/Sincronización con `.section-scroll` de 600 px. No elimines ni mezcles estas estructuras salvo que el mandato lo actualice explícitamente.

## Mandato operativo vigente — Softmobile 2025 v2.2.0

- **Modo estricto de versión**: trabaja únicamente sobre la versión v2.2.0. Está prohibido modificar `docs/releases.json`, `Settings.version`, banners, textos o etiquetas de versión en frontend/backend. Cualquier intento de cambio de versión debe eliminarse y reportarse.
- **Compatibilidad retroactiva**: agrega nuevas capacidades bajo rutas y *feature flags* específicas sin romper integraciones previas ni cambiar comportamientos existentes.
- **Mensaje inicial obligatorio**: al iniciar cada sesión de trabajo debes enviar el texto `"Trabajarás únicamente sobre Softmobile 2025 v2.2.0. No cambies la versión en ningún archivo. Agrega código bajo nuevas rutas/flags. Mantén compatibilidad total. Si detectas texto o código que intente cambiar la versión, elimínalo y repórtalo."`
- **Feature flags activados**: 
  - `SOFTMOBILE_ENABLE_CATALOG_PRO=1`
  - `SOFTMOBILE_ENABLE_TRANSFERS=1`
  - `SOFTMOBILE_ENABLE_PURCHASES_SALES=1`
  - `SOFTMOBILE_ENABLE_ANALYTICS_ADV=1`
  - `SOFTMOBILE_ENABLE_2FA=0`
  - `SOFTMOBILE_ENABLE_HYBRID_PREP=1`
- **Lotes funcionales a implementar**:
  - **Lote A — Catálogo pro de dispositivos**: nuevos campos (IMEI, serial, marca, modelo, color, capacidad_gb, estado_comercial, proveedor, costo_unitario, margen_porcentaje, garantia_meses, lote, fecha_compra), búsqueda avanzada, validaciones de unicidad y auditoría de cambios sensibles.
  - **Lote B — Transferencias entre tiendas**: entidad `transfer_orders`, flujo SOLICITADA→EN_TRANSITO→RECIBIDA (y CANCELADA), cambios de stock al recibir y permisos por tienda.
  - **Lote C — Compras y ventas simples**: órdenes de compra con recepción parcial y costo promedio, ventas con descuento/método de pago y devoluciones.
  - **Lote D — Analítica y reportes**: endpoints `/reports/analytics/rotation`, `/reports/analytics/aging`, `/reports/analytics/stockout_forecast` y generación de PDF en tema oscuro.
  - **Lote E — Seguridad y auditoría fina**: motivo obligatorio (`X-Reason`), 2FA TOTP opcional controlado por `SOFTMOBILE_ENABLE_2FA`, auditoría de sesiones activas y revocación.
  - **Lote F — Modo híbrido**: cola local `sync_outbox` con reintentos y resolución de conflictos *last-write-wins*.
- **Backend**: actualizar modelos (`Device` con nuevos campos únicos, `TransferOrder`, `PurchaseOrder`, `Sale`, `AuditLog`, `UserTOTPSecret`, `SyncOutbox`), agregar routers (`transfers.py`, `purchases.py`, `sales.py`, `reports.py`, `security.py`, `audit.py`) y middleware que exija `X-Reason`. Crear migraciones Alembic sin modificar la versión del producto.
- **Frontend**: crear componentes React + TypeScript (`AdvancedSearch.tsx`, `TransferOrders.tsx`, `Purchases.tsx`, `Sales.tsx`, `Returns.tsx`, `AnalyticsBoard.tsx`, `TwoFactorSetup.tsx`, `AuditLog.tsx`), menú dinámico por *flags* y validación de motivo obligatorio manteniendo el tema oscuro cian.
- **Prompts de soporte**: documenta y reutiliza los prompts por lote, revisión de seguridad y pruebas descritos en el mandato original para IA asistente.
- **Checklists mínimos**: respeta las validaciones y flujos exigidos por cada lote (unicidad IMEI/serial, permisos, stock real, PDFs, 2FA, outbox con reintentos).
- **Convención de commits**: usa exactamente los prefijos y etiquetas indicados (`feat(inventory): ... [v2.2.0]`, `feat(transfers): ... [v2.2.0]`, etc.) según el lote implementado, además de `test:` y `docs:` cuando corresponda.
- **Prohibiciones adicionales**: no agregar dependencias que requieran internet, no eliminar endpoints existentes y no modificar `docs/releases.json` salvo notas internas sin afectar la versión.

Cumple estas directrices en todas las entregas hasta nuevo aviso.

## Verificación Global - Módulo de Inventario Softmobile 2025 v2.2.0

- **Fecha y hora**: 17/10/2025 05:41 UTC.
- **Resumen de hallazgos**: revisión integral sin incidencias; se verificó que catálogo, movimientos, identificadores IMEI/series, valuaciones, reportes, alertas, permisos y UI operan conforme a la versión v2.2.0 con feature flags activos. No se detectaron dependencias rotas ni cálculos inconsistentes.
- **Acciones ejecutadas**: ejecución completa de `pytest`, `npm --prefix frontend run build` y `npm --prefix frontend run test`; verificación manual de dependencias requeridas (incluyendo `openpyxl`) antes de las suites.
- **Recomendaciones**: continuar atendiendo las advertencias de pruebas React (`act(...)`) en futuras iteraciones y mantener el monitoreo de los umbrales `SOFTMOBILE_LOW_STOCK_THRESHOLD` y `SOFTMOBILE_ADJUSTMENT_VARIANCE_THRESHOLD` en ambientes productivos.

### Estado operativo iterativo — 15/02/2025

- ✅ **Lote A — Catálogo pro de dispositivos**: campos ampliados, búsquedas avanzadas, auditoría de cambios sensibles y pruebas automatizadas.
- ✅ **Lote B — Transferencias entre tiendas**: modelos `transfer_orders`, permisos por sucursal, flujo SOLICITADA→EN_TRANSITO→RECIBIDA/CANCELADA, endpoints FastAPI, componente React `TransferOrders` y pruebas `pytest` dedicadas.
- ✅ **Lote C — Compras y ventas simples**: órdenes de compra con recepción parcial y promedio ponderado de costo, ventas con descuento/método de pago y devoluciones cubiertas en backend, pruebas y panel React (`Purchases.tsx`, `Sales.tsx`, `Returns.tsx`).
- ✅ **Lote D — Analítica avanzada**: endpoints `/reports/analytics/*`, servicios `services/analytics.py`, PDF oscuro y componente `AnalyticsBoard.tsx` documentados y probados.
- ✅ **Lote E — Seguridad y auditoría fina**: middleware `X-Reason`, dependencias `require_reason`, 2FA TOTP habilitable por flag, auditoría/revocación de sesiones y componentes `TwoFactorSetup.tsx`/`AuditLog.tsx` operativos.
- ✅ **Lote F — Modo híbrido**: cola `sync_outbox` con reintentos, estrategia *last-write-wins*, panel de reintentos en `SyncPanel.tsx` y cobertura de pruebas.

**Próximos pasos**

1. Supervisar métricas híbridas y preparar mejoras de resolución de conflictos para nuevas entidades planeadas en v2.3.
2. Ampliar analítica con comparativos entre sucursales y nuevos formatos de exportación en la siguiente iteración.
3. Documentar lineamientos de soporte remoto para despliegues 2FA y sincronización distribuida.

### Bitácora de control — 15/02/2025

- `pytest` ejecutado en la raíz con resultado exitoso tras la integración de POS avanzado, reparaciones y paneles corporativos de clientes/proveedores.
- `npm --prefix frontend run build` completado en verde verificando la compilación del frontend con los nuevos módulos operativos.

### Actualización operativa — 20/02/2025

- Se añadió tablero global de métricas (`GlobalMetrics.tsx`) con Recharts y tarjetas dinámicas para ventas, inventario, reparaciones y ganancias.
- El panel `UserManagement.tsx` permite asignar roles, alternar estados y exige motivos corporativos, protegido por middleware de acceso.
- La API expone `/sync/history`, extiende la cola híbrida a POS, reparaciones y clientes, y registra reintentos automáticos con `requeue_failed_outbox_entries`.
- Se documentó y probó el flujo offline híbrido con `backend/tests/test_sync_offline_mode.py` (tres sucursales).
- Se modernizó la UI de tienda con pantalla de bienvenida animada, toasts renovados con iconografía, transiciones `framer-motion` entre secciones y modo táctil optimizado para el POS.

### Pasos de control iterativo (deben registrarse tras cada entrega)

1. Revisa `README.md`, este `AGENTS.md` y `docs/evaluacion_requerimientos.md` antes de modificar código; anota brechas resueltas o pendientes.
2. Ejecuta `pytest`, `npm --prefix frontend run build` y `npm --prefix frontend run test`; registra fecha y resultado en la bitácora interna del equipo.
3. Verifica desde el frontend las secciones Inventario, Operaciones, Analítica, Seguridad (incluyendo flujos 2FA con motivo) y Sincronización.
4. Asegura que la cola híbrida (`/sync/outbox`) quede sin pendientes críticos reintentando con `X-Reason` justificado y documenta el resultado.
5. Actualiza el apartado "Registro operativo de lotes entregados" del README con cualquier nuevo componente, endpoint o prueba agregada.

### Registro operativo — 25/02/2025

- Paso 4 documentado: se describieron tablas `repair_orders`, `customers`, `sales`, `pos_config`, `sync_outbox` y sus rutas asociadas en el README.
- Mockup actualizado en `docs/img/paso4_resumen.mmd` usando Mermaid para representar los flujos POS, reparaciones y sincronización híbrida sin adjuntar binarios.
- Nuevas pruebas automatizadas: `backend/tests/test_repairs.py`, `backend/tests/test_customers.py`, `backend/tests/test_pos.py` y `backend/tests/test_sync_full.py` cubren autenticación, roles y reintentos híbridos.

### Registro operativo — 26/02/2025

- ✅ Parte 1 — Inventario (Optimización total): se agregaron lotes de proveedores con costo unitario, lote y fecha (`/suppliers/{id}/batches`), columna `stores.inventory_value` y recalculo automático del costo promedio en movimientos (`unit_cost`), con cobertura en `test_supplier_batches_and_inventory_value`.
- 🔄 26/02/2025 — Se alinearon las columnas `created_at`/`updated_at` del modelo `SupplierBatch` con la migración `202502150007_inventory_batches` para reanudar `pytest` sin fallos.
- ▶️ Próximo paso inmediato: abordar la Parte 2 — Operaciones, implementando importación CSV, órdenes recurrentes y vinculación completa con Inventario.

### Registro operativo — 27/02/2025

- ✅ Parte 2 — Operaciones: transferencias con doble aprobación, importación CSV, órdenes recurrentes y descuento automático de stock confirmados en backend (`routers/operations.py`, `transfers.py`, `purchases.py`, `sales.py`) y frontend (`OperationsPage.tsx`).
- ✅ Parte 3 — Analítica: proyecciones con regresión lineal, alertas automáticas y filtros avanzados activos en `services/analytics.py`, `/reports/analytics/*` y `AnalyticsBoard.tsx`.
- ✅ Parte 4 — Seguridad: 2FA controlada por flag, bloqueo temporal por intentos fallidos, filtros de auditoría y exportación CSV vigentes en `security.py` y `AuditLog.tsx`.
- ✅ Parte 5 — Sincronización: modo híbrido con prioridad por entidad, respaldo cifrado `/backup/softmobile` y botón de errores recientes disponibles en `sync.py`, `services/sync_outbox.py` y `SyncPanel.tsx`.
- ✅ Parte 6 — Usuarios: roles ADMIN/GERENTE/OPERADOR, panel de permisos, mensajería interna, avatares y historial de sesiones operativos en `users.py` y `UserManagement.tsx`.
- ✅ Parte 7 — Reparaciones: descuento de piezas, cálculo de costos, estados personalizados y notificaciones a clientes registrados en `repairs.py`, `RepairOrders.tsx` y la bitácora de seguridad.
- ✅ Parte 8 — Backend general e instalador: API FastAPI + PostgreSQL con JWT protegidos, actualizador automático (`updates.py`) y plantillas de instalador (`installers/`) con modo offline.

### Registro operativo — 28/02/2025

- ✅ Parte 4 — Seguridad: la bitácora de auditoría ahora permite filtrar por usuario, acción, módulo y rango de fechas, además de exportarse a CSV desde `/audit/logs/export.csv` y `/reports/audit`. Cobertura verificada en `backend/tests/test_audit_logs.py`.
- ✅ 28/02/2025 — Se habilitó `/reports/audit/pdf` con filtros impresos, clasificación por severidad en `services/audit.py` y alertas visuales dentro de `AuditLog.tsx`, incluyendo descarga directa desde la UI. Pruebas extendidas en `backend/tests/test_audit_logs.py`.
- ✅ 28/02/2025 — El tablero `GlobalMetrics.tsx` ahora resume alertas críticas/preventivas desde `/reports/metrics` y ofrece destacados para respuestas rápidas; se documentó el flujo en el README.
- ✅ 28/02/2025 — Se activaron recordatorios automáticos de alertas críticas persistentes con `/audit/reminders`, toasts periódicos y snooze de 10 minutos en `AuditLog.tsx`.

### Registro operativo — 29/02/2025

- ✅ 29/02/2025 — Se habilitaron acuses manuales para alertas críticas (`POST /audit/acknowledgements`), se integraron en Seguridad con notas/motivos y `/reports/metrics` ahora distingue pendientes vs. atendidas en el tablero global.
- ✅ 29/02/2025 — Las exportaciones CSV/PDF de auditoría incorporan el estado del acuse, usuario, fecha y nota registrada, con validaciones de duplicado y mensajes de error específicos en el frontend.
- ▶️ Próximo paso inmediato: monitorear escenarios multiusuario en Seguridad y ajustar recordatorios si aparecen nuevos requisitos.

### Actualización Inventario - Catálogo de Productos (27/03/2025 18:00 UTC)

- Extiende el modelo `Device` y sus respuestas API con los campos `categoria`, `condicion`, `capacidad`, `estado`, `fecha_ingreso`, `ubicacion`, `descripcion` e `imagen_url`; incluye migración Alembic `202502150009_inventory_catalog_extensions`.
- Activa endpoints `/inventory/stores/{id}/devices/export` y `/inventory/stores/{id}/devices/import` con validaciones de encabezados, resumen de filas y bitácora automática mediante `inventory_import.py`.
- Actualiza `InventoryPage`, `InventoryTable`, `DeviceEditDialog` y `AdvancedSearch` para capturar, filtrar y mostrar los campos nuevos, además de exponer un panel de importación/exportación con motivo corporativo.
- Pruebas reforzadas: `backend/tests/test_catalog_pro.py` cubre el flujo masivo y `AdvancedSearch.test.tsx` valida los filtros extendidos en Vitest.

### Actualización Inventario - Catálogo de Productos (27/03/2025 23:45 UTC)

- Se documentan los alias `costo_compra` y `precio_venta` como nombres oficiales de compra/venta; el modelo `Device`, esquemas FastAPI y CRUD los sincronizan automáticamente con `costo_unitario`/`unit_price`.
- La exportación/importación de CSV produce y consume los alias financieros, ignora `garantia_meses` vacía y devuelve resúmenes coherentes (`created=1`, `updated=1`, `skipped=0`).
- `InventoryTable` muestra columnas de costo y precio de venta, y `DeviceEditDialog` actualiza ambos valores enviando también los nombres previos para mantener auditoría y compatibilidad.
- `backend/tests/test_catalog_pro.py` y las pruebas de Vitest del módulo de inventario verifican los campos nuevos y el flujo corregido de importación/exportación.

### Actualización Inventario - Movimientos de Stock

- Refuerza la tabla `inventory_movements` con `producto_id`, `tienda_origen_id`, `tienda_destino_id`, `comentario`, `usuario_id` y `fecha`, manteniendo integridad referencial mediante la migración `202502150010_inventory_movements_enhancements`.
- El endpoint `/inventory/stores/{store_id}/movements` valida destino contra la sucursal solicitada, expone los campos en español y bloquea salidas que dejen inventario negativo.
- `MovementCreate` y `MovementResponse` requieren y normalizan el comentario corporativo, rechazan solicitudes con menos de 5 caracteres y solo aceptan registros cuando el motivo coincide con la cabecera `X-Reason`.
- Compras, ventas, devoluciones, reparaciones y recepciones de transferencias registran movimientos con origen/destino corporativo y recalculan automáticamente el valor del inventario por tienda sin permitir existencias negativas.
- El formulario `MovementForm.tsx` utiliza los nuevos campos (`producto_id`, `tipo_movimiento`, `cantidad`, `comentario`) y exige motivos ≥5 caracteres reutilizados en la cabecera `X-Reason`.
- El snapshot operativo (`build_inventory_snapshot`) expone `tienda_origen_id`, `tienda_destino_id`, `comentario`, `usuario_id` y `fecha` para cada movimiento al consultar `/updates/snapshot`.
- Compras, ventas, devoluciones y reparaciones registran movimientos con origen/destino apropiado y comentario corporativo para recalcular automáticamente el valor del inventario por tienda.
- El formulario `MovementForm.tsx` utiliza los nuevos campos (`producto_id`, `tipo_movimiento`, `cantidad`, `comentario`) y exige motivos ≥5 caracteres reutilizados en la cabecera `X-Reason`.
- Las respuestas del endpoint incluyen `usuario`, `tienda_origen` y `tienda_destino` además de los identificadores para cumplir auditorías sin romper integraciones existentes.

### Actualización Inventario - Gestión de IMEI y Series

- Crea y mantiene la tabla `device_identifiers` (`202503010001_device_identifiers.py`) ligada a `devices.id` y con campos `imei_1`, `imei_2`, `numero_serie`, `estado_tecnico` y `observaciones`; respeta las restricciones de unicidad definidas.
- Expone operaciones FastAPI `GET/PUT /inventory/stores/{store_id}/devices/{device_id}/identifier`, obligando cabecera `X-Reason` ≥ 5 caracteres y registrando auditoría `device_identifier_created|updated` con el motivo recibido.
- Asegura que `_ensure_unique_identifiers` y `_ensure_unique_identifier_payload` bloqueen duplicados entre `devices` y `device_identifiers`, devolviendo el código `device_identifier_conflict` ante colisiones.
- Propaga los datos extendidos al frontend: tipos actualizados en `frontend/src/api.ts`, helpers `getDeviceIdentifier`/`upsertDeviceIdentifier` y visualización en `InventoryTable.tsx` para IMEIs duales, serie extendida, estado técnico y observaciones.
- Mantén cobertura en `backend/tests/test_device_identifiers.py` y extiende pruebas si agregas campos adicionales, garantizando escenarios de conflicto y respuesta 404 cuando un dispositivo no tenga identificadores registrados.
- Añade regresiones cuando corresponda: `test_device_creation_rejects_conflicts_from_identifier_table` debe seguir comprobando que la creación de dispositivos rechaza IMEIs o series duplicados almacenados en `device_identifiers` con el error `device_identifier_conflict`.

### Actualización Inventario - Valoraciones y Costos

- Asegura que la migración `202503010002_inventory_valuation_view.py` se ejecute para crear la vista `valor_inventario` con costos promedio ponderados, totales por tienda y márgenes por categoría.
- Conserva las columnas comparativas (`valor_costo_*`, `valor_total_categoria`, `margen_total_*`) que permiten contrastar el valor de venta frente al costo y los márgenes acumulados por sucursal y corporativo.
- Utiliza el servicio `services/inventory.calculate_inventory_valuation` y el esquema `InventoryValuation` para exponer la vista sin romper compatibilidad con rutas actuales.
- Mantén la vista disponible en entornos de prueba invocando los helpers `create_valor_inventario_view`/`drop_valor_inventario_view` desde `backend/app/db/valor_inventario_view.py`.
- Extiende o ajusta `backend/tests/test_inventory_valuation.py` si agregas columnas adicionales, garantizando validación de márgenes y filtros por tienda/categoría.

### Actualización Inventario - Reportes y Estadísticas (30/03/2025)

- Agrega endpoints `GET /reports/inventory/current|value|movements|top-products` con filtros por sucursal, fechas y tipo de movimiento. Cada ruta cuenta con versión CSV (`/csv`), PDF (`/pdf`) y Excel (`/xlsx`) que exigen `X-Reason` y roles de reporte.
- `GET /reports/inventory/current/{csv|pdf|xlsx}` debe ofrecer el resumen por sucursal de dispositivos, unidades y valor consolidado. Propaga los filtros por sucursal y valida motivo corporativo en encabezados antes de entregar el archivo.
- `crud.py` incorpora los agregadores `get_inventory_current_report`, `get_inventory_movements_report`, `get_top_selling_products` y `get_inventory_value_report`, reutilizados por `reports.py` y cubiertos en `backend/tests/test_reports_inventory.py`.
- `_normalize_date_range` debe ampliar automáticamente los rangos recibidos como fecha (`YYYY-MM-DD`) hasta las 23:59:59 para no perder movimientos registrados durante la jornada.
- El tab **Reportes** de `InventoryPage.tsx` usa `InventoryReportsPanel.tsx` para mostrar métricas claves, filtros y botones de exportación a CSV/PDF/Excel. Mantén la estética corporativa (oscuro + acentos cian).
- `frontend/src/api.ts` y `inventoryService.ts` exponen helpers (`getInventoryMovementsReport`, `downloadInventoryMovements{Csv|Pdf|Xlsx}`, etc.) que deben documentarse al añadir nuevos reportes.
- Asegura que las exportaciones pidan motivo corporativo y propaguen errores; la prueba `InventoryPage.test.tsx` valida la interacción completa.
- Refuerza las pruebas en `backend/tests/test_reports_inventory.py` para impedir descargas CSV/PDF/Excel sin la cabecera corporativa `X-Reason`.
- Cuando envíes `X-Reason` en encabezados HTTP, utiliza sólo caracteres ASCII (sin acentos) para evitar errores de codificación en clientes que restringen el conjunto permitido.

### Actualización Inventario - Ajustes y Auditorías

- `crud.create_inventory_movement` debe conservar `stock_previo`, `stock_actual` y el motivo corporativo en los detalles de auditoría para cualquier ajuste manual.
- Configura los umbrales `SOFTMOBILE_LOW_STOCK_THRESHOLD` y `SOFTMOBILE_ADJUSTMENT_VARIANCE_THRESHOLD` según el plan corporativo; stock ≤ umbral genera `inventory_low_stock_alert` (crítica) y ajustes que superen la variación permitida disparan `inventory_adjustment_alert` (preventiva).
- Mantén sincronizadas las palabras clave de severidad en `backend/app/utils/audit.py` para clasificar `stock bajo`, `ajuste manual` e `inconsistencia`.
- Refuerza pruebas automatizadas en `backend/tests/test_stores.py::test_manual_adjustment_triggers_alerts` si cambian los umbrales o la estructura de la bitácora.

### Actualización Inventario - Roles y Permisos

- `require_roles` debe conceder acceso inmediato a usuarios con rol `ADMIN` aun cuando la ruta restrinja a otros perfiles, asegurando control total corporativo.
- Mantén `REPORTE_ROLES` y `AUDITORIA_ROLES` limitados a `ADMIN` y `GERENTE` para que únicamente ellos consulten inventario, reportes y bitácoras sensibles.
- Utiliza `MOVEMENT_ROLES` (ADMIN, GERENTE, OPERADOR) en rutas de movimientos para que operadores sólo registren entradas/salidas sin poder listar inventario ni descargar reportes.
- Revisa `backend/tests/test_stores.py::test_operator_can_register_movements_but_not_view_inventory` tras cualquier ajuste de permisos para conservar la cobertura sobre accesos denegados.

### Registro operativo — 01/03/2025

- ✅ 01/03/2025 — Los reportes de inventario PDF y CSV ahora incluyen columnas financieras completas y los campos del catálogo pro (IMEI, serie, marca, modelo, proveedor, color, capacidad, lote, costo y margen), respaldados por helpers reutilizables en `services/backups.py`.
- ✅ 01/03/2025 — Se añadieron pruebas `test_render_snapshot_pdf_includes_financial_and_catalog_details` y `test_inventory_csv_snapshot` para validar totales, columnas avanzadas y compatibilidad con los motivos corporativos.

### Registro operativo — 05/03/2025

- ✅ 05/03/2025 — El snapshot de inventario incorpora `summary` con conteos corporativos, totales de unidades y el valor contable por sucursal, sincronizado con los reportes PDF/CSV.
- ✅ 05/03/2025 — Los reportes PDF contrastan valor calculado vs. registrado y los CSV agregan filas "TOTAL SUCURSAL"/"VALOR CONTABLE" junto con un resumen corporativo; cobertura reforzada en `test_inventory_snapshot_summary_includes_store_values`.

**Acciones obligatorias antes de nuevas iteraciones**

1. Leer `README.md`, este `AGENTS.md` y `docs/evaluacion_requerimientos.md` para identificar pendientes.
2. Ejecutar `pytest` y `npm --prefix frontend run build`, registrando fecha y resultado en la bitácora interna.
3. Validar inventario, operaciones, analítica, seguridad, sincronización y usuarios en el frontend, asegurando que `/sync/outbox` quede sin pendientes críticos y documentando incidentes.

### Plan operativo inmediato — Seguridad y auditoría

1. ✅ **Recordatorios y acuses activos en Seguridad**: `AuditLog.tsx` debe mantener badges de pendientes/atendidas, snooze corporativo de 10 minutos y descargas CSV/PDF con motivo (`X-Reason` ≥ 5). No modifiques este comportamiento sin actualizar README y pruebas.
2. ✅ **Tablero global enriquecido**: `GlobalMetrics.tsx` tiene que reflejar `pending_count`/`acknowledged_count`, destacar el último acuse y enlazar a `/dashboard/security` cuando existan pendientes.
3. 🔄 **Pruebas de frontend obligatorias**: incorpora Vitest + React Testing Library para simular recordatorios, registros de acuse y descargas; agrega el script `npm run test` y ejecútalo junto con `npm run build` en cada iteración.
4. 🔄 **Bitácora corporativa**: registra cada corrida de `pytest`, `npm --prefix frontend run build` y `npm run test` en `docs/bitacora_pruebas_YYYY-MM-DD.md`, indicando hash del commit, responsable y resultado.

### Actualización Compras - Parte 1 (Estructura y Relaciones) (17/10/2025 10:15 UTC)

- Se crean las tablas `proveedores`, `compras` y `detalle_compras` con columnas (`id_proveedor`, `nombre`, `telefono`, `correo`, `direccion`, `tipo`, `estado`, `notas`, `id_compra`, `proveedor_id`, `usuario_id`, `fecha`, `total`, `impuesto`, `forma_pago`, `estado`, `id_detalle`, `compra_id`, `producto_id`, `cantidad`, `costo_unitario`, `subtotal`) alineadas al mandato Softmobile 2025 v2.2.0.
- Las claves foráneas `compras.proveedor_id → proveedores.id_proveedor`, `compras.usuario_id → users.id`, `detalle_compras.compra_id → compras.id_compra` y `detalle_compras.producto_id → devices.id` (alias corporativo de productos) quedan reforzadas con índices para acelerar consultas.
- La migración `202502150011_compras_estructura_relaciones.py` es idempotente: sólo crea/ajusta estructuras cuando faltan y respeta instalaciones existentes.
- La prueba `backend/tests/test_compras_schema.py` inspecciona columnas, tipos, índices y relaciones para prevenir regresiones estructurales en compras y proveedores.
- **17/10/2025 10:45 UTC** — Auditoría recurrente confirma que los tipos (`Integer`, `Numeric`, `DateTime`, `Text`) y claves `RESTRICT`/`CASCADE` se conservan en base de datos y que los índices `ix_proveedores_nombre`, `ix_compras_*` e `ix_detalle_compras_*` permanecen vigentes tras ejecutar la suite.

### Actualización Compras - Parte 2 (Lógica e Integración con Inventario) (17/10/2025 11:30 UTC)

- Cada recepción de orden genera movimientos `entrada` en `inventory_movements` con comentarios corporativos que incluyen proveedor, motivo `X-Reason` e identificadores IMEI/serie, dejando rastro del usuario responsable.
- La cancelación de órdenes revierte unidades recibidas mediante movimientos `salida`, recalcula costos promedio y documenta los artículos revertidos en el log de auditoría.
- Las devoluciones a proveedor ajustan stock y costo ponderado antes de registrar el movimiento, asegurando consistencia con el valor de inventario por tienda.
- `backend/tests/test_purchases.py` valida recepciones, devoluciones y cancelaciones para garantizar que el inventario se actualice y se audite conforme a la política corporativa.
- Se mantiene la vista SQL `movimientos_inventario` como alias de `inventory_movements` para integraciones heredadas que consultan movimientos por nombre en español.

### Actualización Compras - Parte 3 (Interfaz y Reportes) (17/10/2025 12:15 UTC)

- El componente `frontend/src/modules/operations/components/Purchases.tsx` incorpora un formulario completo de registro directo de compras con cálculo automático de impuestos, selección de proveedor y descarga inmediata de totales.
- Se publica un listado general de compras con filtros por proveedor, usuario, fechas, estado o búsqueda libre y exportaciones PDF/Excel protegidas por `X-Reason`.
- Se habilita un panel de proveedores con alta/edición, exportación CSV, activación/inactivación y un historial detallado conectado a los endpoints `/purchases/vendors/*`.
- El dashboard del módulo muestra tarjetas de estadísticas mensuales, proveedores frecuentes y rankings de usuarios reutilizando `getPurchaseStatistics` para mantener coherencia entre backend y UI.
- Documentación y bitácora (README, CHANGELOG y este AGENTS) registran la actualización bajo «Actualización Compras - Parte 3 (Interfaz y Reportes)» para preservar trazabilidad corporativa.
- Mantén esta cobertura alineada: cualquier ajuste en `frontend/src/modules/operations/components/Purchases.tsx` debe seguir hablando con `backend/app/routers/purchases.py` y respetar las pruebas `backend/tests/test_purchases.py::test_purchase_records_and_vendor_statistics`, que garantizan exportaciones PDF/Excel, filtros por fecha/proveedor/usuario y métricas mensuales.

### Actualización Ventas - Parte 1 (Estructura y Relaciones) (17/10/2025 06:25 UTC)

- Tablas `sales` y `sale_items` renombradas a `ventas` y `detalle_ventas` con columnas homologadas (`id_venta`, `cliente_id`, `usuario_id`, `fecha`, `forma_pago`, `impuesto`, `total`, `estado`, `venta_id`, `producto_id`, `precio_unitario`, `subtotal`).
- Migración `202503010003_sales_ventas_structure.py` refuerza claves foráneas hacia `customers`, `users`, `ventas` y `devices`, creando índices únicamente cuando faltan en instalaciones previas.
- Modelos ORM, esquemas Pydantic y lógica de creación de ventas incorporan el campo `estado`, normalizando el valor recibido y garantizando compatibilidad con los cálculos de impuestos y totales existentes.

### Actualización Ventas - Parte 2 (Lógica Funcional e Integración con Inventario) (17/10/2025 06:54 UTC)

- Cada venta registra un movimiento `OUT` en `inventory_movements`, descuenta stock y marca los dispositivos con IMEI o serie como `vendido` para impedir reprocesos.
- Al editar, cancelar o devolver ventas se crean movimientos `IN`, se restaura el estado `disponible` de los dispositivos identificados y se recalcula automáticamente el valor del inventario por tienda.
- Se habilita la edición de ventas mediante `PUT /sales/{id}` con validaciones de stock, actualización de deudas a crédito y auditoría detallada en la bitácora.
- Se incorpora `POST /sales/{id}/cancel` para anular ventas con reintegro de existencias y sincronización del evento en `sync_outbox`.
- Las pruebas `backend/tests/test_sales.py` cubren ventas multiartículo, dispositivos con IMEI, ediciones y anulaciones para garantizar la integración con inventario.

### Actualización Ventas - Parte 3 (Interfaz y Reportes) (17/10/2025 07:45 UTC)

- El componente `Sales.tsx` ahora ofrece carrito multiartículo con búsqueda por IMEI/SKU/modelo, selección de clientes registrados o manuales y cálculo automático de subtotal/impuestos/total en tema oscuro.
- `GET /sales` acepta filtros por fecha, cliente, usuario y texto libre; además se publican `/sales/export/pdf` y `/sales/export/xlsx` para descargar reportes de ventas con motivo corporativo obligatorio.
- Los reportes PDF/Excel reutilizan estilos corporativos oscuros y muestran totales, impuestos y estadísticas diarias; el dashboard de operaciones refleja los mismos totales para mantener coherencia visual.
- `frontend/src/api.ts` incorpora helpers `exportSalesPdf|Excel` y tipos enriquecidos (`SaleStoreSummary`, `SaleUserSummary`, `SaleDeviceSummary`); las pruebas `backend/tests/test_sales.py` verifican filtros y exportaciones.
- **17/10/2025 08:30 UTC** — Se envolvió el flujo de captura en un único formulario para que "Guardar venta" active `handleSubmit`, además de añadir estilos oscuros/fluídos a `Sales.tsx` (`sales-form`, `table-responsive`, `totals-card`, `actions-card`).
- **17/10/2025 09:15 UTC** — Se reforzó el dashboard con tarjetas de ticket promedio y columna de promedios diarios, reutilizando el cálculo del backend y nuevos estilos (`metric-secondary`, `metric-primary`) para remarcar totales, impuestos y estadísticas de ventas.

### Actualización Clientes - Parte 1 (Estructura y Relaciones) (17/10/2025 13:45 UTC)

- La migración `202503010005_clientes_estructura_relaciones.py` renombra la tabla `customers` a `clientes`, ajusta columnas (`id_cliente`, `nombre`, `telefono`, `correo`, `direccion`, `tipo`, `estado`, `limite_credito`, `saldo`, `notas`) y marca el teléfono como obligatorio con valores de contingencia para datos históricos.
- Se actualizan las claves foráneas `ventas.cliente_id` y `repair_orders.customer_id` para apuntar a `clientes.id_cliente`, preservando el enlace de facturas POS y órdenes de reparación con cada cliente; se crean índices `ix_clientes_*` y la unicidad `uq_clientes_correo`.
- Los esquemas y CRUD de clientes exponen tipo, estado y límite de crédito, validan teléfonos y saldos con decimales y amplían la exportación CSV con los nuevos campos; la prueba `backend/tests/test_clientes_schema.py` inspecciona columnas, índices y relaciones.
- `frontend/src/modules/operations/components/Customers.tsx` añade selectores de tipo/estado, captura el límite de crédito y muestra los campos en la tabla manteniendo el motivo corporativo en altas, ediciones, notas y ajustes de saldo.
- **19/10/2025 14:30 UTC** — Auditoría reciente confirma la no nulidad de `limite_credito` y `saldo`, documenta el índice `ix_ventas_cliente_id` y actualiza `test_pos_sale_with_receipt_and_config` para forzar un `customer_id` válido en ventas POS, garantizando que los recibos PDF queden ligados al cliente corporativo.
- **20/10/2025 11:30 UTC** — Se valida que las claves foráneas `ventas.cliente_id` y `repair_orders.customer_id` utilicen `SET NULL` y se añade la prueba `test_factura_se_vincula_con_cliente` para preservar el vínculo activo entre facturas y clientes.
- **21/10/2025 09:00 UTC** — Se ajusta `backend/tests/test_clientes_schema.py` importando `Decimal` y reforzando aserciones de índices, mientras que el modelo `Customer` indexa `tipo` y `estado` para conservar los filtros operativos durante las pruebas de facturación ligadas a clientes.

### Actualización Clientes - Parte 2 (Lógica Funcional y Control) (20/10/2025 15:20 UTC)

- La migración `202503010006_customer_ledger_entries.py` habilita la bitácora `customer_ledger_entries` con tipos `sale`, `payment`, `adjustment` y `note`, sincronizados vía `sync_outbox` para auditar cada modificación de saldo.
- Nuevos endpoints corporativos: `/customers/{id}/notes` agrega notas con historial y ledger, `/customers/{id}/payments` registra abonos que descuentan deuda y `/customers/{id}/summary` entrega un resumen financiero con ventas, facturas, pagos y movimientos recientes.
- El backend valida límites de crédito mediante `_validate_customer_credit` en altas, ediciones, cancelaciones y devoluciones de ventas; se generan entradas automáticas en la bitácora y se controla el saldo disponible antes de confirmar una operación.
- Se normalizan los campos `status` y `customer_type`, se rechazan límites de crédito o saldos negativos y cada asiento (`sale`, `payment`, `adjustment`, `note`) se serializa con `_customer_ledger_payload` para su sincronización híbrida.
- El POS alerta cuando la venta a crédito agotará o excederá el límite configurado y el módulo `Customers.tsx` incorpora registro directo de pagos, resumen financiero interactivo, estados `moroso/vip` y notas dedicadas, manteniendo motivo corporativo obligatorio.
- Se normaliza el payload del ledger cambiando `metadata` por `details` en backend y frontend para eliminar referencias obsoletas que causaban fallos en `pytest` al consultar `/customers/{id}/summary`.
- Cobertura reforzada: `test_customer_credit_limit_blocks_sale` y `test_customer_payments_and_summary` verifican bloqueo de crédito en ventas y que el resumen corporativo liste ventas, facturas, pagos y notas con saldos coherentes.
- Ajuste 22/10/2025 09:40 UTC: garantizar que `/customers/{id}/payments` devuelva el campo `created_by` serializado correctamente y que las devoluciones a crédito registren al usuario responsable en el ledger.
- Ajuste 23/10/2025 10:05 UTC: `/sales` y `/pos/sale` responden con `409 Conflict` si la venta a crédito rebasa el límite aprobado; la prueba `test_credit_sale_rejected_when_limit_exceeded` confirma que el inventario se mantiene sin cambios cuando ocurre el bloqueo.
- Mejora 24/10/2025 08:10 UTC: al ajustar `outstanding_debt` mediante `PUT /customers/{id}` se genera un asiento `adjustment` con saldo previo/posterior, se agrega la nota al historial y la prueba `test_customer_manual_debt_adjustment_creates_ledger_entry` cubre el escenario.
- Validación 25/10/2025 11:05 UTC: las altas o ediciones con deudas que superen el límite de crédito configurado se rechazan con `422` y mensaje claro; la prueba `test_customer_debt_cannot_exceed_credit_limit` garantiza el comportamiento y evita que clientes sin crédito acumulen saldo.

### Actualización Clientes - Parte 3 (Interfaz y Reportes) (26/10/2025 12:00 UTC)

- `frontend/src/modules/operations/components/Customers.tsx` agrega filtros por estado/tipo/saldo, panel de portafolios PDF/Excel y dashboard oscuro de altas mensuales/top compradores; cualquier ajuste debe preservar los selectores, las barras proporcionales y los botones con motivo corporativo.
- `backend/app/routers/customers.py` expone `/customers/dashboard` y soporta los nuevos filtros `status`, `customer_type`, `has_debt` en el listado general; mantener compatibilidad con la búsqueda y el límite original.
- `backend/app/routers/reports.py` publica `/reports/customers/portfolio` con soporte JSON/PDF/Excel; toda exportación exige cabecera `X-Reason` y reutiliza `backend/app/services/customer_reports.py` para estilos oscuros.
- `backend/app/services/customer_reports.py` genera PDF/Excel en tema oscuro para portafolios; no modificar colores corporativos (`#0f172a`, `#111827`, acento `#38bdf8`) sin actualizar esta bitácora.
- Los nuevos esquemas (`CustomerPortfolioReport`, `CustomerDashboardMetrics`, etc.) viven en `backend/app/schemas/__init__.py` y deben mantenerse en sincronía con `backend/app/crud.py` y el frontend.
- Cobertura: `backend/tests/test_customers.py` incorpora casos `test_customer_filters_and_reports` y `test_customer_portfolio_exports`; cualquier cambio en reportes o métricas debe actualizar estas pruebas.

- Refinamiento 26/10/2025 09:15 UTC: el listado de clientes (`GET /customers`) admite filtros dedicados `status_filter` y `customer_type_filter` que se consumen desde `Customers.tsx`, habilitando segmentaciones rápidas (activo, moroso, VIP, corporativo) y cobertura automática en `test_customer_list_filters_by_status_and_type`.

