import { useDashboard } from "../../dashboard/context/DashboardContext";

export function useSecurityModule() {
  const dashboard = useDashboard();

  return {
    token: dashboard.token,
    enableTwoFactor: dashboard.enableTwoFactor,
  };
}
