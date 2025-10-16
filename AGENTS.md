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
- `MovementCreate` y `MovementResponse` normalizan el comentario corporativo y rechazan solicitudes con menos de 5 caracteres antes de registrar el movimiento o aceptar la cabecera `X-Reason`.
- Compras, ventas, devoluciones, reparaciones y recepciones de transferencias registran movimientos con origen/destino corporativo y recalculan automáticamente el valor del inventario por tienda sin permitir existencias negativas.
- El formulario `MovementForm.tsx` utiliza los nuevos campos (`producto_id`, `tipo_movimiento`, `cantidad`, `comentario`) y exige motivos ≥5 caracteres reutilizados en la cabecera `X-Reason`.
- El snapshot operativo (`build_inventory_snapshot`) expone `tienda_origen_id`, `tienda_destino_id`, `comentario`, `usuario_id` y `fecha` para cada movimiento al consultar `/updates/snapshot`.
- Compras, ventas, devoluciones y reparaciones registran movimientos con origen/destino apropiado y comentario corporativo para recalcular automáticamente el valor del inventario por tienda.
- El formulario `MovementForm.tsx` utiliza los nuevos campos (`producto_id`, `tipo_movimiento`, `cantidad`, `comentario`) y exige motivos ≥5 caracteres reutilizados en la cabecera `X-Reason`.

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
