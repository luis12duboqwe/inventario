import { useCallback, useEffect, useMemo, useState } from "react";
import {
  type AnalyticsAging,
  type AnalyticsComparative,
  type AnalyticsFilters,
  type AnalyticsForecast,
  type AnalyticsProfitMargin,
  type AnalyticsRotation,
  type AnalyticsSalesProjection,
  type AnalyticsAlerts,
  type AnalyticsRealtime,
  type PurchaseAnalytics,
  downloadAnalyticsCsv,
  downloadAnalyticsPdf,
  getAgingAnalytics,
  getAnalyticsAlerts,
  getAnalyticsCategories,
  getAnalyticsRealtime,
  getComparativeAnalytics,
  getForecastAnalytics,
  getPurchaseAnalytics,
  getProfitMarginAnalytics,
  getRotationAnalytics,
  getSalesProjectionAnalytics,
} from "@api/analytics";
import { listPurchaseVendors } from "@api/purchases";
import { promptCorporateReason } from "../../../utils/corporateReason";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import LoadingOverlay from "../../../shared/components/LoadingOverlay";
import ScrollableTable from "../../../shared/components/ScrollableTable";
import AnalyticsGrid, { type AnalyticsGridItem } from "@components/ui/AnalyticsGrid/AnalyticsGrid";
import Tooltip from "@components/ui/Tooltip";
import TextField from "@components/ui/TextField";
import Select from "@components/ui/Select";
import Button from "@components/ui/Button";

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
  const [alertsData, setAlertsData] = useState<AnalyticsAlerts | null>(null);
  const [realtimeData, setRealtimeData] = useState<AnalyticsRealtime | null>(null);
  const [purchasesReport, setPurchasesReport] = useState<PurchaseAnalytics | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [suppliers, setSuppliers] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedStore, setSelectedStore] = useState<number | "all">("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedSupplier, setSelectedSupplier] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  const storeIds = useMemo(
    () => (selectedStore === "all" ? undefined : [selectedStore]),
    [selectedStore],
  );
  const analyticsFilters = useMemo<AnalyticsFilters>(() => {
    const filters: AnalyticsFilters = {};
    if (storeIds && storeIds.length > 0) {
      filters.storeIds = storeIds;
    }
    if (dateFrom) {
      filters.dateFrom = dateFrom;
    }
    if (dateTo) {
      filters.dateTo = dateTo;
    }
    if (selectedCategory !== "all") {
      filters.category = selectedCategory;
    }
    if (selectedSupplier !== "all") {
      filters.supplier = selectedSupplier;
    }
    return filters;
  }, [dateFrom, dateTo, selectedCategory, selectedSupplier, storeIds]);

  const rotationItems = rotation?.items ?? [];
  const agingItems = aging?.items ?? [];
  const forecastItems = forecast?.items ?? [];
  const comparativeItems = comparative?.items ?? [];
  const profitItems = useMemo(() => profit?.items ?? [], [profit]);
  const projectionItems = useMemo(() => projection?.items ?? [], [projection]);
  const purchaseItems = useMemo(() => purchasesReport?.items ?? [], [purchasesReport]);
  const alerts = alertsData?.items ?? [];
  const realtime = realtimeData?.items ?? [];

  const loadData = useCallback(
    async (notify = false) => {
      try {
        if (!notify) {
          setLoading(true);
          setError(null);
        }
        const [
          rotationData,
          agingData,
          forecastData,
          comparativeData,
          profitData,
          projectionData,
          purchasesData,
          alertsResponse,
          realtimeResponse,
        ] = await Promise.all([
          getRotationAnalytics(token, analyticsFilters),
          getAgingAnalytics(token, analyticsFilters),
          getForecastAnalytics(token, analyticsFilters),
          getComparativeAnalytics(token, analyticsFilters),
          getProfitMarginAnalytics(token, analyticsFilters),
          getSalesProjectionAnalytics(token, analyticsFilters),
          getPurchaseAnalytics(token, analyticsFilters),
          getAnalyticsAlerts(token, analyticsFilters),
          getAnalyticsRealtime(token, analyticsFilters),
        ]);
        setRotation(rotationData);
        setAging(agingData);
        setForecast(forecastData);
        setComparative(comparativeData);
        setProfit(profitData);
        setProjection(projectionData);
        setPurchasesReport(purchasesData);
        setAlertsData(alertsResponse);
        setRealtimeData(realtimeResponse);
        if (notify) {
          pushToast({ message: "Analítica actualizada", variant: "info" });
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "No fue posible cargar la analítica avanzada";
        setError(message);
        pushToast({ message, variant: "error" });
        setAlertsData(null);
        setRealtimeData(null);
        setPurchasesReport(null);
      } finally {
        if (!notify) {
          setLoading(false);
        }
      }
    },
    [analyticsFilters, pushToast, token],
  );

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  useEffect(() => {
    const interval = window.setInterval(() => loadData(true), 60000);
    return () => window.clearInterval(interval);
  }, [loadData]);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await getAnalyticsCategories(token);
        setCategories(response.categories);
      } catch (err) {
        const message =
          err instanceof Error
            ? `No fue posible cargar categorías: ${err.message}`
            : "No fue posible cargar categorías";
        pushToast({ message, variant: "error" });
      }
    };
    fetchCategories();
  }, [pushToast, token]);

  useEffect(() => {
    if (
      selectedCategory !== "all" &&
      categories.length > 0 &&
      !categories.includes(selectedCategory)
    ) {
      setSelectedCategory("all");
    }
  }, [categories, selectedCategory]);

  useEffect(() => {
    const fetchSuppliers = async () => {
      try {
        const vendors = await listPurchaseVendors(token, { status: "activo", limit: 100 });
        const names = Array.from(
          new Set(
            vendors
              .map((vendor) => vendor.nombre?.trim())
              .filter((name): name is string => Boolean(name && name.length > 0)),
          ),
        ).sort((a, b) => a.localeCompare(b));
        setSuppliers(names);
      } catch (err) {
        const message =
          err instanceof Error
            ? `No fue posible cargar proveedores: ${err.message}`
            : "No fue posible cargar proveedores";
        pushToast({ message, variant: "error" });
      }
    };
    fetchSuppliers();
  }, [pushToast, token]);

  useEffect(() => {
    if (
      selectedSupplier !== "all" &&
      suppliers.length > 0 &&
      !suppliers.includes(selectedSupplier)
    ) {
      setSelectedSupplier("all");
    }
  }, [selectedSupplier, suppliers]);

  const resolveDefaultReason = () => {
    if (selectedStore === "all") {
      return "Descarga analítica corporativa";
    }
    const store = stores.find((entry) => entry.id === selectedStore);
    if (!store) {
      return "Descarga analítica corporativa";
    }
    return `Descarga analítica ${store.name}`;
  };

  const handleDownloadPdf = async () => {
    const reason = promptCorporateReason(resolveDefaultReason());
    if (reason === null) {
      pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
      return;
    }
    if (reason.length < 5) {
      const message = "El motivo corporativo debe tener al menos 5 caracteres.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    try {
      await downloadAnalyticsPdf(token, reason, analyticsFilters);
      pushToast({ message: "PDF analítico generado", variant: "success" });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "No fue posible descargar el PDF analítico";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleDownloadCsv = async () => {
    const reason = promptCorporateReason(resolveDefaultReason());
    if (reason === null) {
      pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
      return;
    }
    if (reason.length < 5) {
      const message = "El motivo corporativo debe tener al menos 5 caracteres.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    try {
      await downloadAnalyticsCsv(token, reason, analyticsFilters);
      pushToast({ message: "CSV analítico exportado", variant: "success" });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "No fue posible descargar el CSV analítico";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const formatNumber = useCallback((value: number) => formatCurrency(value), [formatCurrency]);

  const formatDateTime = useCallback((value: string | null) => {
    if (!value) {
      return "Sin registros";
    }
    const dateValue = new Date(value);
    if (Number.isNaN(dateValue.getTime())) {
      return "Sin registros";
    }
    return `${dateValue.toLocaleDateString()} ${dateValue.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    })}`;
  }, []);

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
          <th scope="col">Rotación</th>
        </>
      )}
      renderRow={(item) => (
        <tr>
          <td data-label="SKU">{item.sku}</td>
          <td data-label="Sucursal">{item.store_name}</td>
          <td data-label="Vendidos">{item.sold_units}</td>
          <td data-label="Rotación">{item.turnover_rate.toFixed(2)}</td>
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

  const purchasesContent =
    purchaseItems.length === 0 ? (
      <p className="muted-text">Sin métricas de compras registradas.</p>
    ) : (
      <ScrollableTable
        items={purchaseItems}
        itemKey={(item) => `${item.store_id}-${item.supplier}`}
        title="Rendimiento por proveedor"
        ariaLabel="Tabla de rendimiento por proveedor"
        renderHead={() => (
          <>
            <th scope="col">Proveedor</th>
            <th scope="col">Sucursal</th>
            <th scope="col">Dispositivos</th>
            <th scope="col">Costo total</th>
            <th scope="col">Costo promedio</th>
            <th scope="col">Rotación prom.</th>
            <th scope="col">Días stock prom.</th>
            <th scope="col">Backorders</th>
            <th scope="col">Última compra</th>
          </>
        )}
        renderRow={(item) => (
          <tr>
            <td data-label="Proveedor">{item.supplier}</td>
            <td data-label="Sucursal">{item.store_name}</td>
            <td data-label="Dispositivos">{item.device_count}</td>
            <td data-label="Costo total">{formatNumber(item.total_cost)}</td>
            <td data-label="Costo promedio">{formatNumber(item.average_unit_cost)}</td>
            <td data-label="Rotación prom.">{item.average_rotation.toFixed(2)}</td>
            <td data-label="Días stock prom.">{item.average_days_in_stock.toFixed(1)}</td>
            <td data-label="Backorders">{item.pending_backorders}</td>
            <td data-label="Última compra">{formatDateTime(item.last_purchase_at)}</td>
          </tr>
        )}
      />
    );

  const comparativeTable =
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

  const comparativeContent = (
    <div className="analytics-comparative">
      {comparativeTable}
      <div className="analytics-comparative__section">
        <h4>Rendimiento por proveedor</h4>
        {purchasesContent}
      </div>
    </div>
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
          const normalizedMargin =
            marginMax > 0 ? Math.max((item.margin_percent / marginMax) * 100, 0) : 0;
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
                  <div
                    className="micro-chart__bar micro-chart__bar--primary"
                    style={{ width: `${averageWidth}%` }}
                  />
                  <div
                    className="micro-chart__bar micro-chart__bar--secondary"
                    style={{ width: `${projectedWidth}%` }}
                  />
                </div>
                <span className="sr-only">
                  {item.projected_units.toFixed(2)} unidades proyectadas
                </span>
              </td>
            </tr>
          );
        }}
      />
    );

  const alertContent =
    alerts.length === 0 ? (
      <p className="muted-text">Sin alertas activas.</p>
    ) : (
      <ul className="analytics-alerts">
        {alerts.map((alert, index) => {
          const level = (alert.level ?? "info").toLowerCase();
          const levelLabel =
            alert.level === "critical" ? "Crítico" : alert.level === "warning" ? "Alerta" : "Info";
          return (
            <li
              key={`${alert.type}-${alert.store_id ?? "global"}-${
                alert.device_id ?? "general"
              }-${index}`}
              className={`analytics-alert analytics-alert--${level}`}
            >
              <div className="analytics-alert__header">
                <span className="analytics-alert__badge">{levelLabel}</span>
                <span className="analytics-alert__store">{alert.store_name}</span>
              </div>
              <p className="analytics-alert__message">{alert.message}</p>
              {alert.sku && <p className="analytics-alert__meta">SKU {alert.sku}</p>}
            </li>
          );
        })}
      </ul>
    );

  const realtimeContent =
    realtime.length === 0 ? (
      <p className="muted-text">Sin métricas en tiempo real.</p>
    ) : (
      <div className="analytics-realtime-grid">
        {realtime.map((widget) => {
          const confidencePercent = `${Math.round(widget.confidence * 100)}%`;
          return (
            <article key={widget.store_id} className="analytics-realtime-card">
              <header className="analytics-realtime-card__header">
                <h3>{widget.store_name}</h3>
                <span className={`analytics-tag analytics-tag--${widget.trend}`}>
                  {widget.trend}
                </span>
              </header>
              <div className="analytics-realtime-card__metrics">
                <div className="analytics-realtime-card__metrics-item">
                  <span className="analytics-realtime-card__label">Inventario</span>
                  <span className="analytics-realtime-card__value">
                    {formatNumber(widget.inventory_value)}
                  </span>
                </div>
                <div className="analytics-realtime-card__metrics-item">
                  <span className="analytics-realtime-card__label">Ventas hoy</span>
                  <span className="analytics-realtime-card__value">
                    {formatNumber(widget.sales_today)}
                  </span>
                </div>
                <div className="analytics-realtime-card__metrics-item">
                  <span className="analytics-realtime-card__label">Última venta</span>
                  <span className="analytics-realtime-card__value analytics-realtime-card__value--muted">
                    {formatDateTime(widget.last_sale_at)}
                  </span>
                </div>
                <div className="analytics-realtime-card__metrics-item">
                  <span className="analytics-realtime-card__label">Stock crítico</span>
                  <span className="analytics-realtime-card__value">{widget.low_stock_devices}</span>
                </div>
                <div className="analytics-realtime-card__metrics-item">
                  <span className="analytics-realtime-card__label">Reparaciones</span>
                  <span className="analytics-realtime-card__value">{widget.pending_repairs}</span>
                </div>
                <div className="analytics-realtime-card__metrics-item">
                  <span className="analytics-realtime-card__label">Última sync</span>
                  <span className="analytics-realtime-card__value analytics-realtime-card__value--muted">
                    {formatDateTime(widget.last_sync_at)}
                  </span>
                </div>
                <div className="analytics-realtime-card__metrics-item analytics-realtime-card__metrics-item--full">
                  <span className="analytics-realtime-card__label">Confianza</span>
                  <span className="analytics-realtime-card__value">{confidencePercent}</span>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    );

  const analyticsItems: AnalyticsGridItem[] = [
    {
      id: "rotation",
      title: (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          Rotación por dispositivo
          <Tooltip content="Velocidad a la que se vende el inventario. Mayor es mejor." />
        </div>
      ),
      description: "Velocidad de salida y recepción por SKU en cada sucursal.",
      content: rotationContent,
    },
    {
      id: "aging",
      title: (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          Envejecimiento
          <Tooltip content="Tiempo que los productos permanecen en inventario sin venderse." />
        </div>
      ),
      description: "Días en stock y unidades disponibles por tienda.",
      content: agingContent,
    },
    {
      id: "forecast",
      title: (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          Pronóstico de agotamiento
          <Tooltip content="Estimación de cuándo se agotará el stock actual basado en ventas recientes." />
        </div>
      ),
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
      title: (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          Margen de contribución
          <Tooltip content="Porcentaje de ganancia sobre el costo de los productos vendidos." />
        </div>
      ),
      description: "Ingresos, utilidades y porcentaje por tienda.",
      content: marginContent,
    },
    {
      id: "projection",
      title: (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          Proyección de ventas
          <Tooltip content="Estimación de ventas futuras basada en tendencias históricas." />
        </div>
      ),
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
          <div className="analytics-filters">
            <Select
              label="Sucursal"
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
            </Select>
            <TextField
              label="Desde"
              type="date"
              value={dateFrom}
              max={dateTo || undefined}
              onChange={(event) => setDateFrom(event.target.value)}
            />
            <TextField
              label="Hasta"
              type="date"
              value={dateTo}
              min={dateFrom || undefined}
              onChange={(event) => setDateTo(event.target.value)}
            />
            <Select
              label="Categoría"
              value={selectedCategory}
              onChange={(event) => setSelectedCategory(event.target.value)}
            >
              <option value="all">Todas</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </Select>
            <Select
              label="Proveedor"
              value={selectedSupplier}
              onChange={(event) => setSelectedSupplier(event.target.value)}
            >
              <option value="all">Todos</option>
              {suppliers.map((supplierName) => (
                <option key={supplierName} value={supplierName}>
                  {supplierName}
                </option>
              ))}
            </Select>
          </div>
          <div className="analytics-actions__group">
            <Button onClick={handleDownloadPdf} disabled={loading}>
              Descargar PDF
            </Button>
            <Button variant="ghost" onClick={handleDownloadCsv} disabled={loading}>
              Exportar CSV
            </Button>
          </div>
        </div>
      </header>
      {error && <p className="error-text">{error}</p>}
      <LoadingOverlay visible={loading} label="Consultando analítica..." />
      <div className="analytics-secondary-grid">
        <article className="card analytics-panel">
          <div className="analytics-subheader">
            <h3>Alertas automáticas</h3>
            <p className="card-subtitle">Detección de stock crítico y caídas de ventas.</p>
          </div>
          {alertContent}
        </article>
        <article className="card analytics-panel">
          <div className="analytics-subheader">
            <h3>Widget en tiempo real</h3>
            <p className="card-subtitle">Resumen por sucursal con ventas del día y tendencia.</p>
          </div>
          {realtimeContent}
        </article>
      </div>
      <AnalyticsGrid items={analyticsItems} />
    </section>
  );
}

export default AnalyticsBoard;
