import { Navigate, Route, Routes } from "react-router-dom";
import DashboardLayout from "./layout/DashboardLayout";
import InventoryPage from "../inventory/pages/InventoryPage";
import OperationsPage from "../operations/pages/OperationsPage";
import AnalyticsPage from "../analytics/pages/AnalyticsPage";
import SecurityPage from "../security/pages/SecurityPage";
import SyncPage from "../sync/pages/SyncPage";
import UsersPage from "../users/pages/UsersPage";
import RepairsPage from "../repairs/pages/RepairsPage";

function DashboardRoutes() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route index element={<Navigate to="inventory" replace />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="operations" element={<OperationsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
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
