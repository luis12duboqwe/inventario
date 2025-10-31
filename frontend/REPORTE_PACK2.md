# Softmobile 2025 — Pack 2 (Frontend)

## Subrutas creadas por módulo
- Inventario
  - `/dashboard/inventory/productos`
  - `/dashboard/inventory/movimientos`
  - `/dashboard/inventory/proveedores`
  - `/dashboard/inventory/alertas`
- Operaciones → Ventas
  - `/dashboard/operations/ventas/caja`
  - `/dashboard/operations/ventas/facturacion`
  - `/dashboard/operations/ventas/clientes`
  - `/dashboard/operations/ventas/cajas`
- Operaciones → Compras
  - `/dashboard/operations/compras/ordenes`
  - `/dashboard/operations/compras/pagos`
  - `/dashboard/operations/compras/proveedores`
- Operaciones → Logística
  - `/dashboard/operations/movimientos/internos`
  - `/dashboard/operations/movimientos/transferencias`
- Reparaciones (`/dashboard/repairs/*` servido desde 
  `frontend/src/pages/reparaciones`)
  - `/dashboard/repairs/pendientes`
  - `/dashboard/repairs/finalizadas`
  - `/dashboard/repairs/repuestos`
  - `/dashboard/repairs/presupuestos`

## Archivos nuevos o modificados
- `frontend/src/modules/dashboard/routes.tsx`
- `frontend/src/modules/inventory/pages/InventoryPage.tsx`
- `frontend/src/modules/inventory/pages/InventoryProductsPage.tsx`
- `frontend/src/modules/inventory/pages/InventoryMovementsPage.tsx`
- `frontend/src/modules/inventory/pages/InventorySuppliersPage.tsx`
- `frontend/src/modules/inventory/pages/InventoryAlertsPage.tsx`
- `frontend/src/modules/inventory/pages/components/*`
- `frontend/src/modules/inventory/pages/context/InventoryLayoutContext.tsx`
- `frontend/src/modules/inventory/pages/useInventoryLayoutState.tsx`
- `frontend/src/modules/inventory/pages/hooks/useSmartImportManager.ts`
- `frontend/src/modules/operations/pages/OperationsPage.tsx`
- `frontend/src/modules/operations/pages/ventas/CajaPage.tsx`
- `frontend/src/modules/operations/pages/ventas/FacturacionPage.tsx`
- `frontend/src/modules/operations/pages/ventas/ClientesPage.tsx`
- `frontend/src/modules/operations/pages/ventas/CajasPage.tsx`
- `frontend/src/modules/operations/pages/compras/OrdenesPage.tsx`
- `frontend/src/modules/operations/pages/compras/PagosPage.tsx`
- `frontend/src/modules/operations/pages/compras/ProveedoresPage.tsx`
- `frontend/src/modules/operations/pages/movimientos/InternosPage.tsx`
- `frontend/src/modules/operations/pages/movimientos/TransferenciasPage.tsx`
- `frontend/src/modules/repairs/pages/RepairsPage.tsx`
- `frontend/src/pages/reparaciones/ReparacionesLayout.tsx`
- `frontend/src/pages/reparaciones/Pendientes.tsx`
- `frontend/src/pages/reparaciones/Finalizadas.tsx`
- `frontend/src/pages/reparaciones/Repuestos.tsx`
- `frontend/src/pages/reparaciones/Presupuestos.tsx`
- `frontend/src/modules/repairs/pages/components/*`
- `frontend/src/modules/repairs/pages/components/useRepairOrderActions.ts`
- `frontend/src/modules/repairs/pages/components/useRepairOrdersBoard.ts`
- `frontend/src/modules/repairs/pages/components/createRepairRowRenderer.tsx`
- `frontend/src/modules/repairs/pages/components/repairOrdersBoardConstants.ts`
- `frontend/src/modules/repairs/pages/context/RepairsLayoutContext.tsx`
- `frontend/src/components/layout/PageHeader.tsx`
- `frontend/src/components/layout/PageToolbar.tsx`
- `frontend/src/components/common/Loader.tsx`
- `frontend/src/styles.css`

## Operaciones — Compras y Clientes

### Inventario de bloques previos
- `frontend/src/modules/operations/components/Purchases.tsx` concentraba:
  - Formulario de registro directo de compras con cálculo de impuestos y selección de sucursal/dispositivo.
  - Filtros, exportaciones y tabla histórica de compras registradas.
  - Panel completo de proveedores (alta/edición, filtros, exportación CSV, detalle con historial y métricas).
  - Tarjetas de estadísticas de compras (totales, rankings y serie mensual).
  - Gestión de órdenes de compra con plantillas recurrentes, importación CSV y tabla de seguimiento.
- `frontend/src/modules/operations/components/Customers.tsx` reunía:
  - Formulario de altas/edición con notas, motivo corporativo y exportación CSV.
  - Filtros rápidos, contadores y tabla con acciones de perfil, notas, pagos y ajustes.
  - Panel lateral con resumen financiero, ventas/pagos/notas, historial de contacto y bitácora.
  - Sección de portafolio corporativo y dashboard de métricas con controles propios.

### Nueva estructura de componentes
- Compras (`frontend/src/pages/operaciones/purchases/components/`):
  - `Toolbar.tsx`: alertas de error/éxito reutilizables en el módulo.
  - `FormModal.tsx`: UI del registro directo de compras y totales calculados.
  - `FiltersPanel.tsx`: filtros de historial y accesos a exportaciones.
  - `Table.tsx`: tabla responsiva con el historial de compras.
  - `SidePanel.tsx`: administración de proveedores, filtros y detalle con historial.
  - `SummaryCards.tsx`: tarjetas de estadísticas de compras.
  - `OrdersPanel.tsx`: formulario de órdenes, plantillas recurrentes, importación y tabla de seguimiento.
- Clientes (`frontend/src/pages/operaciones/customers/components/`):
  - `Toolbar.tsx`: contenedor de alertas del módulo.
  - `FormModal.tsx`: formulario de clientes con control de estado y exportación CSV.
  - `FiltersPanel.tsx`: búsqueda rápida, filtros combinados y contadores.
  - `Table.tsx`: tabla de clientes con acciones (perfil, nota, pago, ajuste, eliminación).
  - `SidePanel.tsx`: resumen financiero, ventas/pagos/notas y bitácora con detalle accesible.
  - `SummaryCards.tsx`: portafolio corporativo y dashboard de métricas con controles.

### Ensamblaje en contenedores
- `Purchases.tsx` conserva efectos, servicios y validaciones corporativas, delegando toda la presentación a los nuevos subcomponentes y encapsulando la orquestación en `usePurchasesController.ts` (archivo local que concentra estado y manejadores sin exponer contratos globales).
- `Customers.tsx` mantiene la lógica de datos (fetching, validaciones, notas y operaciones financieras), delega la interfaz a los subcomponentes y apoya la coordinación en `useCustomersController.ts`, garantizando motivos corporativos y selectores derivados sin mezclar UI con servicios.

### Reducción del tamaño de contenedores
- `Purchases.tsx` pasó de ~1 050 líneas a 213 líneas gracias a la separación del controlador interno.
- `Customers.tsx` pasó de ~840 líneas a 168 líneas manteniendo intactos los contratos de rutas y props.

### Verificación
- `npm --prefix frontend run build`
- `pytest`

## Reparaciones

### Nueva estructura de rutas
- `/dashboard/repairs` sirve como layout con `<Outlet />` y redirige su índice a
  `/dashboard/repairs/pendientes`.
- Subrutas disponibles: `pendientes`, `finalizadas`, `repuestos` y `presupuestos`,
  todas cargadas con `React.lazy` y envueltas por `<Suspense>`.
- La navegación superior usa `NavLink` para reflejar la URL activa y conserva el
  estado global del módulo (token, sucursal, inventario, indicadores).

### Archivos creados o modificados
- `frontend/src/modules/dashboard/routes.tsx`
- `frontend/src/modules/repairs/pages/RepairsPage.tsx`
- `frontend/src/pages/reparaciones/ReparacionesLayout.tsx`
- `frontend/src/pages/reparaciones/Pendientes.tsx`
- `frontend/src/pages/reparaciones/Finalizadas.tsx`
- `frontend/src/pages/reparaciones/Repuestos.tsx`
- `frontend/src/pages/reparaciones/Presupuestos.tsx`
- `frontend/src/modules/repairs/pages/RepairsPendingPage.tsx`
- `frontend/src/modules/repairs/pages/RepairsFinalizedPage.tsx`
- `frontend/src/modules/repairs/pages/RepairsPartsPage.tsx`
- `frontend/src/modules/repairs/pages/RepairsBudgetsPage.tsx`
- `frontend/src/modules/repairs/pages/context/RepairsLayoutContext.tsx`
- `frontend/src/modules/repairs/pages/components/RepairOrdersBoard.tsx`
- `frontend/src/components/layout/PageHeader.tsx`
- `frontend/src/components/layout/PageToolbar.tsx`
- `frontend/src/components/common/Loader.tsx`
- `frontend/src/styles.css`

### Lazy y `<Suspense>`
- `dashboard/routes.tsx` delega cada subruta de reparaciones mediante `React.lazy`
  y `ModuleBoundary` (que a su vez utiliza `<Suspense>`).
- `ReparacionesLayout` envuelve `<Outlet />` con `<Suspense>` y reutiliza el
  `Loader` corporativo.
- Las subpáginas (`Pendientes`, `Finalizadas`, `Repuestos`, `Presupuestos`)
  mantienen cargas diferidas y encapsulan filtros/acciones dentro de
  `PageToolbar` locales para evitar montajes innecesarios.

### Compatibilidad
- No se modificaron stores ni servicios globales; `useRepairsModule` expone el
  mismo contrato que consumían las pantallas originales.
- Los callbacks de inventario y los indicadores del módulo se propagan a través
  de `RepairsLayoutContext`, conservando actualizaciones de estado en tiempo real.
- El diseño respeta el tema oscuro y los estilos previos (`reparaciones-*`) y
  añade clases específicas solo para el layout de pestañas.

### Avance
- Reparaciones: 100 % — layout centralizado, subrutas perezosas y documentación
  actualizada sin romper integraciones existentes.

### Modularización UI — Reparaciones
- `RepairOrdersBoard.tsx` conserva la lógica de datos y delega la interfaz en
  `frontend/src/pages/reparaciones/components/{FiltersPanel.tsx, RepairTable.tsx,
  SidePanel.tsx, Toolbar.tsx, BudgetModal.tsx, PartsModal.tsx}` para dividir filtros,
  formulario, tabla y modales de detalle.
- Los formularios y tablas reutilizan los tipos declarados en
  `frontend/src/types/repairs.d.ts`, manteniendo intactos los contratos de los
  servicios (`RepairForm`, `RepairPartForm`).

## Compatibilidad
- `RepairsPage.tsx` reexporta el nuevo layout para mantener el contrato del dashboard; no se modificaron stores ni servicios y las rutas `/dashboard/repairs/*` siguen operando sin cambios.

## Sincronización

### Modularización del panel híbrido
- `SyncPage.tsx` pasó de 978 a 880 líneas al mover el dashboard y las acciones a
  `frontend/src/pages/sync/components/{SyncSummary.tsx, SyncActions.tsx, LogsTable.tsx}`
  manteniendo la lógica de datos, descargas y validaciones corporativas en el
  contenedor.
- Los reportes de respaldo y la tabla de outbox se nutren de los tipos
  centralizados en `frontend/src/types/sync.d.ts`, garantizando contratos
  consistentes para logs recientes y respaldos (`RecentSyncLog`, `SyncBackupEntry`).

## Cierre

### Modularización completada
- **Usuarios — `UserManagement.tsx`:** 1050 → 540 líneas. Se trasladó la interfaz a `frontend/src/pages/usuarios/components/` con los componentes `Toolbar.tsx`, `SummaryCards.tsx`, `FiltersPanel.tsx`, `Table.tsx`, `SidePanel.tsx`, `PermissionMatrix.tsx` y `RoleModal.tsx`, conservando el contenedor como orquestador de datos y flujos corporativos.
- **POS — `POSDashboard.tsx`:** 972 → 201 líneas. La vista delega toda la interfaz en `frontend/src/pages/pos/components/{Toolbar.tsx, QuickSaleForm.tsx, ProductGrid.tsx, CartPanel.tsx, PaymentModal.tsx, ReceiptPreview.tsx}` y mueve la orquestación de estado a `frontend/src/modules/operations/components/POS/usePosDashboardController.ts`, que concentra efectos, sincronización, ventas y sesiones de caja sin exponer contratos nuevos.
- **Ventas — `Sales.tsx`:** 871 → 497 líneas. El contenedor traslada la interfaz a `frontend/src/pages/ventas/components/{Toolbar.tsx, FiltersPanel.tsx, SummaryCards.tsx, SalesTable.tsx, SidePanel.tsx, InvoiceModal.tsx}`, incorpora un modal de factura previo a la descarga y conserva hooks, servicios POS y validaciones de motivo corporativo.
- **Reparaciones — `RepairOrdersBoard.tsx`:** mantiene 188 líneas enfocadas en la orquestación y delega filtros, tabla, panel
  lateral y modales en `frontend/src/pages/reparaciones/components/{FiltersPanel.tsx, RepairTable.tsx, SidePanel.tsx,
  Toolbar.tsx, BudgetModal.tsx, PartsModal.tsx}`.
- **Sincronización — `SyncPage.tsx`:** 978 → 880 líneas. El dashboard, la sección de acciones y la tabla de outbox migran a
  `frontend/src/pages/sync/components/{SyncSummary.tsx, SyncActions.tsx, LogsTable.tsx}` mientras el contenedor conserva la
  lógica de sincronización híbrida.

### Archivos a modular — Cierre
| Archivo | Líneas |
| --- | ---: |
| `frontend/src/pages/operaciones/purchases/components/SidePanel.tsx` | 377 |
| `frontend/src/pages/operaciones/customers/components/SummaryCards.tsx` | 347 |
| `frontend/src/pages/pos/components/PaymentModal.tsx` | 340 |
| `frontend/src/pages/operaciones/purchases/components/OrdersPanel.tsx` | 298 |
| `frontend/src/pages/ventas/components/SidePanel.tsx` | 292 |

### Higiene y telemetría
- Se reemplazaron los `console.*` de autenticación y QR por el nuevo emisor `softmobile:client-log` definido en
  `frontend/src/utils/clientLog.ts`, evitando ruido en consola y conservando trazabilidad mediante eventos personalizados.
- `frontend/src/services/api/http.ts` reporta fallas al leer o persistir el token con `emitClientWarning`,
  manteniendo el estado en memoria aunque `localStorage` falle.
- `frontend/src/modules/inventory/components/InventoryTable.tsx` usa `emitClientError` y alerta en la UI cuando la generación de códigos QR no es posible.

### Validación de rutas y lazy loading
- Nuevas suites Vitest:
  - `frontend/src/__tests__/routes/inventario.routes.test.tsx`
  - `frontend/src/__tests__/routes/reparaciones.routes.test.tsx`
- Ambas prueban el render “smoke” de `/dashboard/inventory/*` y `/dashboard/repairs/*`, verifican que los índices redirigen a sus subrutas por defecto y afirman que los `<Suspense>` muestran los loaders corporativos durante la carga perezosa.
- Resultado: `npm --prefix frontend run test -- src/__tests__/routes/inventario.routes.test.tsx src/__tests__/routes/reparaciones.routes.test.tsx` en verde.
