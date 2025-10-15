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

const PIE_COLORS = ["#06b6d4", "#22d3ee", "#38bdf8", "#0ea5e9", "#0891b2"];

function resolveStatusTone(value: number, threshold: number, inverse = false): "good" | "alert" | "info" {
  if (inverse) {
    return value <= threshold ? "good" : "alert";
  }
  return value >= threshold ? "good" : "alert";
}

function GlobalMetrics() {
  const { metrics, formatCurrency } = useDashboard();

  if (!metrics) {
    return null;
  }

  const performance = metrics.global_performance;
  const auditAlerts = metrics.audit_alerts;
  const formatHighlightDate = (isoString: string) =>
    new Date(isoString).toLocaleString("es-MX", { dateStyle: "short", timeStyle: "short" });
  const severityLabels: Record<"critical" | "warning" | "info", string> = {
    critical: "Crítica",
    warning: "Preventiva",
    info: "Informativa",
  };
  const alertsTone = useMemo(() => {
    if (auditAlerts.pending_count > 0 || auditAlerts.critical > 0) {
      return "alert" as const;
    }
    if (auditAlerts.warning > 0) {
      return "info" as const;
    }
    return "good" as const;
  }, [auditAlerts.critical, auditAlerts.pending_count, auditAlerts.warning]);

  const alertsValue = useMemo(() => {
    if (auditAlerts.total === 0) {
      return "Sin eventos";
    }
    return `${auditAlerts.pending_count} pendientes · ${auditAlerts.acknowledged_count} atendidas`;
  }, [auditAlerts.acknowledged_count, auditAlerts.pending_count, auditAlerts.total]);

  const cards = useMemo(
    () => [
      {
        id: "sales",
        title: "Ventas netas",
        value: formatCurrency(performance.total_sales),
        caption: `${performance.sales_count} operaciones cerradas`,
        tone: resolveStatusTone(performance.total_sales, 1),
      },
      {
        id: "profit",
        title: "Ganancia bruta",
        value: formatCurrency(performance.gross_profit),
        caption: performance.gross_profit >= 0 ? "Margen positivo" : "Atiende descuentos excesivos",
        tone: resolveStatusTone(performance.gross_profit, 0),
      },
      {
        id: "stock",
        title: "Inventario total",
        value: `${performance.total_stock.toLocaleString("es-MX")} uds`,
        caption: "Unidades disponibles en tiendas",
        tone: "info" as const,
      },
      {
        id: "repairs",
        title: "Reparaciones abiertas",
        value: `${performance.open_repairs}`,
        caption: performance.open_repairs === 0 ? "Sin pendientes" : "Coordina cierres con taller",
        tone: resolveStatusTone(performance.open_repairs, 0, true),
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
    ],
    [alertsTone, alertsValue, auditAlerts.has_alerts, auditAlerts.pending_count, formatCurrency, performance]
  );

  const salesTrend = useMemo(
    () => metrics.sales_trend.map((entry) => ({ ...entry, value: Number(entry.value.toFixed(2)) })),
    [metrics.sales_trend]
  );
  const stockBreakdown = metrics.stock_breakdown;
  const profitSlices = useMemo(
    () => (metrics.profit_breakdown.length > 0 ? metrics.profit_breakdown : metrics.stock_breakdown),
    [metrics.profit_breakdown, metrics.stock_breakdown]
  );
  const repairMix = metrics.repair_mix;
  const acknowledgedEntities = useMemo(
    () => auditAlerts.acknowledged_entities.slice(0, 3),
    [auditAlerts.acknowledged_entities]
  );
  const latestAcknowledgement = acknowledgedEntities.length > 0 ? acknowledgedEntities[0] : null;

  return (
    <section className="global-metrics">
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
        <article className="chart-card audit-alerts-card">
          <header>
            <h3>Alertas y respuestas rápidas</h3>
            <span className="chart-caption">Consolidado corporativo</span>
          </header>
          <div className="alerts-summary" role="list">
            <div className="summary-item critical" role="listitem">
              <span className="summary-value">{auditAlerts.critical}</span>
              <span className="summary-label">Críticas</span>
            </div>
            <div className="summary-item warning" role="listitem">
              <span className="summary-value">{auditAlerts.warning}</span>
              <span className="summary-label">Preventivas</span>
            </div>
            <div className="summary-item info" role="listitem">
              <span className="summary-value">{auditAlerts.info}</span>
              <span className="summary-label">Informativas</span>
            </div>
            <div className="summary-item pending" role="listitem">
              <span className="summary-value">{auditAlerts.pending_count}</span>
              <span className="summary-label">Pendientes</span>
            </div>
            <div className="summary-item acknowledged" role="listitem">
              <span className="summary-value">{auditAlerts.acknowledged_count}</span>
              <span className="summary-label">Atendidas</span>
            </div>
          </div>
          <div className="acknowledgement-meta">
            {latestAcknowledgement ? (
              <p className="muted-text">
                Último acuse: {latestAcknowledgement.entity_type} #{latestAcknowledgement.entity_id} ·
                {" "}
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
          {auditAlerts.highlights.length === 0 ? (
            <p className="muted-text">
              {auditAlerts.has_alerts
                ? "Hay incidencias registradas, revisa el módulo de Seguridad para más contexto."
                : "Sin incidentes críticos o preventivos en el periodo reciente."}
            </p>
          ) : (
            <ul className="alerts-list">
              {auditAlerts.highlights.map((highlight) => (
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
                    {entity.entity_type} #{entity.entity_id}
                  </span>
                  <span className="acknowledged-meta">
                    {entity.acknowledged_by_name ?? "Usuario corporativo"} · {formatHighlightDate(entity.acknowledged_at)}
                    {entity.note ? ` — ${entity.note}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
          {auditAlerts.pending_count > 0 ? (
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
                <YAxis stroke="var(--text-secondary)" tickFormatter={(value) => formatCurrency(value).replace("MX$", "")} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#06b6d4" strokeWidth={2} dot={{ r: 3 }} name="Ventas" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </article>

        <article className="chart-card">
          <header>
            <h3>Inventario por tienda</h3>
            <span className="chart-caption">Unidades registradas</span>
          </header>
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
                <Bar dataKey="value" fill="#1d4ed8" name="Unidades" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </article>

        <article className="chart-card">
          <header>
            <h3>Distribución de ganancias</h3>
            <span className="chart-caption">Participación por tienda</span>
          </header>
          {profitSlices.length === 0 ? (
            <p className="muted-text">No hay registros de ganancias para graficar.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Legend />
                <Pie data={profitSlices} dataKey="value" nameKey="label" innerRadius={60} outerRadius={90} paddingAngle={4}>
                  {profitSlices.map((entry, index) => (
                    <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          )}
        </article>

        <article className="chart-card">
          <header>
            <h3>Estado de reparaciones</h3>
            <span className="chart-caption">Resumen global</span>
          </header>
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
                <Bar dataKey="value" fill="#22d3ee" name="Órdenes" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </article>
      </div>
    </section>
  );
}

export default GlobalMetrics;
