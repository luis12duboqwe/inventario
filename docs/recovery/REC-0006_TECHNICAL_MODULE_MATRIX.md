# REC-0006 — Matriz técnica real por módulos (R2)

## Alcance y baseline

Este documento aplica **únicamente** a `luis12duboqwe/inventario`.

Fuera de alcance: `inventario-main`, `sistema-de-inve-sand` y cualquier otro repositorio.

Baseline auditado de esta matriz:

- REC-0004 backend recuperado: `a99c8fecb15781c8fa31787f5714091940ffaa5d`.
- REC-0005 frontend strict verde: `2765dc4f0f85e04b1e7728d39153a4aff084827e`.
- Rama R2: `recovery/rec-0006-technical-module-matrix`.
- Softmobile CI final de REC-0005: run `33086901490` — success.
- Backend en ese run: **348 passed, 5 skipped, 0 failed**.
- Frontend en ese run: strict TypeScript ✅, ESLint ✅, Vitest ✅, production build ✅.
- Import de FastAPI: Softmobile Central `2.2.0`; 1135 rutas montadas contando prefijos/aliases.

La clasificación refleja el **estado operativo observable en este baseline**, no afirmaciones históricas de README/CHANGELOG.

## Estados

- `FUNCIONA`: implementación conectada, probada y sin bloqueo funcional conocido en el alcance auditado.
- `REPARAR`: existe y funciona parcial o mayoritariamente, pero duplicidad, integración incompleta o deuda estructural impide considerarla canónica.
- `TERMINAR`: existe interfaz/flujo visible con placeholder, simulación, botón sin acción o integración faltante.
- `ELIMINAR`: duplicado/huérfano/obsoleto con evidencia suficiente; la eliminación efectiva corresponde a R3/R7.
- `NO EVALUADO`: no debe quedar ningún módulo visible en el cierre de R2.

## Matriz canónica

| # | Módulo | Frontend / rutas | Backend / persistencia | Pruebas/evidencia | Legacy / simulación / deuda | Estado |
|---|---|---|---|---|---|---|
| 1 | Autenticación y sesiones | `/login`; `frontend/src/auth/*`; guards `RequireAuth` | `routers/auth.py`, `security.py`, usuarios/sesiones | `test_auth_login_email.py`, `test_auth_pack28.py`, `test_routes_bootstrap.py`, `test_security.py` verdes | Bootstrap y refresh están conectados. Seguridad sigue compartiendo infraestructura legacy transversal por `crud/__init__.py`, pero sin bloqueo conocido. | **FUNCIONA** |
| 2 | Usuarios, roles y permisos | `/dashboard/users`, `/dashboard/security`; `useAuthz`, `RequireRole`, `RequirePerm` | `routers/users.py`, `routers/security.py`, CRUD users, roles/permisos | `test_users_management.py`, `test_permissions.py`, `test_rbac_matrix.py`, `test_roles.py`, `test_security.py` verdes | Debe migrarse fuera de wildcard/compatibilidad legacy en R3, sin evidencia de fallo funcional actual. | **FUNCIONA** |
| 3 | Sucursales / almacenes / WMS | `/dashboard/stores`; `/dashboard/operations/wms` | `routers/stores.py`, `routers/wms_bins.py`, `crud/stores.py`, `crud/warehouses.py`, modelos stores | `test_stores.py`, `test_soft_deletes.py`, `test_wms_bins.py`, schemas de sucursales verdes | WMS depende de feature flag; no se detectó placeholder bloqueante en la ruta activa. | **FUNCIONA** |
| 4 | Inventario, IMEI/seriales y valuación | `/dashboard/inventory/*`: productos, listas, movimientos, proveedores, alertas, reservas | routers inventory/import/export/variants/counts; `models/inventory.py`, `products.py`; `crud/inventory.py`, `devices.py`; servicio contable | Amplia cobertura: `test_inventory_*`, `test_device_identifiers*`, `test_stores.py`, `test_suppliers.py`, `test_reports_inventory.py`; backend verde | Core recuperado depende todavía de bridges en `crud/__init__.py` (`_normalize_date_range`, recálculo, movimientos, legacy helpers). Tres pantallas antiguas no enrutadas quedan como candidatas a eliminar. | **FUNCIONA** |
| 5 | Compras y proveedores | `/dashboard/operations/compras`; inventario/proveedores | `routers/purchases.py`, `suppliers.py`; `models/purchases.py`; `crud/purchases.py`, `suppliers.py` | `test_purchases.py`, `test_purchases_complex_cost.py`, `test_purchase_suggestions.py`, `test_suppliers.py`, `test_reports_purchases.py` verdes | Recalculo de precio se reinyecta desde compatibilidad REC-0004. Funcional hoy; deuda arquitectónica para R3. | **FUNCIONA** |
| 6 | Ventas / POS | Dos rutas activas: `/dashboard/operations/pos` y `/dashboard/sales/pos` con implementaciones diferentes | `routers/pos.py`, `sales.py`, payments, store credits; `models/sales.py`; `crud/pos.py`, `sales.py` | `test_pos.py`, `test_pos_module.py`, `test_pos_pack34.py`, `test_pos_promotions.py`, `test_sales.py`, tests frontend POS verdes | **Dos POS activos**: `OperationsPOS.tsx` y `sales/pages/POSPage.tsx`. Ambos conectan servicios reales, pero la duplicidad impide definir una UI canónica. POS sales además conserva TODO menores de manejo visual/preview. | **REPARAR** |
| 7 | Caja diaria | Caja integrada dentro de `OperationsPOS`; además `/dashboard/sales/cash-close` | Backend POS soporta apertura/cierre/sesiones/historial | `test_pos.py`, `test_cash_register_entries.py`, `test_pos_session_recovery.py` verdes | `sales/pages/CashClosePage.tsx` está **enrutada** pero usa `INITIAL_TOTALS` en cero, `TODO(wire)` y texto explícito de placeholder. Debe consolidarse con la caja real de OperationsPOS o eliminar la ruta duplicada. | **TERMINAR** |
| 8 | Clientes / cuentas por cobrar / créditos | `/dashboard/sales/customers` y `customers/:id`; operaciones relacionadas desde POS | `routers/customers.py`, store credits, reminders; `models/customers.py`; `crud/customers.py` | `test_customers.py`, `test_customer_ledger_composite.py`, `test_accounts_receivable_reminders.py`, `test_customer_segments.py`, `test_store_credits.py` verdes | CRUD y cola offline están conectados, pero `CustomerDetailPage` deja visible `TODO(wire) tabla de ventas del cliente`. | **TERMINAR** |
| 9 | Devoluciones / reembolsos | `/dashboard/operations/devoluciones`; `/dashboard/sales/returns/*`; devolución también desde POS | `routers/returns.py`, ventas/POS; modelos sales | `test_returns.py`, `test_sales.py`, `test_pos.py`, `test_pos_pack34.py` verdes | Hay más de un entrypoint de UI, pero las operaciones se conectan a backend real. No se confirmó placeholder bloqueante. | **FUNCIONA** |
| 10 | Garantías | `/dashboard/operations/garantias` | `routers/warranties.py`; modelos de warranty en dominio; `warranty_recovery.py` compat | `test_warranties.py` verde | Métricas requieren bridge REC-0004 (`CANCELADO` → rejected). Funcional, con deuda de normalización para R3. | **FUNCIONA** |
| 11 | Reparaciones / RMA | `/dashboard/repairs/*`: pendientes, en proceso, listas, entregadas, repuestos, presupuestos | `routers/repairs.py`, `rmas.py`; `models/repairs.py` | `test_repairs.py`, `test_rma_requests.py` verdes | Reparaciones tienen UI completa; RMA tiene backend probado pero no se identificó una ruta RMA dedicada equivalente. Debe decidirse si RMA queda absorbido por reparaciones o requiere UI canónica. | **REPARAR** |
| 12 | Transferencias | `/dashboard/operations/transferencias`; existe detalle `TransferDetailPage` | `routers/transfers.py`; `crud/transfers.py`; reservas/inventario/sync | `test_transfers.py`, `test_transfers_acceptance.py`, `test_transfers_get.py`, sync tests verdes | Flujo backend despacho/recepción es real, pero el detalle frontend ejecuta **Picking completado (simulado)** y **Packing completado (simulado)**; IMEI de vista se inicializa vacío. | **TERMINAR** |
| 13 | Sincronización / offline | `/dashboard/sync`; colas offline también usadas en POS/clientes | `routers/sync.py`, `models/sync.py`, `crud/sync.py`, `sync_recovery.py`, scheduler/provider | `test_sync_*` (conflicts, cycle, full, interface, offline, outbox, queue, replication, providers) verdes | Sync overview y outbox fueron recuperados mediante compatibilidad REC-0004. No hay fallo actual; sanear dependencia legacy en R3. | **FUNCIONA** |
| 14 | Reportes / analítica | `/dashboard/reports/*`, `/dashboard/analytics`; reportes globales y operativos | `routers/reports/*`, `reports_sales.py`; `crud/analytics.py`; exporters | `test_reports_*`, `test_global_reports.py`, `test_observability.py` verdes | Varias rutas históricas fueron restauradas en REC-0004. Queda deuda de consolidación, pero exports y cálculos están cubiertos. | **FUNCIONA** |
| 15 | Backups / restauración | API cliente en `frontend/src/api/system.ts`; no se confirmó módulo dashboard dedicado | `routers/backups.py`; `services/backups.py`, `backup_recovery.py`; artefactos/config | `test_backups.py` cubre generación, descarga y restauración y está verde | Generación manual usa wrapper de recuperación. Aún existen artefactos históricos bajo `backups/` en el árbol/historia y REC-0001 conserva trabajo de seguridad/rotación. No hay validación R8 en instalación limpia. | **REPARAR** |
| 16 | Importación / exportación | Herramientas dentro del inventario; import smart/catalog y exportaciones de reportes | routers `inventory_import.py`, `inventory_export.py`, `import_validation.py`; CRUD/servicios inventory | `test_catalog_pro.py`, `test_inventory_smart_import.py`, `test_inventory_export_formats.py`, `test_validacion_importacion.py`, report exports verdes | No se detectó mock bloqueante en el flujo activo. Hay componentes modales legacy que deben revisarse en R3/R7. | **FUNCIONA** |
| 17 | DTE / facturación / integraciones externas | `/dashboard/operations/dte`; integraciones y pagos desde operaciones/settings | `routers/dte.py`, `integrations.py`, `integration_hooks.py`, payments; `crud/invoicing.py`; adapters externos | `test_dte.py`, `test_integrations.py`, `test_integration_hooks.py`, `test_payments_adapters.py`, `test_fiscal_printers.py` verdes | Backend DTE exige venta real y cola; UI DTE lista autorizaciones reales, pero **Cargar nuevo CAF** y **Ver historial** no tienen acción. Algunos adapters/hardware trabajan en modo simulación cuando SDK/config no existe. Falta validación con proveedor/fiscal real. | **TERMINAR** |
| 18 | Observabilidad / logs / auditoría | `/dashboard/analytics`, `/dashboard/security`; módulos audit/support/help | `routers/monitoring.py`, `observability_admin.py`, `system_logs.py`, `audit.py`, `audit_ui.py`; modelos audit | `test_observability.py`, `test_system_logs.py`, `test_system_logs_rotation.py`, `test_audit*.py`, `test_support_feedback.py` verdes | Persisten warnings/deprecaciones y documentación histórica, pero no bloqueo funcional confirmado. | **FUNCIONA** |
| 19 | Instaladores / despliegue | Sin ruta runtime; empaquetado externo | `backend/Dockerfile`, `.devcontainer`, `installers/softmobile_backend.spec`, `installers/SoftmobileInstaller.iss`, scripts `ops/*` | CI valida backend/frontend, pero no ejecuta PyInstaller + Inno Setup en Windows | `installers/README.md` describe **plantillas** y ordena “ajusta las rutas”; R8 exige validar instalación/arranque Windows desde cero. No hay evidencia reproducible actual del instalador final. | **REPARAR** |

## Hallazgo transversal R3 — `crud_legacy` sigue activo

`backend/app/crud/__init__.py` importa `crud_legacy` mediante wildcard y después importa módulos especializados, además de reinyectar helpers/atributos de compatibilidad en dominios actuales. Esto fue necesario para recuperar el baseline, pero **no representa la arquitectura final**.

Dominios con compatibilidad explícita observada en `crud/__init__.py`:

- inventario y valuación;
- proveedores/compras;
- ventas/reservas;
- transferencias;
- clientes y ledgers;
- POS/store credit;
- sync;
- garantías;
- auditoría.

Regla para R3: no retirar ninguna función legacy sin identificar consumidores y mantener regresión verde.

## Candidatos `ELIMINAR` / consolidar en R3

Estos archivos no deben borrarse durante R2; quedan inventariados como candidatos:

1. `frontend/src/modules/inventory/pages/CycleCountPage.tsx`
   - contiene `TODO(wire)`;
   - no aparece en el router activo de dashboard;
   - búsqueda de referencias encuentra únicamente el propio archivo.
2. `frontend/src/modules/inventory/pages/StockLedgerPage.tsx`
   - contiene `TODO(wire)`;
   - no aparece en rutas activas;
   - sin consumidor detectado fuera de sí mismo.
3. `frontend/src/modules/inventory/pages/AdjustmentsPage.tsx`
   - contiene `TODO(wire)`;
   - no aparece en rutas activas;
   - sin consumidor detectado fuera de sí mismo.
4. `frontend/src/modules/sales/pages/OrderDetailPage.tsx`
   - contiene deuda `TODO(wire)` histórica;
   - no aparece en `sales/routes.tsx`;
   - sin consumidor detectado fuera del propio archivo/estilos.
5. POS duplicado:
   - `frontend/src/modules/operations/pages/OperationsPOS.tsx`;
   - `frontend/src/modules/sales/pages/POSPage.tsx`.
   - Ambos son rutas activas y ambos conectan backend; **no eliminar todavía**. R3 debe elegir implementación canónica y migrar consumidores.
6. Cierre de caja duplicado/parcial:
   - caja real existe dentro de `OperationsPOS`;
   - `sales/pages/CashClosePage.tsx` está enrutada pero es placeholder.
   - R3/R5 debe decidir consolidación y retirar el flujo ficticio.

## Backlog derivado por fase

### R3 — Arquitectura canónica

- Elegir POS canónico y retirar la segunda implementación solo tras migrar navegación/consumidores.
- Reducir `crud_legacy` por dominio, eliminando wildcard y bridges uno a uno con regresión.
- Resolver si RMA es subdominio de Reparaciones o módulo independiente.
- Confirmar y retirar páginas huérfanas de inventario/OrderDetail.
- Consolidar duplicidades de reportes/entrypoints cuando no aporten funciones distintas.

### R4 — GOLD flows

- Crear pruebas E2E/integración explícitas para GOLD-01 a GOLD-05; la suite actual cubre muchas piezas pero no sustituye una prueba GOLD nombrada de extremo a extremo.
- Confirmar atomicidad y trazabilidad en compra → inventario → POS, devolución, transferencia, caja y backup→restore.

### R5 — UI inconclusa

- Sustituir `CashClosePage` placeholder por flujo real o redirigir a caja canónica.
- Completar historial de compras en `CustomerDetailPage`.
- Conectar picking/packing real o retirar esos pasos del detalle de transferencia.
- Completar acciones DTE de carga CAF e historial.
- Revisar estados de error visual pendientes del POS secundario.

### R6 — Calidad/seguridad/datos

- Completar rotación/saneamiento de backups y secretos históricos de REC-0001.
- Revisar deprecaciones de Redis/fakeredis/cookies visibles en pytest.
- Validar integraciones fiscales/pagos/hardware contra proveedores o entorno sandbox real, no solo simuladores.

### R7 — Limpieza

- Borrar solo candidatos confirmados como huérfanos después de R3.
- Retirar notebooks/artefactos accidentales y documentación histórica redundante tras verificar valor de trazabilidad.

### R8 — Release

- Ejecutar PyInstaller + Inno Setup en Windows limpio.
- Probar instalación, arranque, configuración, backup/restore y smoke operativo desde cero.

## Estado de R2 tras esta matriz

Los 19 dominios mínimos del plan están clasificados. La matriz no declara el producto terminado: identifica qué funciona, qué debe repararse y qué UI debe completarse antes de los GOLD flows y la limpieza final.

Antes de cerrar REC-0006 falta una segunda pasada de evidencia para:

1. validar navegación/consumidores de todos los candidatos `ELIMINAR`;
2. confirmar cobertura frontend específica de cada ruta marcada `FUNCIONA`;
3. convertir los hallazgos `REPARAR`/`TERMINAR` de mayor impacto en issues trazables separados;
4. actualizar el tracker #756 con el resultado definitivo de R2.
