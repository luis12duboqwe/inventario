import { useEffect, useState } from "react";
import {
  AnalyticsAging,
  AnalyticsForecast,
  AnalyticsRotation,
  downloadAnalyticsPdf,
  getAgingAnalytics,
  getForecastAnalytics,
  getRotationAnalytics,
} from "../api";

type Props = {
  token: string;
};

function AnalyticsBoard({ token }: Props) {
  const [rotation, setRotation] = useState<AnalyticsRotation | null>(null);
  const [aging, setAging] = useState<AnalyticsAging | null>(null);
  const [forecast, setForecast] = useState<AnalyticsForecast | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [rotationData, agingData, forecastData] = await Promise.all([
          getRotationAnalytics(token),
          getAgingAnalytics(token),
          getForecastAnalytics(token),
        ]);
        setRotation(rotationData);
        setAging(agingData);
        setForecast(forecastData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar la analítica avanzada");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [token]);

  const handleDownload = async () => {
    try {
      await downloadAnalyticsPdf(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible descargar el PDF analítico");
    }
  };

  return (
    <section className="card analytics-card fade-in">
      <header className="card-header">
        <h2 className="accent-title">Analítica avanzada</h2>
        <p className="card-subtitle">
          Rotación, envejecimiento y pronóstico de agotamiento bajo los indicadores corporativos.
        </p>
        <button className="btn" onClick={handleDownload} disabled={loading}>
          Descargar PDF
        </button>
      </header>
      {error && <p className="error-text">{error}</p>}
      {loading ? (
        <p>Cargando analítica...</p>
      ) : (
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
                {(rotation?.items ?? []).slice(0, 10).map((item) => (
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
                {(aging?.items ?? []).slice(0, 10).map((item) => (
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
                {(forecast?.items ?? []).slice(0, 10).map((item) => (
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
      )}
    </section>
  );
}

export default AnalyticsBoard;
