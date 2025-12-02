import { useEffect, useMemo, useState } from "react";

import type { MinimumStockAlert, MinimumStockSummary } from "../../../api";
import { getMinimumStockAlerts } from "../../../api";
import { useDashboard } from "../context/DashboardContext";

function MinimumStockWidget() {
  const { token, selectedStoreId, pushToast, setError, formatCurrency } = useDashboard();
  const [alerts, setAlerts] = useState<MinimumStockAlert[]>([]);
  const [summary, setSummary] = useState<MinimumStockSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    async function fetchMinimumStockAlerts() {
      try {
        setIsLoading(true);
        const response = await getMinimumStockAlerts(token, {
          ...(selectedStoreId ? { storeId: selectedStoreId } : {}),
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
          error instanceof Error ? error.message : "No fue posible obtener el stock bajo mínimo.";
        setError(message);
        pushToast({ message, variant: "error" });
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void fetchMinimumStockAlerts();

    return () => {
      isMounted = false;
    };
  }, [pushToast, selectedStoreId, setError, token]);

  const topAlerts = useMemo(() => alerts.slice(0, 4), [alerts]);

  const summaryLabel = useMemo(() => {
    if (!summary) {
      return "Sin datos de stock mínimo";
    }
    if (summary.total === 0) {
      return "Todo el inventario está por encima del mínimo";
    }
    return `${summary.below_minimum} bajo mínimo · ${summary.below_reorder_point} en reorden`;
  }, [summary]);

  return (
    <section className="minimum-stock-widget" aria-label="Stock bajo mínimo y reorden">
      <header className="minimum-stock-header">
        <div>
          <h2>Stock bajo mínimo</h2>
          <p className="muted-text">
            Dispositivos con prioridad de compra según mínimo y punto de reorden.
          </p>
        </div>
        <div className="minimum-stock-summary" aria-live="polite">
          {isLoading ? "Cargando…" : summaryLabel}
        </div>
      </header>

      {isLoading ? (
        <div className="minimum-stock-empty" role="status">
          <span className="muted-text">Cargando dispositivos…</span>
        </div>
      ) : topAlerts.length === 0 ? (
        <div className="minimum-stock-empty" role="status">
          <span className="muted-text">Sin productos bajo mínimo.</span>
        </div>
      ) : (
        <ul className="minimum-stock-list">
          {topAlerts.map((alert) => (
            <li
              key={`minimum-${alert.device_id}`}
              className={`minimum-stock-card ${alert.below_minimum ? "critical" : "warning"}`}
            >
              <div className="minimum-stock-main">
                <strong>{alert.sku}</strong>
                <span className="muted-text">
                  {alert.name} · {alert.store_name}
                </span>
                <div className="minimum-stock-tags">
                  <span className="stock-tag tag-minimum">Mínimo {alert.minimum_stock}</span>
                  <span className="stock-tag tag-reorder">Reorden {alert.reorder_point}</span>
                  {alert.below_minimum ? (
                    <span className="stock-tag tag-critical">Por debajo del mínimo</span>
                  ) : (
                    <span className="stock-tag tag-warning">En punto de reorden</span>
                  )}
                  {alert.reorder_gap > 0 ? (
                    <span className="stock-tag tag-gap">Faltan {alert.reorder_gap} uds</span>
                  ) : (
                    <span className="stock-tag tag-gap safe">Sin brecha</span>
                  )}
                </div>
              </div>
              <div className="minimum-stock-meta">
                <span className="minimum-stock-quantity">{alert.quantity} uds</span>
                <span className="muted-text">{formatCurrency(alert.inventory_value)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default MinimumStockWidget;
