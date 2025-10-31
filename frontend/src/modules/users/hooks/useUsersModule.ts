import { useDashboard } from "../../dashboard/context/DashboardContext";

export function useUsersModule() {
  const dashboard = useDashboard();

  return {
    token: dashboard.token,
    pushToast: dashboard.pushToast,
    currentUser: dashboard.currentUser,
  };
}
