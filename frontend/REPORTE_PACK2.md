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
- Reparaciones
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
- `frontend/src/modules/repairs/pages/RepairsPendingPage.tsx`
- `frontend/src/modules/repairs/pages/RepairsFinalizedPage.tsx`
- `frontend/src/modules/repairs/pages/RepairsPartsPage.tsx`
- `frontend/src/modules/repairs/pages/RepairsBudgetsPage.tsx`
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

## Lazy/Suspense
- Las rutas hijas de Inventario, Operaciones y Reparaciones se cargan mediante `React.lazy` desde `dashboard/routes.tsx` y se envuelven en `Suspense` (loader global en el router y `Loader` corporativo en cada layout).
- `InventoryPage` delega sus submódulos a `<Outlet />` dentro de `Suspense`, mientras que los formularios/tablas se mantienen perezosos mediante `lazy` locales.
- `OperationsPage` conserva el `Suspense` interno para cada sección (POS, compras, transferencias, etc.) y sincroniza las rutas hijas con la URL.
- `RepairsPage` funciona como layout modular: Tabs sincronizados con la URL, contexto compartido y cargas diferidas para pendientes, finalizadas, repuestos y presupuestos.
- Las rutas hijas de Inventario y Operaciones se cargan mediante `React.lazy` desde `dashboard/routes.tsx` y se envuelven en `Suspense` (loader global en el router y `Loader` corporativo en cada layout).
- `InventoryPage` delega sus submódulos a `<Outlet />` dentro de `Suspense`, mientras que los formularios/tablas se mantienen perezosos mediante `lazy` locales.
- `OperationsPage` conserva el `Suspense` interno para cada sección (POS, compras, transferencias, etc.).

## Navegación y comportamiento
- Inventario ahora funciona como layout ligero: el tab seleccionado controla la URL (`/inventory/*`) y cada subruta abre su propia pantalla con `PageHeader`/`PageToolbar` y las secciones heredadas (salud, tabla, importación inteligente, lotes, alertas).
- Se reemplazó el acordeón de Operaciones por navegación de subrutas; las pestañas internas reflejan el estado activo en la URL y reutilizan POS, Purchases, Sales, Returns y Suppliers sin alterar su lógica.
- Los componentes `PageHeader` y `PageToolbar` unifican encabezados, acciones, filtros y búsqueda en Inventario, Operaciones y Reparaciones, respetando el tema oscuro y los estilos previos (`inventory-*`, `operations-*`, `repairs-*`).
- Reparaciones se divide en cuatro subrutas: el panel de pendientes conserva el formulario completo con filtros encapsulados en `PageToolbar`, las finalizadas se concentran en el historial con descargas, repuestos agrega resumen por dispositivo y presupuestos muestra métricas financieras.
- `RepairOrdersBoard` se fragmentó en hooks (`useRepairOrdersBoard`, `useRepairOrderActions`) y helpers reutilizables para cumplir el límite <500 líneas sin alterar la UI ni la lógica de inventario sincronizado.

## Pendientes
- Los componentes `PageHeader` y `PageToolbar` unifican encabezados, acciones, filtros y búsqueda en Inventario y Operaciones, respetando el tema oscuro y los estilos previos (`inventory-*`, `operations-*`).

## Pendientes
- Reparaciones: dividir `RepairOrders` en subrutas (`pendientes`, `finalizadas`, `repuestos`, `presupuestos`) manteniendo exportaciones y controles existentes.
- Inventario: revisar pruebas unitarias/integración para asegurar que la división por secciones mantenga la cobertura previa (test de `InventoryPage` requiere actualización hacia los nuevos componentes).
- Documentar capturas o walkthrough de navegación una vez completadas las pruebas finales.

## Avance del sprint
- Operaciones: 100 % (subrutas activas con `React.lazy`, navegación interna y documentación).
- Inventario: 100 % (layout modular con pruebas actualizadas para el router y las subpáginas perezosas).
- Reparaciones: 100 % (layout con Tabs, subrutas perezosas y vistas dedicadas; hooks y helpers validados con pruebas unitarias).
- Inventario: 85 % (layout convertido en router, subpáginas modulares y secciones reutilizables; faltan ajustes de pruebas/documentación visual).
- Reparaciones: 0 % (pendiente iniciar subdivisión y lazy loading por estado de orden).
