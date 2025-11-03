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
import { Skeleton } from "@/ui/Skeleton"; // [PACK36-metrics]
import { safeArray, safeNumber, safeString } from "@/utils/safeValues"; // [PACK36-metrics]

const PIE_COLORS = [colors.chartCyan, colors.accentBright, colors.accent, colors.chartSky, colors.chartTeal];

function resolveStatusTone(value: number, threshold: number, inverse = false): "good" | "alert" | "info" {
  if (inverse) {
    return value <= threshold ? "good" : "alert";
  }
  return value >= threshold ? "good" : "alert";
}

/**
 * Tablero global con tarjetas, gráficos y resúmenes auditables del backend.
 *
 * El hook `useDashboard` aporta métricas normalizadas por el servicio de
 * analítica. Los estados de carga y vacíos están cubiertos por
 * `GlobalMetrics.test.tsx`, asegurando que los escenarios descritos en la nueva
 * documentación respondan de forma consistente ante datos incompletos.
 */
function GlobalMetrics() {
  const { metrics, formatCurrency, loading } = useDashboard();

  if (!metrics && loading) {
    // [PACK36-metrics]
    return (
      <section className="global-metrics" aria-busy="true">
        <div className="metric-cards">
          {Array.from({ length: 5 }).map((_, index) => (
            <article key={`metric-skeleton-${index}`} className="metric-card metric-info">
              <Skeleton lines={3} />
            </article>
          ))}
        </div>
        <div className="metric-charts">
          <div className="chart-card" style={{ padding: 24 }}>
            <Skeleton lines={10} />
          </div>
        </div>
      </section>
    );
  }

  if (!metrics) {
    // [PACK36-metrics]
    return (
      <section className="global-metrics">
        <div className="metric-empty" role="status">
          <p className="muted-text">Sin métricas disponibles por el momento.</p>
          <p className="muted-text">Actualiza la vista cuando los servicios vuelvan a responder.</p>
        </div>
      </section>
    );
  }

  const performance = metrics.global_performance ?? {
    // [PACK36-metrics]
    total_sales: 0,
    sales_count: 0,
    total_stock: 0,
    open_repairs: 0,
    gross_profit: 0,
  };
  const auditAlerts = metrics.audit_alerts ?? {
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
  const highlights = safeArray(auditAlerts.highlights);
  const formatHighlightDate = (isoString: string) => {
    const normalized = safeString(isoString, "");
    const parsed = new Date(normalized);
    if (Number.isNaN(parsed.getTime())) {
      return "Fecha desconocida";
    }
    return parsed.toLocaleString("es-MX", { dateStyle: "short", timeStyle: "short" });
  };
  const severityLabels: Record<"critical" | "warning" | "info", string> = {
    critical: "Crítica",
    warning: "Preventiva",
    info: "Informativa",
  };
  const alertsTone = useMemo(() => {
    if (pendingCount > 0 || criticalCount > 0) {
      return "alert" as const;
    }
    if (warningCount > 0) {
      return "info" as const;
    }
    return "good" as const;
  }, [criticalCount, pendingCount, warningCount]);

  const alertsValue = useMemo(() => {
    if (totalAlerts === 0) {
      return "Sin eventos";
    }
    return `${pendingCount} pendientes · ${acknowledgedCount} atendidas`;
  }, [acknowledgedCount, pendingCount, totalAlerts]);

  const cards = useMemo(
    () => [
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
        id: "stock",
        title: "Inventario total",
        value: `${safeNumber(performance.total_stock).toLocaleString("es-MX")} uds`,
        caption: "Unidades disponibles en tiendas",
        tone: "info" as const,
      },
      {
        id: "repairs",
        title: "Reparaciones abiertas",
        value: `${safeNumber(performance.open_repairs)}`,
        caption:
          safeNumber(performance.open_repairs) === 0 ? "Sin pendientes" : "Coordina cierres con taller",
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
    ],
    [alertsTone, alertsValue, auditAlerts.has_alerts, pendingCount, formatCurrency, performance]
  );

  const salesTrend = useMemo(
    () =>
      safeArray(metrics.sales_trend).map((entry) => ({
        ...entry,
        value: Number(safeNumber(entry.value).toFixed(2)),
      })),
    [metrics.sales_trend]
  );
  const stockBreakdown = safeArray(metrics.stock_breakdown);
  const profitSlices = useMemo(
    () => {
      const profit = safeArray(metrics.profit_breakdown);
      return profit.length > 0 ? profit : stockBreakdown;
    },
    [metrics.profit_breakdown, stockBreakdown]
  );
  const repairMix = safeArray(metrics.repair_mix);
  const acknowledgedEntities = useMemo(
    () => safeArray(auditAlerts.acknowledged_entities).slice(0, 3),
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
              <span className="summary-value">{criticalCount}</span>
              <span className="summary-label">Críticas</span>
            </div>
            <div className="summary-item warning" role="listitem">
              <span className="summary-value">{warningCount}</span>
              <span className="summary-label">Preventivas</span>
            </div>
            <div className="summary-item info" role="listitem">
              <span className="summary-value">{infoCount}</span>
              <span className="summary-label">Informativas</span>
            </div>
            <div className="summary-item pending" role="listitem">
              <span className="summary-value">{pendingCount}</span>
              <span className="summary-label">Pendientes</span>
            </div>
            <div className="summary-item acknowledged" role="listitem">
              <span className="summary-value">{acknowledgedCount}</span>
              <span className="summary-label">Atendidas</span>
            </div>
          </div>
          <div className="acknowledgement-meta">
            {latestAcknowledgement ? (
              <p className="muted-text">
                Último acuse: {safeString(latestAcknowledgement.entity_type, "Entidad")} #
                {safeString(latestAcknowledgement.entity_id, "-")} ·
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
                    {safeString(entity.entity_type, "Entidad")} #{safeString(entity.entity_id, "-")}
                  </span>
                  <span className="acknowledged-meta">
                    {entity.acknowledged_by_name ?? "Usuario corporativo"} ·
                    {" "}
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
                <YAxis stroke="var(--text-secondary)" tickFormatter={(value) => formatCurrency(value).replace("MX$", "")} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Legend />
                <Line type="monotone" dataKey="value" stroke={colors.chartCyan} strokeWidth={2} dot={{ r: 3 }} name="Ventas" />
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
                <Bar dataKey="value" fill={colors.chartIndigo} name="Unidades" radius={[6, 6, 0, 0]} />
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
                <Bar dataKey="value" fill={colors.accentBright} name="Órdenes" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </article>
      </div>
    </section>
  );
}

export default GlobalMetrics;
