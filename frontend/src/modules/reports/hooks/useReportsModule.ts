import { useDashboard } from "../../dashboard/context/DashboardContext";

export function useReportsModule() {
  const dashboard = useDashboard();

  return {
    token: dashboard.token,
    pushToast: dashboard.pushToast,
    formatCurrency: dashboard.formatCurrency,
  };
}
