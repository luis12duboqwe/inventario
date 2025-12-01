import { useCallback, useEffect, useState } from "react";
import { getPurchaseStatistics } from "../../../../../api/purchases";
import type { PurchaseStatistics } from "../../../../../api/purchases";

type UsePurchaseStatisticsParams = {
  token: string;
  setError: (msg: string | null) => void;
};

export function usePurchaseStatistics(params: UsePurchaseStatisticsParams) {
  const { token, setError } = params;
  const [statistics, setStatistics] = useState<PurchaseStatistics | null>(null);
  const [statisticsLoading, setStatisticsLoading] = useState(false);

  const loadStatistics = useCallback(async () => {
    try {
      setStatisticsLoading(true);
      const data = await getPurchaseStatistics(token);
      setStatistics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar las estadísticas");
    } finally {
      setStatisticsLoading(false);
    }
  }, [token, setError]);

  useEffect(() => {
    void loadStatistics();
  }, [loadStatistics]);

  return {
    statistics,
    statisticsLoading,
    loadStatistics,
  };
}
