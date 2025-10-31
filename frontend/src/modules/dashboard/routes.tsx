import { Suspense, lazy, memo, type ReactNode, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import NotFound from "../../components/feedback/NotFound";
const DashboardLayout = lazy(() => import("./layout/DashboardLayout"));

const InventoryLayout = lazy(() => import("../inventory/pages/InventoryLayout"));
const InventoryProducts = lazy(() => import("../inventory/pages/InventoryProducts"));
const InventoryMoves = lazy(() => import("../inventory/pages/InventoryMovements"));
const InventorySuppliers = lazy(() => import("../inventory/pages/InventorySuppliers"));
const InventoryAlerts = lazy(() => import("../inventory/pages/InventoryAlerts"));
const OperationsLayout = lazy(() => import("../operations/pages/OperationsLayout"));
const OperationsPOS = lazy(() => import("../operations/pages/OperationsPOS"));
const OperationsPurchases = lazy(() => import("../operations/pages/OperationsPurchases"));
const OperationsReturns = lazy(() => import("../operations/pages/OperationsReturns"));
const OperationsTransfers = lazy(() => import("../operations/pages/OperationsTransfers"));
const AnalyticsPage = lazy(() => import("../analytics/pages/AnalyticsPage"));
const SecurityPage = lazy(() => import("../security/pages/SecurityPage"));
const SyncPage = lazy(() => import("../sync/pages/SyncPage"));
const UsersPage = lazy(() => import("../users/pages/UsersPage"));
const RepairsLayout = lazy(() => import("../repairs/pages/RepairsLayout"));
const RepairsPending = lazy(() => import("../repairs/pages/RepairsPendingPage"));
const RepairsInProgress = lazy(() => import("../repairs/pages/RepairsInProgressPage"));
const RepairsReady = lazy(() => import("../repairs/pages/RepairsReadyPage"));
const RepairsDelivered = lazy(() => import("../repairs/pages/RepairsDeliveredPage"));
const RepairsParts = lazy(() => import("../repairs/pages/RepairsPartsPage"));
const RepairsBudgets = lazy(() => import("../repairs/pages/RepairsBudgetsPage"));
const GlobalReportsPage = lazy(() => import("../reports/pages/GlobalReportsPage"));
// [PACK29-*] Ruta autónoma de reportes operativos
const SalesReportsRoutes = lazy(() => import("../reports/routes"));
const SalesModuleRoutes = lazy(() => import("../sales/routes"));
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
  "reports",
  "security",
  "sync",
  "users",
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
          <Route path="movimientos" element={<InventoryMoves />} />
          <Route path="proveedores" element={<InventorySuppliers />} />
          <Route path="alertas" element={<InventoryAlerts />} />
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
          <Route path="transferencias" element={<OperationsTransfers />} />
        </Route>
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
          path="repairs/*"
          element={
            <ModuleBoundary>
              {/* [PACK36-dashboard-routes] */}
              <AppErrorBoundary
                variant="inline"
                title="Reparaciones no disponibles"
                description="Espera un momento e intenta nuevamente ingresar a reparaciones."
              >
                <RepairsLayout />
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
