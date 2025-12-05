import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useDashboard } from "../context/DashboardContext";
import { colors } from "../../../theme/designTokens";
import { Skeleton } from "@components/ui/Skeleton"; // [PACK36-metrics]
import { safeArray, safeNumber, safeString } from "@/utils/safeValues"; // [PACK36-metrics]
import type { DashboardAuditAlerts } from "@/api";

const PIE_COLORS = [
  colors.chartCyan,
  colors.accentBright,
  colors.accent,
  colors.chartSky,
  colors.chartTeal,
];

function resolveStatusTone(
  value: number,
  threshold: number,
  inverse = false,
): "good" | "alert" | "info" {
  if (inverse) {
    return value <= threshold ? "good" : "alert";
  }
  return value >= threshold ? "good" : "alert";
}

type GlobalMetricsProps = {
  /**
   * Permite inyectar alertas de auditoría predeterminadas cuando las métricas
   * aún no están disponibles. Útil para pruebas y pantallas de contingencia.
   */
  auditAlertsMock?: DashboardAuditAlerts;
};

/**
 * Tablero global con tarjetas, gráficos y resúmenes auditables del backend.
 *
 * El hook `useDashboard` aporta métricas normalizadas por el servicio de
 * analítica. Los estados de carga y vacíos están cubiertos por
 * `GlobalMetrics.test.tsx`, asegurando que los escenarios descritos en la nueva
 * documentación respondan de forma consistente ante datos incompletos.
 */
function GlobalMetrics({ auditAlertsMock }: GlobalMetricsProps) {
  const { metrics, formatCurrency, loading } = useDashboard();

  const performance = metrics?.global_performance ?? {
    // [PACK36-metrics]
    total_sales: 0,
    sales_count: 0,
    total_stock: 0,
    open_repairs: 0,
    gross_profit: 0,
  };
  const salesInsights = metrics?.sales_insights ?? {
    average_ticket: 0,
    top_products: [],
    top_customers: [],
    payment_mix: [],
  };
  const receivables = metrics?.accounts_receivable ?? {
    total_outstanding_debt: 0,
    customers_with_debt: 0,
    moroso_flagged: 0,
    top_debtors: [],
  };
  const receivableTotal = safeNumber(receivables.total_outstanding_debt);
  const receivableCustomers = safeNumber(receivables.customers_with_debt);
  const receivableMorosos = safeNumber(receivables.moroso_flagged);
  const auditAlerts = metrics?.audit_alerts ??
    auditAlertsMock ?? {
      // [PACK36-metrics]
      total: 0,
      critical: 0,
      warning: 0,
      info: 0,
      has_alerts: false,
      pending_count: 0,
      acknowledged_count: 0,
      highlights: [],
      acknowledged_entities: [],
    };
  const totalAlerts = safeNumber(auditAlerts.total);
  const criticalCount = safeNumber(auditAlerts.critical);
  const warningCount = safeNumber(auditAlerts.warning);
  const infoCount = safeNumber(auditAlerts.info);
  const pendingCount = safeNumber(auditAlerts.pending_count);
  const acknowledgedCount = safeNumber(auditAlerts.acknowledged_count);
  type AlertHighlight = {
    id: string | number;
    severity: "critical" | "warning" | "info";
    action: string;
    created_at: string;
    entity_type: string;
  };
  const highlights = safeArray(auditAlerts.highlights) as AlertHighlight[];
  const formatHighlightDate = (isoString: string) => {
    const normalized = safeString(isoString, "");
    const parsed = new Date(normalized);
    if (Number.isNaN(parsed.getTime())) {
      return "Fecha desconocida";
    }
    return parsed.toLocaleString("es-HN", { dateStyle: "short", timeStyle: "short" });
  };
  const severityLabels: Record<"critical" | "warning" | "info", string> = {
    critical: "Crítica",
    warning: "Preventiva",
    info: "Informativa",
  };
  type ReceivableCustomer = {
    customer_id: number;
    name: string;
    outstanding_debt: number;
    available_credit?: number | null;
  };
  const topDebtors = safeArray(receivables.top_debtors) as ReceivableCustomer[];
  type SalesMetric = {
    label: string;
    value: number;
    quantity?: number | null;
    percentage?: number | null;
  };
  const topProducts = safeArray(salesInsights.top_products) as SalesMetric[];
  const topCustomers = safeArray(salesInsights.top_customers) as SalesMetric[];
  const paymentMix = safeArray(salesInsights.payment_mix).map((entry) => ({
    label: safeString((entry as SalesMetric).label, "Método"),
    value: safeNumber((entry as SalesMetric).value),
    quantity: (entry as SalesMetric).quantity ?? null,
    percentage: safeNumber((entry as SalesMetric).percentage ?? 0),
  }));
  const receivableCaption =
    receivableCustomers > 0
      ? `${receivableCustomers} clientes con saldo${
          receivableMorosos > 0 ? ` · ${receivableMorosos} morosos` : ""
        }`
      : "Sin cuentas por cobrar activas";
  const alertsTone =
    pendingCount > 0 || criticalCount > 0
      ? ("alert" as const)
      : warningCount > 0
      ? ("info" as const)
      : ("good" as const);

  const alertsValue =
    totalAlerts === 0
      ? "Sin eventos"
      : `${pendingCount} pendientes · ${acknowledgedCount} atendidas`;

  const cards = [
    {
      id: "sales",
      title: "Ventas netas",
      value: formatCurrency(safeNumber(performance.total_sales)), // [PACK36-metrics]
      caption: `${safeNumber(performance.sales_count)} operaciones cerradas`,
      tone: resolveStatusTone(safeNumber(performance.total_sales), 1),
    },
    {
      id: "profit",
      title: "Ganancia bruta",
      value: formatCurrency(safeNumber(performance.gross_profit)),
      caption:
        safeNumber(performance.gross_profit) >= 0
          ? "Margen positivo"
          : "Atiende descuentos excesivos",
      tone: resolveStatusTone(safeNumber(performance.gross_profit), 0),
    },
    {
      id: "receivables",
      title: "Cuentas por cobrar",
      value: formatCurrency(receivableTotal),
      caption: receivableCaption,
      tone: receivableTotal > 0 ? ("alert" as const) : ("good" as const),
    },
    {
      id: "stock",
      title: "Inventario total",
      value: `${safeNumber(performance.total_stock).toLocaleString("es-HN")} uds`,
      caption: "Unidades disponibles en tiendas",
      tone: "info" as const,
    },
    {
      id: "repairs",
      title: "Reparaciones abiertas",
      value: `${safeNumber(performance.open_repairs)}`,
      caption:
        safeNumber(performance.open_repairs) === 0
          ? "Sin pendientes"
          : "Coordina cierres con taller",
      tone: resolveStatusTone(safeNumber(performance.open_repairs), 0, true),
    },
    {
      id: "audit-alerts",
      title: "Alertas de auditoría",
      value: alertsValue,
      caption:
        auditAlerts.pending_count > 0
          ? "Ingresa a Seguridad para registrar acuses corporativos."
          : auditAlerts.has_alerts
          ? "Incidencias atendidas recientemente."
          : "Sin incidencias recientes",
      tone: alertsTone,
    },
  ] as const;

  // Cálculo directo para evitar discrepancias del compilador de React al preservar memoización manual
  const salesTrend = safeArray(metrics?.sales_trend).map(
    (entry: { label: string; value: number }) => ({
      ...entry,
      value: Number(safeNumber(entry.value).toFixed(2)),
    }),
  );
  const stockBreakdown = safeArray(metrics?.stock_breakdown);
  type Slice = { label: string; value: number };
  const profitSlices = useMemo<Slice[]>(() => {
    const profit = safeArray(metrics?.profit_breakdown) as Slice[];
    return profit.length > 0 ? profit : (stockBreakdown as Slice[]);
  }, [metrics?.profit_breakdown, stockBreakdown]);
  const repairMix = safeArray(metrics?.repair_mix);
  const averageTicket = formatCurrency(safeNumber(salesInsights.average_ticket));
  type AcknowledgedEntity = {
    entity_type: string;
    entity_id: string | number;
    acknowledged_by_name?: string | null;
    acknowledged_at: string;
    note?: string | null;
  };
  const acknowledgedEntities = (
    safeArray(auditAlerts.acknowledged_entities) as AcknowledgedEntity[]
  ).slice(0, 3);
  const latestAcknowledgement = acknowledgedEntities.length > 0 ? acknowledgedEntities[0] : null;

  return (
    <section className="global-metrics">
      {/* Estados de carga y vacío sin retornos tempranos para mantener ganchos en orden */}
      {!metrics && loading ? (
        <div aria-busy="true">
          <div className="metric-cards">
            {Array.from({ length: 5 }).map((_, index) => (
              <article key={`metric-skeleton-${index}`} className="metric-card metric-info">
                <Skeleton lines={3} />
              </article>
            ))}
          </div>
          <div className="metric-charts">
            <div className="chart-card p-6">
              <Skeleton lines={10} />
            </div>
          </div>
        </div>
      ) : null}

      {!loading && !metrics ? (
        <div className="metric-empty" role="status">
          <p className="muted-text">Sin métricas disponibles por el momento.</p>
          <p className="muted-text">Actualiza la vista cuando los servicios vuelvan a responder.</p>
          <div className="metric-empty__actions">
            <p className="muted-text">
              {auditAlerts.has_alerts
                ? `Existen ${pendingCount} alertas pendientes en Seguridad.`
                : "Puedes abrir Seguridad para revisar historial corporativo."}
            </p>
            <Link to="/dashboard/security" className="btn btn--link audit-shortcut">
              Abrir módulo de Seguridad
            </Link>
          </div>
        </div>
      ) : null}

      {metrics ? (
        <>
          <div className="metric-cards" aria-label="Tarjetas de desempeño global">
            {cards.map((card) => (
              <article key={card.id} className={`metric-card metric-${card.tone}`}>
                <h3>{card.title}</h3>
                <p className="metric-value">{card.value}</p>
                <p className="metric-caption">{card.caption}</p>
              </article>
            ))}
          </div>

          <div className="metric-charts">
            <article className="chart-card receivables-panel">
              <header>
                <h3>Cartera por cobrar</h3>
                <span className="chart-caption">{receivableCaption}</span>
              </header>
              <dl className="receivables-summary">
                <div>
                  <dt>Saldo pendiente</dt>
                  <dd>{formatCurrency(receivableTotal)}</dd>
                </div>
                <div>
                  <dt>Clientes con saldo</dt>
                  <dd>{receivableCustomers}</dd>
                </div>
                <div>
                  <dt>Morosos</dt>
                  <dd>{receivableMorosos}</dd>
                </div>
              </dl>
              {topDebtors.length > 0 ? (
                <ul className="receivables-list">
                  {topDebtors.map((debtor) => {
                    const outstanding = formatCurrency(safeNumber(debtor.outstanding_debt));
                    const available = debtor.available_credit;
                    return (
                      <li key={debtor.customer_id} className="receivables-item">
                        <div className="receivables-item__header">
                          <span className="receivables-name">
                            {safeString(debtor.name, "Cliente")}
                          </span>
                          <span className="receivables-amount">{outstanding}</span>
                        </div>
                        {available != null ? (
                          <span className="receivables-credit">
                            Crédito disponible: {formatCurrency(safeNumber(available))}
                          </span>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="muted-text">Sin deudores destacados en este periodo.</p>
              )}
              <Link to="/dashboard/operations/pos" className="btn btn--link receivables-link">
                Gestionar abonos en POS
              </Link>
            </article>
            <article className="chart-card audit-alerts-card">
              <header>
                <h3>Alertas y respuestas rápidas</h3>
                <span className="chart-caption">Consolidado corporativo</span>
              </header>
              <div className="alerts-summary">
                <div className="summary-item critical">
                  <span className="summary-value">{criticalCount}</span>
                  <span className="summary-label">Críticas</span>
                </div>
                <div className="summary-item warning">
                  <span className="summary-value">{warningCount}</span>
                  <span className="summary-label">Preventivas</span>
                </div>
                <div className="summary-item info">
                  <span className="summary-value">{infoCount}</span>
                  <span className="summary-label">Informativas</span>
                </div>
                <div className="summary-item pending">
                  <span className="summary-value">{pendingCount}</span>
                  <span className="summary-label">Pendientes</span>
                </div>
                <div className="summary-item acknowledged">
                  <span className="summary-value">{acknowledgedCount}</span>
                  <span className="summary-label">Atendidas</span>
                </div>
              </div>
              <div className="acknowledgement-meta">
                {latestAcknowledgement ? (
                  <p className="muted-text">
                    Último acuse: {safeString(latestAcknowledgement.entity_type, "Entidad")} #
                    {safeString(latestAcknowledgement.entity_id, "-")} ·{" "}
                    {formatHighlightDate(latestAcknowledgement.acknowledged_at)}
                    {latestAcknowledgement.acknowledged_by_name
                      ? ` por ${latestAcknowledgement.acknowledged_by_name}`
                      : ""}
                    {latestAcknowledgement.note ? ` — ${latestAcknowledgement.note}` : ""}
                  </p>
                ) : (
                  <p className="muted-text">Aún no se registran acuses corporativos.</p>
                )}
              </div>
              {highlights.length === 0 ? (
                <p className="muted-text">
                  {auditAlerts.has_alerts
                    ? "Hay incidencias registradas, revisa el módulo de Seguridad para más contexto."
                    : "Sin incidentes críticos o preventivos en el periodo reciente."}
                </p>
              ) : (
                <ul className="alerts-list">
                  {highlights.map((highlight) => (
                    <li key={highlight.id}>
                      <span className={`severity-pill severity-${highlight.severity}`}>
                        {severityLabels[highlight.severity]}
                      </span>
                      <div className="highlight-details">
                        <p className="highlight-action">{highlight.action}</p>
                        <span className="highlight-meta">
                          {formatHighlightDate(highlight.created_at)} · {highlight.entity_type}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {acknowledgedEntities.length > 0 ? (
                <ul className="acknowledged-list">
                  {acknowledgedEntities.map((entity) => (
                    <li key={`${entity.entity_type}-${entity.entity_id}`}>
                      <span className="acknowledged-entity">
                        {safeString(entity.entity_type, "Entidad")} #
                        {safeString(entity.entity_id, "-")}
                      </span>
                      <span className="acknowledged-meta">
                        {entity.acknowledged_by_name ?? "Usuario corporativo"} ·{" "}
                        {formatHighlightDate(entity.acknowledged_at)}
                        {entity.note ? ` — ${entity.note}` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {pendingCount > 0 ? (
                <Link to="/dashboard/security" className="btn btn--link audit-shortcut">
                  Abrir módulo de Seguridad
                </Link>
              ) : null}
            </article>

            <article className="chart-card">
              <header>
                <h3>Tendencia de ventas</h3>
                <span className="chart-caption">Últimos 7 días</span>
              </header>
              {salesTrend.length === 0 ? (
                <p className="muted-text">Aún no hay datos de ventas recientes.</p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={salesTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                    <XAxis dataKey="label" stroke="var(--text-secondary)" />
                    <YAxis
                      stroke="var(--text-secondary)"
                      tickFormatter={(value) => formatCurrency(value).replace("MX$", "")}
                    />
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke={colors.chartCyan}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name="Ventas"
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </article>

            <article className="chart-card sales-ranking-card">
              <header>
                <h3>Ranking de ventas</h3>
                <span className="chart-caption">Top productos y clientes</span>
              </header>
              <div className="ranking-grid">
                <div className="ranking-chart">
                  <h4>Top productos</h4>
                  {topProducts.length === 0 ? (
                    <p className="muted-text">Aún no hay productos destacados por ventas.</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={topProducts} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                        <XAxis
                          type="number"
                          stroke="var(--text-secondary)"
                          tickFormatter={(value) => formatCurrency(value).replace("MX$", "")}
                        />
                        <YAxis
                          type="category"
                          dataKey="label"
                          stroke="var(--text-secondary)"
                          width={140}
                        />
                        <Tooltip formatter={(value: number) => formatCurrency(value)} />
                        <Legend />
                        <Bar
                          dataKey="value"
                          fill={colors.chartCyan}
                          name="Ingresos"
                          radius={[6, 6, 6, 6]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
                <div className="ranking-list-wrapper">
                  <h4>Top clientes</h4>
                  {topCustomers.length === 0 ? (
                    <p className="muted-text">
                      Sin clientes destacados por ventas en este periodo.
                    </p>
                  ) : (
                    <ul className="sales-ranking-list">
                      {topCustomers.map((customer, index) => {
                        const ordersCount = safeNumber(customer.quantity ?? 0);
                        return (
                          <li key={`${customer.label}-${index}`}>
                            <span className="ranking-position">#{index + 1}</span>
                            <div className="ranking-details">
                              <span className="ranking-name">
                                {safeString(customer.label, "Cliente")}
                              </span>
                              <span className="ranking-amount">
                                {formatCurrency(safeNumber(customer.value))}
                              </span>
                              <span className="ranking-orders">
                                {ordersCount.toLocaleString("es-HN")} órdenes
                              </span>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              </div>
            </article>

            <article className="chart-card dual-chart-card">
              <header>
                <h3>Inventario y ganancias</h3>
                <span className="chart-caption">Panorama consolidado por tienda</span>
              </header>
              <div className="dual-chart-grid">
                <div className="chart-panel">
                  <h4>Inventario por tienda</h4>
                  {stockBreakdown.length === 0 ? (
                    <p className="muted-text">No hay tiendas registradas.</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={stockBreakdown}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                        <XAxis dataKey="label" stroke="var(--text-secondary)" />
                        <YAxis stroke="var(--text-secondary)" />
                        <Tooltip />
                        <Legend />
                        <Bar
                          dataKey="value"
                          fill={colors.chartIndigo}
                          name="Unidades"
                          radius={[6, 6, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
                <div className="chart-panel">
                  <h4>Distribución de ganancias</h4>
                  {profitSlices.length === 0 ? (
                    <p className="muted-text">No hay registros de ganancias para graficar.</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <PieChart>
                        <Tooltip formatter={(value: number) => formatCurrency(value)} />
                        <Legend />
                        <Pie
                          data={profitSlices}
                          dataKey="value"
                          nameKey="label"
                          innerRadius={60}
                          outerRadius={90}
                          paddingAngle={4}
                        >
                          {profitSlices.map((entry, index) => (
                            <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>
            </article>

            <article className="chart-card operations-health-card">
              <header>
                <h3>Salud de operaciones</h3>
                <span className="chart-caption">Pagos, ticket promedio y reparaciones</span>
              </header>
              <div className="operations-summary">
                <div>
                  <span className="summary-label">Ticket promedio</span>
                  <span className="ticket-value">{averageTicket}</span>
                </div>
              </div>
              <div className="operations-charts">
                <div className="chart-panel">
                  <h4>Pagos crédito vs contado</h4>
                  {paymentMix.length === 0 || paymentMix.every((entry) => entry.value === 0) ? (
                    <p className="muted-text">Sin operaciones registradas para este periodo.</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <PieChart>
                        <Tooltip
                          formatter={(value: number, _name, payload) => {
                            const percentage = safeNumber(
                              (payload as { payload?: SalesMetric })?.payload?.percentage ?? 0,
                            );
                            return `${formatCurrency(value)} · ${percentage.toFixed(2)}%`;
                          }}
                        />
                        <Legend />
                        <Pie
                          data={paymentMix}
                          dataKey="value"
                          nameKey="label"
                          innerRadius={55}
                          outerRadius={85}
                          paddingAngle={4}
                        >
                          {paymentMix.map((entry, index) => (
                            <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </div>
                <div className="chart-panel">
                  <h4>Estado de reparaciones</h4>
                  {repairMix.length === 0 ? (
                    <p className="muted-text">Sin órdenes de reparación registradas.</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={repairMix}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                        <XAxis dataKey="label" stroke="var(--text-secondary)" />
                        <YAxis stroke="var(--text-secondary)" />
                        <Tooltip />
                        <Legend />
                        <Bar
                          dataKey="value"
                          fill={colors.accentBright}
                          name="Órdenes"
                          radius={[6, 6, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>
            </article>
          </div>
        </>
      ) : null}
    </section>
  );
}

export default GlobalMetrics;
