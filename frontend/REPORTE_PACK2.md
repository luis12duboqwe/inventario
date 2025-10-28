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

## Compatibilidad
- `RepairsPage.tsx` reexporta el nuevo layout para mantener el contrato del dashboard; no se modificaron stores ni servicios y las rutas `/dashboard/repairs/*` siguen operando sin cambios.
