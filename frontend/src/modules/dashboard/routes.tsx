import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import DashboardLayout from "./layout/DashboardLayout";
import InventoryPage from "../inventory/pages/InventoryPage";
import OperationsPage from "../operations/pages/OperationsPage";
import AnalyticsPage from "../analytics/pages/AnalyticsPage";
import SecurityPage from "../security/pages/SecurityPage";
import SyncPage from "../sync/pages/SyncPage";
import UsersPage from "../users/pages/UsersPage";
import RepairsPage from "../repairs/pages/RepairsPage";
import GlobalReportsPage from "../reports/pages/GlobalReportsPage";

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

function DashboardRoutes({ theme, onToggleTheme, onLogout }: DashboardRoutesProps) {
  const [initialModule] = useState(resolveInitialModule);

  return (
    <Routes>
      <Route element={<DashboardLayout theme={theme} onToggleTheme={onToggleTheme} onLogout={onLogout} />}>
        <Route index element={<Navigate to={initialModule} replace />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="operations" element={<OperationsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="reports" element={<GlobalReportsPage />} />
        <Route path="security" element={<SecurityPage />} />
        <Route path="sync" element={<SyncPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="repairs" element={<RepairsPage />} />
        <Route path="*" element={<Navigate to="inventory" replace />} />
      </Route>
    </Routes>
  );
}

export default DashboardRoutes;
