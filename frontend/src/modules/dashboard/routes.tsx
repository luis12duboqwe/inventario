import { Suspense, lazy, memo, type ReactNode, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
const DashboardLayout = lazy(() => import("./layout/DashboardLayout"));

const InventoryPage = lazy(() => import("../inventory/pages/InventoryPage"));
const OperationsPage = lazy(() => import("../operations/pages/OperationsPage"));
const AnalyticsPage = lazy(() => import("../analytics/pages/AnalyticsPage"));
const SecurityPage = lazy(() => import("../security/pages/SecurityPage"));
const SyncPage = lazy(() => import("../sync/pages/SyncPage"));
const UsersPage = lazy(() => import("../users/pages/UsersPage"));
const RepairsPage = lazy(() => import("../repairs/pages/RepairsPage"));
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
          path="inventory"
          element={
            <ModuleBoundary>
              <InventoryPage />
            </ModuleBoundary>
          }
        />
        <Route
          path="operations"
          element={
            <ModuleBoundary>
              <OperationsPage />
            </ModuleBoundary>
          }
        />
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
          path="repairs"
          element={
            <ModuleBoundary>
              <RepairsPage />
            </ModuleBoundary>
          }
        />
        <Route path="*" element={<Navigate to="inventory" replace />} />
      </Route>
    </Routes>
  );
});

export default DashboardRoutes;
