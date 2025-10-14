import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AnalyticsAging,
  AnalyticsComparative,
  AnalyticsForecast,
  AnalyticsProfitMargin,
  AnalyticsRotation,
  AnalyticsSalesProjection,
  downloadAnalyticsCsv,
  downloadAnalyticsPdf,
  getAgingAnalytics,
  getComparativeAnalytics,
  getForecastAnalytics,
  getProfitMarginAnalytics,
  getRotationAnalytics,
  getSalesProjectionAnalytics,
} from "../api";
import { useDashboard } from "./dashboard/DashboardContext";

type Props = {
  token: string;
};

function AnalyticsBoard({ token }: Props) {
  const { stores, pushToast, formatCurrency } = useDashboard();
  const [rotation, setRotation] = useState<AnalyticsRotation | null>(null);
  const [aging, setAging] = useState<AnalyticsAging | null>(null);
  const [forecast, setForecast] = useState<AnalyticsForecast | null>(null);
  const [comparative, setComparative] = useState<AnalyticsComparative | null>(null);
  const [profit, setProfit] = useState<AnalyticsProfitMargin | null>(null);
  const [projection, setProjection] = useState<AnalyticsSalesProjection | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedStore, setSelectedStore] = useState<number | "all">("all");

  const storeIds = useMemo(() => (selectedStore === "all" ? undefined : [selectedStore]), [selectedStore]);

  const rotationItems = rotation?.items ?? [];
  const agingItems = aging?.items ?? [];
  const forecastItems = forecast?.items ?? [];
  const comparativeItems = comparative?.items ?? [];
  const profitItems = profit?.items ?? [];
  const projectionItems = projection?.items ?? [];

  const loadData = useCallback(
    async (notify = false) => {
      try {
        if (!notify) {
          setLoading(true);
          setError(null);
        }
        const [rotationData, agingData, forecastData, comparativeData, profitData, projectionData] =
          await Promise.all([
            getRotationAnalytics(token, storeIds),
            getAgingAnalytics(token, storeIds),
            getForecastAnalytics(token, storeIds),
            getComparativeAnalytics(token, storeIds),
            getProfitMarginAnalytics(token, storeIds),
            getSalesProjectionAnalytics(token, storeIds),
          ]);
        setRotation(rotationData);
        setAging(agingData);
        setForecast(forecastData);
        setComparative(comparativeData);
        setProfit(profitData);
        setProjection(projectionData);
        if (notify) {
          pushToast({ message: "Analítica actualizada", variant: "info" });
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "No fue posible cargar la analítica avanzada";
        setError(message);
        pushToast({ message, variant: "error" });
      } finally {
        if (!notify) {
          setLoading(false);
        }
      }
    },
    [pushToast, storeIds, token]
  );

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  useEffect(() => {
    const interval = window.setInterval(() => loadData(true), 60000);
    return () => window.clearInterval(interval);
  }, [loadData]);

  const handleDownloadPdf = async () => {
    try {
      await downloadAnalyticsPdf(token, storeIds);
      pushToast({ message: "PDF analítico generado", variant: "success" });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "No fue posible descargar el PDF analítico";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleDownloadCsv = async () => {
    try {
      await downloadAnalyticsCsv(token, storeIds);
      pushToast({ message: "CSV analítico exportado", variant: "success" });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "No fue posible descargar el CSV analítico";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const formatNumber = useCallback(
    (value: number) => formatCurrency(value),
    [formatCurrency]
  );

  const limitedComparatives = useMemo(() => comparativeItems.slice(0, 5), [comparativeItems]);
  const limitedProfit = useMemo(() => profitItems.slice(0, 5), [profitItems]);
  const limitedProjection = useMemo(() => projectionItems.slice(0, 5), [projectionItems]);

  return (
    <section className="card analytics-card fade-in">
      <header className="card-header analytics-header">
        <div>
          <h2 className="accent-title">Analítica avanzada</h2>
          <p className="card-subtitle">
            Rotación, envejecimiento, comparativos multi-sucursal y proyecciones de ventas.
          </p>
        </div>
        <div className="analytics-actions">
          <label>
            <span>Sucursal</span>
            <select
              value={selectedStore}
              onChange={(event) => {
                const value = event.target.value;
                setSelectedStore(value === "all" ? "all" : Number(value));
              }}
            >
              <option value="all">Todas</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </label>
          <button className="btn" onClick={handleDownloadPdf} disabled={loading}>
            Descargar PDF
          </button>
          <button className="btn ghost" onClick={handleDownloadCsv} disabled={loading}>
            Exportar CSV
          </button>
        </div>
      </header>
      {error && <p className="error-text">{error}</p>}
      {loading ? (
        <p>Cargando analítica...</p>
      ) : (
        <>
          <div className="analytics-grid">
            <div className="analytics-panel">
              <h3 className="accent-title">Rotación por dispositivo</h3>
              <table>
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Sucursal</th>
                    <th>Vendidos</th>
                    <th>Recibidos</th>
                    <th>Rotación</th>
                  </tr>
                </thead>
                <tbody>
                  {rotationItems.slice(0, 10).map((item) => (
                    <tr key={`${item.device_id}-${item.store_id}`}>
                      <td>{item.sku}</td>
                      <td>{item.store_name}</td>
                      <td>{item.sold_units}</td>
                      <td>{item.received_units}</td>
                      <td>{item.rotation_rate.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="analytics-panel">
              <h3 className="accent-title">Envejecimiento</h3>
              <table>
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Sucursal</th>
                    <th>Días</th>
                    <th>Inventario</th>
                  </tr>
                </thead>
                <tbody>
                  {agingItems.slice(0, 10).map((item) => (
                    <tr key={`${item.device_id}-${item.store_name}`}>
                      <td>{item.sku}</td>
                      <td>{item.store_name}</td>
                      <td>{item.days_in_stock}</td>
                      <td>{item.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="analytics-panel">
              <h3 className="accent-title">Pronóstico de agotamiento</h3>
              <table>
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Sucursal</th>
                    <th>Promedio diario</th>
                    <th>Días proyectados</th>
                  </tr>
                </thead>
                <tbody>
                  {forecastItems.slice(0, 10).map((item) => (
                    <tr key={`${item.device_id}-${item.store_name}`}>
                      <td>{item.sku}</td>
                      <td>{item.store_name}</td>
                      <td>{item.average_daily_sales.toFixed(2)}</td>
                      <td>{item.projected_days ?? "N/A"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="analytics-secondary-grid">
            <div className="metrics-card">
              <h3 className="accent-title">Comparativo por sucursal</h3>
              {limitedComparatives.length === 0 ? (
                <p className="muted-text">Sin datos comparativos disponibles.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Sucursal</th>
                      <th>Inventario</th>
                      <th>Unidades</th>
                      <th>Rotación</th>
                      <th>Ventas 30d</th>
                    </tr>
                  </thead>
                  <tbody>
                    {limitedComparatives.map((item) => (
                      <tr key={item.store_id}>
                        <td>{item.store_name}</td>
                        <td>{formatNumber(item.inventory_value)}</td>
                        <td>{item.total_units}</td>
                        <td>{item.average_rotation.toFixed(2)}</td>
                        <td>{formatNumber(item.sales_last_30_days)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="metrics-card">
              <h3 className="accent-title">Margen de contribución</h3>
              {limitedProfit.length === 0 ? (
                <p className="muted-text">Aún no se registran ventas para calcular márgenes.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Sucursal</th>
                      <th>Ingresos</th>
                      <th>Utilidad</th>
                      <th>Margen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {limitedProfit.map((item) => (
                      <tr key={item.store_id}>
                        <td>{item.store_name}</td>
                        <td>{formatNumber(item.revenue)}</td>
                        <td>{formatNumber(item.profit)}</td>
                        <td>{item.margin_percent.toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="metrics-card">
              <h3 className="accent-title">Proyección de ventas (30 días)</h3>
              {limitedProjection.length === 0 ? (
                <p className="muted-text">Sin datos suficientes para proyectar ventas.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Sucursal</th>
                      <th>Unidades/día</th>
                      <th>Ticket promedio</th>
                      <th>Ingresos proyectados</th>
                    </tr>
                  </thead>
                  <tbody>
                    {limitedProjection.map((item) => (
                      <tr key={item.store_id}>
                        <td>{item.store_name}</td>
                        <td>{item.average_daily_units.toFixed(2)}</td>
                        <td>{formatNumber(item.average_ticket)}</td>
                        <td>{formatNumber(item.projected_revenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

export default AnalyticsBoard;
