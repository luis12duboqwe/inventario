import { useQuery } from "@tanstack/react-query";
import { getRiskAlerts } from "../../../api";

export function useRiskAlerts(token: string) {
  return useQuery({
    queryKey: ["riskAlerts"],
    queryFn: async () => {
      const response = await getRiskAlerts(token);
      return response.alerts;
    },
    enabled: !!token,
    initialData: [],
  });
}
