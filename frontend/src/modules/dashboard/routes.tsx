import { Suspense, lazy, memo, type ReactNode, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import NotFound from "../../components/feedback/NotFound";
const DashboardLayout = lazy(() => import("./layout/DashboardLayout"));

const InventoryLayout = lazy(() => import("../inventory/pages/InventoryLayout"));
const InventoryProducts = lazy(() => import("../inventory/pages/InventoryProducts"));
const InventoryMoves = lazy(() => import("../inventory/pages/InventoryMovements"));
const InventorySuppliers = lazy(() => import("../inventory/pages/InventorySuppliers"));
const InventoryAlerts = lazy(() => import("../inventory/pages/InventoryAlerts"));
const InventoryAdjustments = lazy(() => import("../inventory/pages/InventoryAdjustments"));
const InventoryTransfers = lazy(() => import("../inventory/pages/InventoryTransfers"));
const InventoryCycleCount = lazy(() => import("../inventory/pages/InventoryCycleCount"));
const InventoryTransferDetail = lazy(() => import("../inventory/pages/TransferDetailPage"));
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
const RepairsPending = lazy(() => import("../repairs/pages/RepairsPending"));
const RepairsCompleted = lazy(() => import("../repairs/pages/RepairsCompleted"));
const RepairsParts = lazy(() => import("../repairs/pages/RepairsParts"));
const RepairsBudgets = lazy(() => import("../repairs/pages/RepairsBudgets"));
const GlobalReportsPage = lazy(() => import("../reports/pages/GlobalReportsPage"));

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
            <DashboardLayout theme={theme} onToggleTheme={onToggleTheme} onLogout={onLogout} />
          </ModuleBoundary>
        }
      >
        <Route index element={<Navigate to={initialModule} replace />} />
        <Route
          path="inventory/*"
          element={
            <ModuleBoundary>
              <InventoryLayout />
            </ModuleBoundary>
          }
        >
          <Route index element={<Navigate to="productos" replace />} />
          <Route path="productos" element={<InventoryProducts />} />
          <Route path="movimientos" element={<InventoryMoves />} />
          <Route path="proveedores" element={<InventorySuppliers />} />
          <Route path="alertas" element={<InventoryAlerts />} />
          <Route path="ajustes" element={<InventoryAdjustments />} />
          <Route path="transferencias" element={<InventoryTransfers />} />
          <Route path="transferencias/:transferId" element={<InventoryTransferDetail />} />
          <Route path="conteos" element={<InventoryCycleCount />} />
        </Route>
        <Route
          path="operations/*"
          element={
            <ModuleBoundary>
              <OperationsLayout />
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
          path="analytics"
          element={
            <ModuleBoundary>
              <AnalyticsPage />
            </ModuleBoundary>
          }
        />
        <Route
          path="reports"
          element={
            <ModuleBoundary>
              <GlobalReportsPage />
            </ModuleBoundary>
          }
        />
        <Route
          path="security"
          element={
            <ModuleBoundary>
              <SecurityPage />
            </ModuleBoundary>
          }
        />
        <Route
          path="sync"
          element={
            <ModuleBoundary>
              <SyncPage />
            </ModuleBoundary>
          }
        />
        <Route
          path="users"
          element={
            <ModuleBoundary>
              <UsersPage />
            </ModuleBoundary>
          }
        />
        <Route
          path="repairs/*"
          element={
            <ModuleBoundary>
              <RepairsLayout />
            </ModuleBoundary>
          }
        >
          <Route index element={<Navigate to="pendientes" replace />} />
          <Route path="pendientes" element={<RepairsPending />} />
          <Route path="finalizadas" element={<RepairsCompleted />} />
          <Route path="repuestos" element={<RepairsParts />} />
          <Route path="presupuestos" element={<RepairsBudgets />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
});

export default DashboardRoutes;
