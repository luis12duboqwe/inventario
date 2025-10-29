import { Suspense, lazy, memo, type ReactNode, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
const DashboardLayout = lazy(() => import("./layout/DashboardLayout"));

const InventoryLayout = lazy(() => import("../inventory/pages/InventoryLayout"));
const InventoryProducts = lazy(() => import("../inventory/pages/InventoryProducts"));
const InventoryMoves = lazy(() => import("../inventory/pages/InventoryMovements"));
const InventorySuppliers = lazy(() => import("../inventory/pages/InventorySuppliers"));
const InventoryAlerts = lazy(() => import("../inventory/pages/InventoryAlerts"));
const OperationsLayout = lazy(() => import("../operations/pages/OperationsLayout"));
const OperationsPage = lazy(() => import("../operations/pages/OperationsPage"));
const OperationsSalesCashPage = lazy(() => import("../operations/pages/ventas/CajaPage"));
const OperationsSalesBillingPage = lazy(() => import("../operations/pages/ventas/FacturacionPage"));
const OperationsSalesClientsPage = lazy(() => import("../operations/pages/ventas/ClientesPage"));
const OperationsSalesRegistersPage = lazy(() => import("../operations/pages/ventas/CajasPage"));
const OperationsPurchasesOrdersPage = lazy(() => import("../operations/pages/compras/OrdenesPage"));
const OperationsPurchasesPaymentsPage = lazy(() => import("../operations/pages/compras/PagosPage"));
const OperationsPurchasesSuppliersPage = lazy(() => import("../operations/pages/compras/ProveedoresPage"));
const OperationsMovementsInternalPage = lazy(() => import("../operations/pages/movimientos/InternosPage"));
const OperationsMovementsTransfersPage = lazy(() => import("../operations/pages/movimientos/TransferenciasPage"));
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
        </Route>
        <Route
          path="operations/*"
          element={
            <ModuleBoundary>
              <OperationsLayout />
            </ModuleBoundary>
          }
        >
          <Route index element={<Navigate to="ventas/caja" replace />} />
          <Route path="pos" element={<Navigate to="ventas/caja" replace />} />
          <Route path="compras" element={<Navigate to="compras/ordenes" replace />} />
          <Route path="devoluciones" element={<Navigate to="ventas/facturacion" replace />} />
          <Route path="transferencias" element={<Navigate to="movimientos/transferencias" replace />} />
          <Route element={<OperationsPage />}>
            <Route path="ventas">
              <Route index element={<Navigate to="caja" replace />} />
              <Route path="caja" element={<OperationsSalesCashPage />} />
              <Route path="clientes" element={<OperationsSalesClientsPage />} />
              <Route path="facturacion" element={<OperationsSalesBillingPage />} />
              <Route path="cajas" element={<OperationsSalesRegistersPage />} />
            </Route>
            <Route path="compras">
              <Route index element={<Navigate to="ordenes" replace />} />
              <Route path="ordenes" element={<OperationsPurchasesOrdersPage />} />
              <Route path="pagos" element={<OperationsPurchasesPaymentsPage />} />
              <Route path="proveedores" element={<OperationsPurchasesSuppliersPage />} />
            </Route>
            <Route path="movimientos">
              <Route index element={<Navigate to="internos" replace />} />
              <Route path="internos" element={<OperationsMovementsInternalPage />} />
              <Route path="transferencias" element={<OperationsMovementsTransfersPage />} />
            </Route>
          </Route>
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
        <Route path="*" element={<Navigate to="inventory" replace />} />
      </Route>
    </Routes>
  );
});

export default DashboardRoutes;
