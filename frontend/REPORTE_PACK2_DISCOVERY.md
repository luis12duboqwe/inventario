# Softmobile 2025 — Pack 2A (Discovery)

## 1. Rutas actuales
- El `AppRouter` usa `createBrowserRouter` con dos ramas: `/login` para autenticación (envuelta en `Suspense`) y `/dashboard/*` para el panel principal; cualquier otra ruta redirige a `/dashboard/inventory`.【F:frontend/src/router/AppRouter.tsx†L15-L111】
- Dentro de `/dashboard/*`, `DashboardRoutes` monta `DashboardLayout`, envuelve cada módulo en `Suspense` y anida subrutas perezosas: `inventory/*` redirige a `productos` y expone `productos`, `movimientos`, `proveedores` y `alertas`, mientras que `operations/*` conserva los árboles de ventas, compras y logística; el resto de módulos (`analytics`, `reports`, `security`, `sync`, `users`, `repairs`) mantienen sus rutas directas.【F:frontend/src/modules/dashboard/routes.tsx†L1-L177】
- `DashboardLayout` actúa como layout global con sidebar, encabezado, barra de notificaciones y un `<Outlet />` para renderizar el módulo activo dentro del contenedor animado.【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L20-L200】【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L600-L638】

## 2. Archivos de página y componentes > 500 líneas
- `frontend/src/modules/operations/components/Purchases.tsx` (~1869 líneas) y `frontend/src/modules/operations/components/Customers.tsx` (~1689 líneas) continúan concentrando lógica compleja de compras y cartera.【F:frontend/src/modules/operations/components/Purchases.tsx†L1-L39】【F:frontend/src/modules/operations/components/Customers.tsx†L1-L39】
- `frontend/src/modules/inventory/pages/useInventoryLayoutState.tsx` (~847 líneas) centraliza el estado global, descargas, métricas y helpers del módulo de inventario tras la división en subpáginas.【F:frontend/src/modules/inventory/pages/useInventoryLayoutState.tsx†L1-L80】
- `frontend/src/modules/dashboard/layout/DashboardLayout.tsx` (638 líneas) sigue controlando navegación, shell visual y toasts del panel principal.【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L33-L200】
- Otros componentes extensos detectados: `frontend/src/modules/users/components/UserManagement.tsx` (~1050), `frontend/src/modules/sync/pages/SyncPage.tsx` (~978), `frontend/src/modules/operations/components/POS/POSDashboard.tsx` (~972), `frontend/src/modules/operations/components/Sales.tsx` (~871) y `frontend/src/modules/repairs/components/RepairOrders.tsx` (~827).【F:frontend/src/modules/users/components/UserManagement.tsx†L1-L40】【F:frontend/src/modules/sync/pages/SyncPage.tsx†L1-L40】【F:frontend/src/modules/operations/components/POS/POSDashboard.tsx†L1-L40】【F:frontend/src/modules/operations/components/Sales.tsx†L1-L40】【F:frontend/src/modules/repairs/components/RepairOrders.tsx†L1-L40】

## 3. Lazy/Suspense existente
- Rutas principales y escenas de autenticación usan `React.lazy` y `Suspense` para cargar formularios, dashboard y módulos de negocio.【F:frontend/src/router/AppRouter.tsx†L15-L111】
- `DashboardRoutes` aplica un `ModuleBoundary` (Suspense) alrededor del layout y de cada módulo hijo, asegurando loaders por sección.【F:frontend/src/modules/dashboard/routes.tsx†L1-L177】
- `OperationsPage` ya carga cada panel (clientes, proveedores, POS, compras, ventas, devoluciones, transferencias, movimientos internos e historial) con `React.lazy` y Suspense puntuales.【F:frontend/src/modules/operations/pages/OperationsPage.tsx†L1-L172】
- `InventoryPage` ahora funciona como layout: envuelve el `<Outlet />` de las subrutas en `Suspense` con el loader corporativo y mantiene un `lazy` para `DeviceEditDialog` dentro de un segundo `Suspense`.【F:frontend/src/modules/inventory/pages/InventoryPage.tsx†L1-L66】

## 4. Layouts detectados
- `DashboardLayout` proporciona el shell único del dashboard (sidebar con permisos por flag, barra superior, acciones rápidas, toasts, buscador global) y aloja el `<Outlet />` que renderiza cada módulo.【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L20-L200】【F:frontend/src/modules/dashboard/layout/DashboardLayout.tsx†L600-L638】
- Inventario y Operaciones ahora tienen layouts propios: `InventoryPage` provee `InventoryLayoutContext`, Tabs y el `<Outlet />` de subrutas, mientras que `OperationsPage` renderiza la navegación interna y delega su contenido a `Outlet` dentro de `Suspense`.【F:frontend/src/modules/inventory/pages/InventoryPage.tsx†L14-L66】【F:frontend/src/modules/inventory/pages/context/InventoryLayoutContext.tsx†L1-L89】【F:frontend/src/modules/operations/pages/OperationsPage.tsx†L65-L148】

## 5. Stores y contextos en uso
- `DashboardContext` centraliza estado global (token, flags de features, tiendas, métricas, usuario, toasts, outbox, historial de sincronización) y utilidades como `refreshInventoryAfterTransfer` y `formatCurrency`. Todos los módulos consumen este contexto para acceder a datos y acciones compartidas.【F:frontend/src/modules/dashboard/context/DashboardContext.tsx†L1-L206】
- `useInventoryModule`, `useOperationsModule` y `useRepairsModule` son hooks delgados que exponen fragmentos del contexto para cada página, reutilizando token, tiendas, sucursal seleccionada y helpers corporativos.【F:frontend/src/modules/inventory/hooks/useInventoryModule.ts†L11-L200】【F:frontend/src/modules/operations/hooks/useOperationsModule.ts†L1-L13】【F:frontend/src/modules/repairs/hooks/useRepairsModule.ts†L1-L13】
- No se detectaron stores externos (Zustand/Redux); el estado compartido depende de React Context y React Query dentro del router principal.【F:frontend/src/router/AppRouter.tsx†L1-L111】【F:frontend/src/modules/dashboard/context/DashboardContext.tsx†L1-L206】

## 6. Servicios API y endpoints
- `frontend/src/services/api/http.ts` define el cliente Axios con base URL configurable (`VITE_API_URL` o `getApiBaseUrl`), almacenamiento de token en `localStorage`, refresco automático en `/auth/refresh` y evento global `softmobile:unauthorized` para cerrar sesión sincronizadamente.【F:frontend/src/services/api/http.ts†L1-L139】
- Los servicios específicos viven en `frontend/src/services/api/` (`auth.ts`, `inventory.ts`, `pos.ts`, `stores.ts`) y se consumen desde hooks o módulos especializados.【F:frontend/src/services/api/auth.ts†L1-L32】【F:frontend/src/services/api/inventory.ts†L1-L68】【F:frontend/src/services/api/pos.ts†L1-L60】【F:frontend/src/services/api/stores.ts†L1-L44】
- El módulo de inventario encapsula todas las llamadas corporativas en `inventoryService` (reportes, exportaciones, importaciones inteligentes, lotes por proveedor, movimientos) reutilizando funciones del SDK interno `frontend/src/api.ts`.【F:frontend/src/modules/inventory/services/inventoryService.ts†L1-L167】

## 7. Plan actualizado por módulo
### Inventario (`/dashboard/inventory/*`)
- Estado actual: `InventoryPage` ya funciona como layout con Tabs, `InventoryLayoutContext` y `<Outlet />`; las subrutas `productos`, `movimientos`, `proveedores` y `alertas` cargan pantallas dedicadas con `PageHeader`/`PageToolbar` y secciones desacopladas (`InventoryStatusSection`, `InventoryMovementsTimelineSection`, etc.).【F:frontend/src/modules/inventory/pages/InventoryPage.tsx†L14-L66】【F:frontend/src/modules/inventory/pages/InventoryProductsPage.tsx†L1-L44】【F:frontend/src/modules/inventory/pages/InventoryMovementsPage.tsx†L1-L18】【F:frontend/src/modules/inventory/pages/components/InventoryStatusSection.tsx†L1-L120】
- Próximos pasos: actualizar las pruebas de `InventoryPage` para apuntar a las nuevas rutas/componentes y validar que `useInventoryLayoutState` siga cubriendo todos los flujos (descargas, importaciones inteligentes, métricas).【F:frontend/src/modules/inventory/pages/__tests__/InventoryPage.test.tsx†L1-L40】【F:frontend/src/modules/inventory/pages/useInventoryLayoutState.tsx†L1-L80】

### Operaciones (`/dashboard/operations/*`)
- Estado actual: `OperationsPage` actúa como layout con navegación interna y `Suspense`; el router ya entrega subrutas para ventas, compras y logística con componentes perezosos (`CajaPage`, `OrdenesPage`, `TransferenciasPage`, etc.).【F:frontend/src/modules/operations/pages/OperationsPage.tsx†L65-L148】【F:frontend/src/modules/dashboard/routes.tsx†L99-L123】
- Próximos pasos: revisar si los submódulos requieren pruebas dedicadas tras el cambio de rutas y documentar capturas de la navegación completa.

### Reparaciones (`/dashboard/repairs` → `/reparaciones/...`)
- Plan pendiente: introducir `<Outlet />` dentro de `RepairsPage` y dividir `RepairOrders` en subcomponentes/rutas (`pendientes`, `finalizadas`, `repuestos`, `presupuestos`) preservando filtros, exportaciones y callbacks existentes.【F:frontend/src/modules/repairs/pages/RepairsPage.tsx†L1-L44】【F:frontend/src/modules/repairs/components/RepairOrders.tsx†L200-L823】
- Fragmentar `RepairOrders` (>800 líneas) en contenedores (`RepairFilters`, `RepairForm`, `RepairTable`, `RepairSummary`) ubicados en `pages/repairs/components/` manteniendo props (`onStatusChange`, `onInventoryRefresh`) para no romper integraciones con inventario y POS.【F:frontend/src/modules/repairs/components/RepairOrders.tsx†L200-L823】

## 8. Scaffolding creado en este pack
- Se añadieron componentes neutros `PageHeaderSM`, `PageToolbarSM` y `Loader` (re-export) en `frontend/src/components/` para estandarizar encabezados, toolbars y loaders en iteraciones posteriores sin interferir con los componentes actuales bajo `shared/components/`.【F:frontend/src/components/layout/PageHeader.tsx†L1-L100】【F:frontend/src/components/layout/PageToolbar.tsx†L1-L82】【F:frontend/src/components/common/Loader.tsx†L1-L10】
- Estos componentes aceptan `title`, `subtitle`, `actions`, `onSearch` y `filters`, cumpliendo el contrato solicitado y quedando listos para integrarse a las nuevas subrutas.

