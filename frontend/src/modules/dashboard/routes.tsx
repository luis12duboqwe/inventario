import { Suspense, lazy, memo, type ReactNode, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
const DashboardLayout = lazy(() => import("./layout/DashboardLayout"));

const InventoryPage = lazy(() => import("../inventory/pages/InventoryPage"));
const InventoryProductsPage = lazy(() => import("../inventory/pages/InventoryProductsPage"));
const InventoryMovementsPage = lazy(() => import("../inventory/pages/InventoryMovementsPage"));
const InventorySuppliersPage = lazy(() => import("../inventory/pages/InventorySuppliersPage"));
const InventoryAlertsPage = lazy(() => import("../inventory/pages/InventoryAlertsPage"));
const OperationsPage = lazy(() => import("../operations/pages/OperationsPage"));
const VentasCajaPage = lazy(() => import("../operations/pages/ventas/CajaPage"));
const VentasFacturacionPage = lazy(() => import("../operations/pages/ventas/FacturacionPage"));
const VentasClientesPage = lazy(() => import("../operations/pages/ventas/ClientesPage"));
const VentasCajasPage = lazy(() => import("../operations/pages/ventas/CajasPage"));
const ComprasOrdenesPage = lazy(() => import("../operations/pages/compras/OrdenesPage"));
const ComprasPagosPage = lazy(() => import("../operations/pages/compras/PagosPage"));
const ComprasProveedoresPage = lazy(() => import("../operations/pages/compras/ProveedoresPage"));
const MovimientosInternosPage = lazy(() => import("../operations/pages/movimientos/InternosPage"));
const TransferenciasPage = lazy(() => import("../operations/pages/movimientos/TransferenciasPage"));
const AnalyticsPage = lazy(() => import("../analytics/pages/AnalyticsPage"));
const SecurityPage = lazy(() => import("../security/pages/SecurityPage"));
const SyncPage = lazy(() => import("../sync/pages/SyncPage"));
const UsersPage = lazy(() => import("../users/pages/UsersPage"));
const RepairsPage = lazy(() => import("../repairs/pages/RepairsPage"));
const RepairsPendingPage = lazy(() => import("../repairs/pages/RepairsPendingPage"));
const RepairsFinalizedPage = lazy(() => import("../repairs/pages/RepairsFinalizedPage"));
const RepairsPartsPage = lazy(() => import("../repairs/pages/RepairsPartsPage"));
const RepairsBudgetsPage = lazy(() => import("../repairs/pages/RepairsBudgetsPage"));
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
              <InventoryPage />
            </ModuleBoundary>
          }
        >
          <Route index element={<Navigate to="productos" replace />} />
          <Route path="productos" element={<InventoryProductsPage />} />
          <Route path="movimientos" element={<InventoryMovementsPage />} />
          <Route path="proveedores" element={<InventorySuppliersPage />} />
          <Route path="alertas" element={<InventoryAlertsPage />} />
        </Route>
        <Route
          path="operations/*"
          element={
            <ModuleBoundary>
              <OperationsPage />
            </ModuleBoundary>
          }
        >
          <Route index element={<Navigate to="ventas/caja" replace />} />
          <Route path="ventas">
            <Route index element={<Navigate to="caja" replace />} />
            <Route path="caja" element={<VentasCajaPage />} />
            <Route path="facturacion" element={<VentasFacturacionPage />} />
            <Route path="clientes" element={<VentasClientesPage />} />
            <Route path="cajas" element={<VentasCajasPage />} />
          </Route>
          <Route path="compras">
            <Route index element={<Navigate to="ordenes" replace />} />
            <Route path="ordenes" element={<ComprasOrdenesPage />} />
            <Route path="pagos" element={<ComprasPagosPage />} />
            <Route path="proveedores" element={<ComprasProveedoresPage />} />
          </Route>
          <Route path="movimientos">
            <Route index element={<Navigate to="internos" replace />} />
            <Route path="internos" element={<MovimientosInternosPage />} />
            <Route path="transferencias" element={<TransferenciasPage />} />
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
              <RepairsPage />
            </ModuleBoundary>
          }
        >
          <Route index element={<Navigate to="pendientes" replace />} />
          <Route
            path="pendientes"
            element={
              <ModuleBoundary>
                <RepairsPendingPage />
              </ModuleBoundary>
            }
          />
          <Route
            path="finalizadas"
            element={
              <ModuleBoundary>
                <RepairsFinalizedPage />
              </ModuleBoundary>
            }
          />
          <Route
            path="repuestos"
            element={
              <ModuleBoundary>
                <RepairsPartsPage />
              </ModuleBoundary>
            }
          />
          <Route
            path="presupuestos"
            element={
              <ModuleBoundary>
                <RepairsBudgetsPage />
              </ModuleBoundary>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="inventory" replace />} />
      </Route>
    </Routes>
  );
});

export default DashboardRoutes;
