import { useCallback, useEffect, useMemo, useState } from "react";

import type { InventoryAlertsResponse } from "@api/inventory";
import { getInventoryAlerts } from "@api/inventory";
import { useDashboard } from "../../../dashboard/context/DashboardContext";
import InventoryAlerts from "../../components/InventoryAlerts";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

function InventoryAlertsSection() {
  const {
    module: { selectedStoreId, formatCurrency, lowStockDevices },
    alerts: { thresholdDraft, updateThresholdDraftValue, handleSaveThreshold, isSavingThreshold },
  } = useInventoryLayout();
  const { token, pushToast, setError } = useDashboard();

  const [alertsData, setAlertsData] = useState<InventoryAlertsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchAlerts = useCallback(
    async (overrideThreshold?: number) => {
      try {
        setIsLoading(true);
        const response = await getInventoryAlerts(token, {
          ...(selectedStoreId != null ? { storeId: selectedStoreId } : {}),
          ...(overrideThreshold !== undefined ? { threshold: overrideThreshold } : {}),
        });
        setAlertsData(response);
        updateThresholdDraftValue(response.settings.threshold);
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible obtener las alertas de inventario.";
        setError(message);
        pushToast({ message, variant: "error" });
      } finally {
        setIsLoading(false);
      }
    },
    [pushToast, selectedStoreId, setError, token, updateThresholdDraftValue],
  );

  useEffect(() => {
    void fetchAlerts();
  }, [fetchAlerts]);

  useEffect(() => {
    void fetchAlerts(alertsData?.settings.threshold);
  }, [fetchAlerts, lowStockDevices.length, alertsData?.settings.threshold]);

  const handlePersistThreshold = useCallback(async () => {
    try {
      await handleSaveThreshold();
      await fetchAlerts(thresholdDraft);
    } catch {
      await fetchAlerts(alertsData?.settings.threshold);
    }
  }, [alertsData?.settings.threshold, fetchAlerts, handleSaveThreshold, thresholdDraft]);

  const summary = alertsData?.summary ?? {
    total: 0,
    critical: 0,
    warning: 0,
    notice: 0,
  };

  const settings = useMemo(() => {
    if (alertsData) {
      return alertsData.settings;
    }
    return {
      threshold: thresholdDraft,
      minimum_threshold: 0,
      maximum_threshold: 100,
      warning_cutoff: 0,
      critical_cutoff: 0,
      adjustment_variance_threshold: 0,
    };
  }, [alertsData, thresholdDraft]);

  const items = alertsData?.items ?? [];

  return (
    <InventoryAlerts
      items={items}
      summary={summary}
      settings={settings}
      thresholdDraft={thresholdDraft}
      onThresholdChange={updateThresholdDraftValue}
      onSaveThreshold={() => {
        void handlePersistThreshold();
      }}
      isSaving={isSavingThreshold}
      formatCurrency={formatCurrency}
      isLoading={isLoading}
    />
  );
}

export default InventoryAlertsSection;
