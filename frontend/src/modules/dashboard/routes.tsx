import { Suspense, memo, type ReactNode, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import NotFound from "../../components/feedback/NotFound";
import { lazyWithRetry } from "../../shared/utils/lazyWithRetry";

const DashboardLayout = lazyWithRetry(() => import("./layout/DashboardLayout"));

const InventoryLayout = lazyWithRetry(() => import("../inventory/pages/InventoryLayout"));
// Usar las variantes *Page para permitir mocks de pruebas y loaders dedicados
const InventoryProducts = lazyWithRetry(() => import("../inventory/pages/InventoryProductsPage"));
const InventoryPriceLists = lazyWithRetry(() => import("../inventory/pages/InventoryPriceListsPage"));
const InventoryMoves = lazyWithRetry(() => import("../inventory/pages/InventoryMovementsPage"));
const InventorySuppliers = lazyWithRetry(() => import("../inventory/pages/InventorySuppliersPage"));
const InventoryAlerts = lazyWithRetry(() => import("../inventory/pages/InventoryAlertsPage"));
const InventoryReservations = lazyWithRetry(() => import("../inventory/pages/InventoryReservationsPage"));
const OperationsLayout = lazyWithRetry(() => import("../operations/pages/OperationsLayout"));
const OperationsPOS = lazyWithRetry(() => import("../operations/pages/OperationsPOS"));
const OperationsPurchases = lazyWithRetry(() => import("../operations/pages/OperationsPurchases"));
const OperationsReturns = lazyWithRetry(() => import("../operations/pages/OperationsReturns"));
const OperationsTransfers = lazyWithRetry(() => import("../operations/pages/OperationsTransfers"));
const OperationsWarranties = lazyWithRetry(() => import("../operations/pages/OperationsWarranties"));
const OperationsDiagnostics = lazyWithRetry(() => import("../operations/pages/OperationsDiagnostics"));
const OperationsBundles = lazyWithRetry(() => import("../operations/pages/OperationsBundles"));
const OperationsDte = lazyWithRetry(() => import("../operations/pages/OperationsDte"));
const AnalyticsPage = lazyWithRetry(() => import("../analytics/pages/AnalyticsPage"));
const SecurityPage = lazyWithRetry(() => import("../security/pages/SecurityPage"));
const SyncPage = lazyWithRetry(() => import("../sync/pages/SyncPage"));
const UsersPage = lazyWithRetry(() => import("../users/pages/UsersPage"));
const StoresPage = lazyWithRetry(() => import("../stores/pages/StoresPage"));
const MobileWorkspace = lazyWithRetry(() => import("../../mobile/MobileWorkspace"));
// Reparaciones: usar el alias RepairsPage para permitir el control de Suspense en pruebas
const RepairsPage = lazyWithRetry(() => import("../repairs/pages/RepairsPage"));
const RepairsPending = lazyWithRetry(() => import("../repairs/pages/RepairsPendingPage"));
const RepairsInProgress = lazyWithRetry(() => import("../repairs/pages/RepairsInProgressPage"));
const RepairsReady = lazyWithRetry(() => import("../repairs/pages/RepairsReadyPage"));
const RepairsDelivered = lazyWithRetry(() => import("../repairs/pages/RepairsDeliveredPage"));
const RepairsParts = lazyWithRetry(() => import("../repairs/pages/RepairsPartsPage"));
const RepairsBudgets = lazyWithRetry(() => import("../repairs/pages/RepairsBudgetsPage"));
const GlobalReportsPage = lazyWithRetry(() => import("../reports/pages/GlobalReportsPage"));
// [PACK29-*] Ruta autónoma de reportes operativos
const SalesReportsRoutes = lazyWithRetry(() => import("../reports/routes"));
const SalesModuleRoutes = lazyWithRetry(() => import("../sales/routes"));
import AppErrorBoundary from "../../shared/components/AppErrorBoundary"; // [PACK36-dashboard-routes]

type DashboardRoutesProps = {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  onLogout: () => void;
};

const allowedModules = new Set([
  "inventory",
  "operations",
  "analytics",
  "mobile",
  "reports",
  "security",
  "sync",
  "users",
  "stores",
  "repairs",
]);

function resolveInitialModule(): string {
  if (typeof window === "undefined") {
    return "inventory";
  }
  const stored = window.localStorage.getItem("softmobile_last_module");
  if (stored && stored.startsWith("/dashboard/")) {
    const slug = stored.replace("/dashboard/", "");
    if (allowedModules.has(slug)) {
      return slug;
    }
  }
  return "inventory";
}

const ModuleLoader = memo(function ModuleLoader() {
  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>Cargando panel…</span>
    </div>
  );
});

const ModuleBoundary = memo(function ModuleBoundary({ children }: { children: ReactNode }) {
  return <Suspense fallback={<ModuleLoader />}>{children}</Suspense>;
});

const DashboardRoutes = memo(function DashboardRoutes({ theme, onToggleTheme, onLogout }: DashboardRoutesProps) {
  const [initialModule] = useState(resolveInitialModule);

  return (
    <Routes>
        <Route
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Dashboard no disponible"
              description="Actualiza la página o vuelve más tarde mientras restablecemos el panel."
            >
              <DashboardLayout theme={theme} onToggleTheme={onToggleTheme} onLogout={onLogout} />
            </AppErrorBoundary>
          </ModuleBoundary>
        }
      >
        <Route index element={<Navigate to={initialModule} replace />} />
        <Route
          path="inventory/*"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Inventario no disponible"
                description="Revisa tu conexión y vuelve a intentarlo en unos momentos."
              >
                <InventoryLayout />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        >
          <Route index element={<Navigate to="productos" replace />} />
          <Route path="productos" element={<InventoryProducts />} />
          <Route path="listas-precios" element={<InventoryPriceLists />} />
          <Route path="movimientos" element={<InventoryMoves />} />
          <Route path="proveedores" element={<InventorySuppliers />} />
          <Route path="alertas" element={<InventoryAlerts />} />
          <Route path="reservas" element={<InventoryReservations />} />
          <Route path="listas" element={<InventoryPriceLists />} />
        </Route>
        <Route
          path="operations/*"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Operaciones con inconvenientes"
                description="Estamos recuperando el módulo de operaciones, intenta de nuevo pronto."
              >
                <OperationsLayout />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        >
          <Route index element={<Navigate to="pos" replace />} />
          <Route path="pos" element={<OperationsPOS />} />
          <Route path="compras" element={<OperationsPurchases />} />
          <Route path="devoluciones" element={<OperationsReturns />} />
          <Route path="garantias" element={<OperationsWarranties />} />
          <Route path="transferencias" element={<OperationsTransfers />} />
          <Route path="diagnosticos" element={<OperationsDiagnostics />} />
          <Route path="paquetes" element={<OperationsBundles />} />
          <Route path="dte" element={<OperationsDte />} />
        </Route>
        <Route
          path="mobile"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Módulo móvil fuera de línea"
                description="Revisa tu conexión y vuelve a intentarlo desde el dispositivo móvil."
              >
                <MobileWorkspace />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        />
        <Route
          path="/sales/*"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Ventas corporativas en pausa"
                description="Recarga el módulo de ventas o intenta más tarde."
              >
                <SalesModuleRoutes />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        />
        {/* // [PACK29-*] Soporte para /reports/* fuera del dashboard principal */}
        <Route
          path="/reports/*"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Reportes de ventas no disponibles"
                description="Revisamos el módulo de reportes, vuelve a intentarlo más tarde."
              >
                <SalesReportsRoutes />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        />
        <Route
          path="analytics"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Analítica momentáneamente fuera de línea"
                description="Vuelve a intentarlo en breve mientras restablecemos las métricas."
              >
                <AnalyticsPage />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        />
        <Route
          path="reports"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Reportes globales no disponibles"
                description="Estamos restableciendo los reportes corporativos, inténtalo nuevamente."
              >
                <GlobalReportsPage />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        />
        <Route
          path="security"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Seguridad temporalmente inactiva"
                description="Recarga la vista de seguridad o intenta más tarde."
              >
                <SecurityPage />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        />
        <Route
          path="sync"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Sincronización en revisión"
                description="Vuelve a intentar abrir el módulo de sincronización en unos segundos."
              >
                <SyncPage />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        />
        <Route
          path="users"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Usuarios no disponibles"
                description="Recarga para volver a gestionar usuarios cuando el módulo se recupere."
              >
                <UsersPage />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        />
        <Route
          path="stores"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Sucursales temporalmente no disponibles"
                description="Intenta nuevamente en unos momentos mientras restablecemos el módulo."
              >
                <StoresPage />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        />
        <Route
          path="repairs/*"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Reparaciones no disponibles"
                description="Espera un momento e intenta nuevamente ingresar a reparaciones."
              >
                <RepairsPage />
              </AppErrorBoundary>
            </ModuleBoundary>
          }
        >
          <Route index element={<Navigate to="pendientes" replace />} />
          <Route path="pendientes" element={<RepairsPending />} />
          <Route path="en-proceso" element={<RepairsInProgress />} />
          <Route path="listas" element={<RepairsReady />} />
          <Route path="entregadas" element={<RepairsDelivered />} />
          <Route path="repuestos" element={<RepairsParts />} />
          <Route path="presupuestos" element={<RepairsBudgets />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
});

export default DashboardRoutes;
