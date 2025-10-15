import { useDashboard } from "../../dashboard/context/DashboardContext";

export function useAnalyticsModule() {
  const dashboard = useDashboard();

  return {
    token: dashboard.token,
    enableAnalyticsAdv: dashboard.enableAnalyticsAdv,
  };
}
