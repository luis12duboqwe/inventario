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
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import LoadingOverlay from "../../../components/LoadingOverlay";
import ScrollableTable from "../../../components/ScrollableTable";
import AnalyticsGrid, {
  type AnalyticsGridItem,
} from "../../../components/ui/AnalyticsGrid/AnalyticsGrid";

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

  const projectionUnitsMax = useMemo(() => {
    return projectionItems.reduce(
      (acc, item) => Math.max(acc, item.projected_units, item.average_daily_units),
      1,
    );
  }, [projectionItems]);

  const marginMax = useMemo(() => {
    return profitItems.reduce((acc, item) => Math.max(acc, item.margin_percent), 0);
  }, [profitItems]);

  const rotationContent = (
    <ScrollableTable
      items={rotationItems}
      itemKey={(item) => `${item.device_id}-${item.store_id}`}
      title="Rotación por dispositivo"
      ariaLabel="Tabla de rotación por dispositivo"
      renderHead={() => (
        <>
          <th scope="col">SKU</th>
          <th scope="col">Sucursal</th>
          <th scope="col">Vendidos</th>
          <th scope="col">Recibidos</th>
          <th scope="col">Rotación</th>
        </>
      )}
      renderRow={(item) => (
        <tr>
          <td data-label="SKU">{item.sku}</td>
          <td data-label="Sucursal">{item.store_name}</td>
          <td data-label="Vendidos">{item.sold_units}</td>
          <td data-label="Recibidos">{item.received_units}</td>
          <td data-label="Rotación">{item.rotation_rate.toFixed(2)}</td>
        </tr>
      )}
    />
  );

  const agingContent = (
    <ScrollableTable
      items={agingItems}
      itemKey={(item) => `${item.device_id}-${item.store_name}`}
      title="Envejecimiento de inventario"
      ariaLabel="Tabla de envejecimiento de inventario"
      renderHead={() => (
        <>
          <th scope="col">SKU</th>
          <th scope="col">Sucursal</th>
          <th scope="col">Días</th>
          <th scope="col">Inventario</th>
        </>
      )}
      renderRow={(item) => (
        <tr>
          <td data-label="SKU">{item.sku}</td>
          <td data-label="Sucursal">{item.store_name}</td>
          <td data-label="Días">{item.days_in_stock}</td>
          <td data-label="Inventario">{item.quantity}</td>
        </tr>
      )}
    />
  );

  const forecastContent = (
    <ScrollableTable
      items={forecastItems}
      itemKey={(item) => `${item.device_id}-${item.store_name}`}
      title="Pronóstico de agotamiento"
      ariaLabel="Tabla de pronóstico de agotamiento"
      renderHead={() => (
        <>
          <th scope="col">SKU</th>
          <th scope="col">Sucursal</th>
          <th scope="col">Promedio diario</th>
          <th scope="col">Días proyectados</th>
        </>
      )}
      renderRow={(item) => (
        <tr>
          <td data-label="SKU">{item.sku}</td>
          <td data-label="Sucursal">{item.store_name}</td>
          <td data-label="Promedio diario">{item.average_daily_sales.toFixed(2)}</td>
          <td data-label="Días proyectados">{item.projected_days ?? "N/A"}</td>
        </tr>
      )}
    />
  );

  const comparativeContent =
    comparativeItems.length === 0 ? (
      <p className="muted-text">Sin datos comparativos disponibles.</p>
    ) : (
      <ScrollableTable
        items={comparativeItems}
        itemKey={(item) => item.store_id}
        title="Comparativo por sucursal"
        ariaLabel="Tabla comparativa por sucursal"
        renderHead={() => (
          <>
            <th scope="col">Sucursal</th>
            <th scope="col">Inventario</th>
            <th scope="col">Unidades</th>
            <th scope="col">Rotación</th>
            <th scope="col">Ventas 30d</th>
          </>
        )}
        renderRow={(item) => (
          <tr>
            <td data-label="Sucursal">{item.store_name}</td>
            <td data-label="Inventario">{formatNumber(item.inventory_value)}</td>
            <td data-label="Unidades">{item.total_units}</td>
            <td data-label="Rotación">{item.average_rotation.toFixed(2)}</td>
            <td data-label="Ventas 30d">{formatNumber(item.sales_last_30_days)}</td>
          </tr>
        )}
      />
    );

  const marginContent =
    profitItems.length === 0 ? (
      <p className="muted-text">Aún no se registran ventas para calcular márgenes.</p>
    ) : (
      <ScrollableTable
        items={profitItems}
        itemKey={(item) => item.store_id}
        title="Margen de contribución"
        ariaLabel="Tabla de márgenes de contribución"
        renderHead={() => (
          <>
            <th scope="col">Sucursal</th>
            <th scope="col">Ingresos</th>
            <th scope="col">Utilidad</th>
            <th scope="col">Margen</th>
            <th scope="col">Visual</th>
          </>
        )}
        renderRow={(item) => {
          const normalizedMargin = marginMax > 0 ? Math.max((item.margin_percent / marginMax) * 100, 0) : 0;
          const width = Math.min(normalizedMargin, 100);
          return (
            <tr>
              <td data-label="Sucursal">{item.store_name}</td>
              <td data-label="Ingresos">{formatNumber(item.revenue)}</td>
              <td data-label="Utilidad">{formatNumber(item.profit)}</td>
              <td data-label="Margen">{item.margin_percent.toFixed(2)}%</td>
              <td data-label="Visual">
                <div className="micro-chart" aria-hidden="true">
                  <div className="micro-chart__bar" style={{ width: `${width}%` }} />
                </div>
                <span className="sr-only">Margen {item.margin_percent.toFixed(2)} por ciento</span>
              </td>
            </tr>
          );
        }}
      />
    );

  const projectionContent =
    projectionItems.length === 0 ? (
      <p className="muted-text">Sin datos suficientes para proyectar ventas.</p>
    ) : (
      <ScrollableTable
        items={projectionItems}
        itemKey={(item) => item.store_id}
        title="Proyección de ventas (30 días)"
        ariaLabel="Tabla de proyección de ventas"
        renderHead={() => (
          <>
            <th scope="col">Sucursal</th>
            <th scope="col">Unidades/día</th>
            <th scope="col">Ticket promedio</th>
            <th scope="col">Ingresos proyectados</th>
            <th scope="col">Visual</th>
          </>
        )}
        renderRow={(item) => {
          const averageWidth = Math.min((item.average_daily_units / projectionUnitsMax) * 100, 100);
          const projectedWidth = Math.min((item.projected_units / projectionUnitsMax) * 100, 100);
          return (
            <tr>
              <td data-label="Sucursal">{item.store_name}</td>
              <td data-label="Unidades/día">{item.average_daily_units.toFixed(2)}</td>
              <td data-label="Ticket promedio">{formatNumber(item.average_ticket)}</td>
              <td data-label="Ingresos proyectados">{formatNumber(item.projected_revenue)}</td>
              <td data-label="Visual">
                <div className="micro-chart" aria-hidden="true">
                  <div className="micro-chart__bar micro-chart__bar--primary" style={{ width: `${averageWidth}%` }} />
                  <div className="micro-chart__bar micro-chart__bar--secondary" style={{ width: `${projectedWidth}%` }} />
                </div>
                <span className="sr-only">{item.projected_units.toFixed(2)} unidades proyectadas</span>
              </td>
            </tr>
          );
        }}
      />
    );

  const analyticsItems: AnalyticsGridItem[] = [
    {
      id: "rotation",
      title: "Rotación por dispositivo",
      description: "Velocidad de salida y recepción por SKU en cada sucursal.",
      content: rotationContent,
    },
    {
      id: "aging",
      title: "Envejecimiento",
      description: "Días en stock y unidades disponibles por tienda.",
      content: agingContent,
    },
    {
      id: "forecast",
      title: "Pronóstico de agotamiento",
      description: "Predicción de días restantes antes del quiebre.",
      content: forecastContent,
    },
    {
      id: "comparative",
      title: "Comparativo por sucursal",
      description: "Inventario, unidades y rotación consolidada.",
      content: comparativeContent,
    },
    {
      id: "margin",
      title: "Margen de contribución",
      description: "Ingresos, utilidades y porcentaje por tienda.",
      content: marginContent,
    },
    {
      id: "projection",
      title: "Proyección de ventas (30 días)",
      description: "Estimación de unidades y ticket promedio mensual.",
      content: projectionContent,
    },
  ];

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
          <button className="btn btn--primary" onClick={handleDownloadPdf} aria-busy={loading}>
            Descargar PDF
          </button>
          <button className="btn btn--ghost" onClick={handleDownloadCsv} aria-busy={loading}>
            Exportar CSV
          </button>
        </div>
      </header>
      {error && <p className="error-text">{error}</p>}
      <LoadingOverlay visible={loading} label="Consultando analítica..." />
      <AnalyticsGrid items={analyticsItems} />
    </section>
  );
}

export default AnalyticsBoard;
