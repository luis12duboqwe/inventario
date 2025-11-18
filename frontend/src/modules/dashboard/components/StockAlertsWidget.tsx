import { useEffect, useMemo, useState } from "react";

import type { InventoryAlertItem, InventoryAlertSummary } from "../../../api";
import { getInventoryAlerts } from "../../../api";
import { useDashboard } from "../context/DashboardContext";

function resolveSeverityLabel(severity: InventoryAlertItem["severity"]): string {
  switch (severity) {
    case "critical":
      return "Crítica";
    case "warning":
      return "Preventiva";
    default:
      return "Seguimiento";
  }
}

function StockAlertsWidget() {
  const { token, selectedStoreId, pushToast, setError, formatCurrency } = useDashboard();
  const [alerts, setAlerts] = useState<InventoryAlertItem[]>([]);
  const [summary, setSummary] = useState<InventoryAlertSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    async function fetchAlerts() {
      try {
        setIsLoading(true);
        const response = await getInventoryAlerts(token, {
          storeId: selectedStoreId ?? undefined,
        });
        if (!isMounted) {
          return;
        }
        setAlerts(response.items);
        setSummary(response.summary);
      } catch (error) {
        if (!isMounted) {
          return;
        }
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible obtener las alertas de inventario.";
        setError(message);
        pushToast({ message, variant: "error" });
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }
    void fetchAlerts();
    return () => {
      isMounted = false;
    };
  }, [pushToast, selectedStoreId, setError, token]);

  const topAlerts = useMemo(() => alerts.slice(0, 3), [alerts]);
  const summaryLabel = useMemo(() => {
    if (!summary) {
      return "Sin alertas registradas";
    }
    const { critical, warning, notice } = summary;
    if (critical > 0) {
      return `${critical} críticas · ${warning} preventivas · ${notice} en seguimiento`;
    }
    if (warning > 0) {
      return `${warning} preventivas · ${notice} en seguimiento`;
    }
    if (notice > 0) {
      return `${notice} en seguimiento`;
    }
    return "Sin alertas activas";
  }, [summary]);

  return (
    <section className="stock-alerts-widget" aria-label="Alertas de inventario prioritarias">
      <header className="stock-alerts-header">
        <div>
          <h2>Alertas de stock</h2>
          <p className="muted-text">Pronóstico híbrido y umbrales corporativos en tiempo real.</p>
        </div>
        <div className="stock-alerts-summary" aria-live="polite">
          {isLoading ? "Cargando…" : summaryLabel}
        </div>
      </header>
      {isLoading ? (
        <div className="stock-alerts-empty" role="status">
          <span className="muted-text">Cargando alertas…</span>
        </div>
      ) : topAlerts.length === 0 ? (
        <div className="stock-alerts-empty" role="status">
          <span className="muted-text">Sin alertas con el umbral actual.</span>
        </div>
      ) : (
        <ul className="stock-alerts-list">
          {topAlerts.map((alert) => (
            <li key={alert.device_id} className={`stock-alert-card ${alert.severity}`}>
              <div className="stock-alert-main">
                <strong>{alert.sku}</strong>
                <span className="muted-text">
                  {alert.name} · {alert.store_name}
                </span>
                <span className="muted-text">Severidad: {resolveSeverityLabel(alert.severity)}</span>
                <div className="stock-alert-tags">
                  <span className="stock-tag tag-minimum">Mínimo {alert.minimum_stock}</span>
                  <span className="stock-tag tag-reorder">Reorden {alert.reorder_point}</span>
                  {alert.reorder_gap > 0 ? (
                    <span className="stock-tag tag-gap">Faltan {alert.reorder_gap} uds</span>
                  ) : (
                    <span className="stock-tag tag-gap safe">En rango</span>
                  )}
                  {alert.projected_days !== null ? (
                    <span
                      className={`stock-tag tag-forecast ${
                        alert.projected_days <= 3
                          ? "critical"
                          : alert.projected_days <= 7
                            ? "warning"
                            : "notice"
                      }`}
                    >
                      {alert.projected_days}d restantes
                    </span>
                  ) : (
                    <span className="stock-tag tag-forecast notice">Sin pronóstico</span>
                  )}
                  {alert.insights.slice(0, 2).map((insight, index) => (
                    <span key={`${alert.device_id}-widget-insight-${index}`} className="stock-tag tag-insight">
                      {insight}
                    </span>
                  ))}
                </div>
              </div>
              <div className="stock-alert-meta">
                <span className="stock-alert-quantity">{alert.quantity} uds</span>
                <span className="muted-text">{formatCurrency(alert.inventory_value)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default StockAlertsWidget;
