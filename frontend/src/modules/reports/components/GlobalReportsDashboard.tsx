import { useCallback, useEffect, useMemo, useState } from "react";
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

import {
  downloadGlobalReportCsv,
  downloadGlobalReportPdf,
  downloadGlobalReportXlsx,
  getGlobalReportDashboard,
  getGlobalReportOverview,
  type GlobalReportAlert,
  type GlobalReportDashboard,
  type GlobalReportFilters,
  type GlobalReportOverview,
  type SystemLogLevel,
} from "../../../api";
import LoadingOverlay from "../../../shared/components/LoadingOverlay";
import ScrollableTable from "../../../shared/components/ScrollableTable";
import { promptCorporateReason } from "../../../utils/corporateReason";
import { useReportsModule } from "../hooks/useReportsModule";
import { colors } from "../../../theme/designTokens";

const PIE_COLORS = [
  colors.accent,
  colors.chartIndigo,
  colors.accentBright,
  colors.chartSky,
  colors.backgroundSecondary,
  colors.chartCyan,
];

const severityLabels: Record<SystemLogLevel, string> = {
  info: "Info",
  warning: "Alerta",
  error: "Error",
  critical: "Crítico",
};

function formatDateTime(value: string | undefined | null): string {
  if (!value) {
    return "—";
  }
  try {
    const date = new Date(value);
    return new Intl.DateTimeFormat("es-HN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  } catch {
    return value;
  }
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("es-HN", { maximumFractionDigits: 0 }).format(value);
}

const severityOptions: { value: SystemLogLevel | "all"; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "info", label: "Info" },
  { value: "warning", label: "Alertas" },
  { value: "error", label: "Errores" },
  { value: "critical", label: "Críticas" },
];

function GlobalReportsDashboard() {
  const { token, pushToast } = useReportsModule();
  const [overview, setOverview] = useState<GlobalReportOverview | null>(null);
  const [dashboard, setDashboard] = useState<GlobalReportDashboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [severity, setSeverity] = useState<SystemLogLevel | "all">("all");

  const filters = useMemo<GlobalReportFilters>(() => {
    const result: GlobalReportFilters = {};
    if (dateFrom) {
      result.dateFrom = `${dateFrom}T00:00:00`;
    }
    if (dateTo) {
      result.dateTo = `${dateTo}T23:59:59`;
    }
    if (moduleFilter.trim()) {
      result.module = moduleFilter.trim();
    }
    if (severity !== "all") {
      result.severity = severity;
    }
    return result;
  }, [dateFrom, dateTo, moduleFilter, severity]);

  const activityData = useMemo(() => {
    if (!dashboard) {
      return [];
    }
    return dashboard.activity_series.map((point) => ({
      date: point.date,
      info: point.info,
      warning: point.warning,
      error: point.error,
      critical: point.critical,
      system_errors: point.system_errors,
    }));
  }, [dashboard]);

  const moduleData = useMemo(() => {
    if (!dashboard) {
      return [];
    }
    return dashboard.module_distribution.map((item) => ({
      name: item.name,
      value: item.total,
    }));
  }, [dashboard]);

  const severityData = useMemo(() => {
    if (!dashboard) {
      return [];
    }
    return dashboard.severity_distribution.map((item) => ({
      name: item.name,
      value: item.total,
    }));
  }, [dashboard]);

  const totals = overview?.totals;
  const alerts: GlobalReportAlert[] = overview?.alerts ?? [];
  const recentLogs = overview?.recent_logs ?? [];
  const recentErrors = overview?.recent_errors ?? [];

  const handleDownload = useCallback(
    async (
      callback: (tokenValue: string, reason: string, currentFilters: GlobalReportFilters) => Promise<void>,
      suggestedReason: string,
    ) => {
      const reason = promptCorporateReason(suggestedReason);
      if (reason === null) {
        pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
        return;
      }
      if (reason.trim().length < 5) {
        pushToast({ message: "El motivo corporativo debe tener al menos 5 caracteres.", variant: "error" });
        return;
      }
      try {
        await callback(token, reason.trim(), filters);
        pushToast({ message: "Descarga iniciada", variant: "success" });
      } catch (downloadError) {
        const message =
          downloadError instanceof Error
            ? downloadError.message
            : "No fue posible exportar el reporte global";
        pushToast({ message, variant: "error" });
      }
    },
    [filters, pushToast, token],
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewResponse, dashboardResponse] = await Promise.all([
        getGlobalReportOverview(token, filters),
        getGlobalReportDashboard(token, filters),
      ]);
      setOverview(overviewResponse);
      setDashboard(dashboardResponse);
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : "No fue posible cargar los reportes globales";
      setError(message);
      pushToast({ message, variant: "error" });
      setOverview(null);
      setDashboard(null);
    } finally {
      setLoading(false);
    }
  }, [filters, pushToast, token]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <section className="card reports-card section-scroll">
      <header className="reports-card__header">
        <div>
          <h2 className="accent-title">Reportes globales y notificaciones</h2>
          <p className="card-subtitle">
            Supervisión consolidada de actividad, errores críticos y alertas de sincronización corporativa.
          </p>
        </div>
        <div className="reports-card__actions">
          <div className="reports-card__filters">
            <label>
              <span>Desde</span>
              <input
                type="date"
                value={dateFrom}
                max={dateTo || undefined}
                onChange={(event) => setDateFrom(event.target.value)}
              />
            </label>
            <label>
              <span>Hasta</span>
              <input
                type="date"
                value={dateTo}
                min={dateFrom || undefined}
                onChange={(event) => setDateTo(event.target.value)}
              />
            </label>
            <label>
              <span>Módulo</span>
              <input
                type="text"
                placeholder="inventario, sincronizacion…"
                value={moduleFilter}
                onChange={(event) => setModuleFilter(event.target.value)}
              />
            </label>
            <label>
              <span>Severidad</span>
              <select value={severity} onChange={(event) => setSeverity(event.target.value as SystemLogLevel | "all")}>
                {severityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <button className="btn btn--ghost" type="button" onClick={loadData} aria-busy={loading}>
              Actualizar
            </button>
          </div>
          <div className="reports-card__downloads">
            <button
              className="btn btn--primary"
              type="button"
              onClick={() => handleDownload(downloadGlobalReportPdf, "Descarga PDF reportes globales")}
              aria-busy={loading}
            >
              Descargar PDF
            </button>
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => handleDownload(downloadGlobalReportXlsx, "Descarga Excel reportes globales")}
              aria-busy={loading}
            >
              Exportar Excel
            </button>
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => handleDownload(downloadGlobalReportCsv, "Descarga CSV reportes globales")}
              aria-busy={loading}
            >
              Exportar CSV
            </button>
          </div>
        </div>
      </header>

      {error ? <p className="error-text">{error}</p> : null}
      <LoadingOverlay visible={loading} label="Generando reportes globales..." />

      <div className="metric-cards">
        <article className="metric-card metric-primary">
          <h3>Registros totales</h3>
          <p className="metric-card__value">{formatNumber(totals?.logs ?? 0)}</p>
          <p className="metric-card__hint">Última actividad: {formatDateTime(totals?.last_activity_at ?? null)}</p>
        </article>
        <article className="metric-card metric-alert">
          <h3>Errores críticos</h3>
          <p className="metric-card__value">{formatNumber(totals?.errors ?? 0)}</p>
          <p className="metric-card__hint">Eventos CRITICAL: {formatNumber(totals?.critical ?? 0)}</p>
        </article>
        <article className="metric-card metric-info">
          <h3>Sync pendientes</h3>
          <p className="metric-card__value">{formatNumber(totals?.sync_pending ?? 0)}</p>
          <p className="metric-card__hint">Fallidas: {formatNumber(totals?.sync_failed ?? 0)}</p>
        </article>
        <article className="metric-card metric-secondary">
          <h3>Eventos informativos</h3>
          <p className="metric-card__value">{formatNumber(totals?.info ?? 0)}</p>
          <p className="metric-card__hint">Alertas: {formatNumber(totals?.warning ?? 0)}</p>
        </article>
      </div>

      <div className="reports-chart-grid">
        <article className="chart-card">
          <header>
            <h3>Tendencia de actividad</h3>
            <span className="chart-caption">Eventos por día</span>
          </header>
          {activityData.length === 0 ? (
            <p className="muted-text">Sin datos suficientes para graficar el periodo seleccionado.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                <XAxis dataKey="date" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="info" name="Info" stroke={colors.accent} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="warning" name="Alertas" stroke={colors.warning} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="error" name="Errores" stroke={colors.chartOrange} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="critical" name="Críticos" stroke={colors.danger} strokeWidth={2} dot={false} />
                <Line
                  type="monotone"
                  dataKey="system_errors"
                  name="Errores sistema"
                  stroke={colors.accentStrong}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </article>

        <article className="chart-card">
          <header>
            <h3>Eventos por módulo</h3>
            <span className="chart-caption">Distribución actual</span>
          </header>
          {moduleData.length === 0 ? (
            <p className="muted-text">No hay eventos registrados para el filtro aplicado.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={moduleData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
                <XAxis dataKey="name" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" name="Eventos" fill={colors.chartIndigo} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </article>

        <article className="chart-card">
          <header>
            <h3>Severidad consolidada</h3>
            <span className="chart-caption">Participación por nivel</span>
          </header>
          {severityData.length === 0 ? (
            <p className="muted-text">Sin datos disponibles para graficar severidades.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Tooltip />
                <Legend />
                <Pie data={severityData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={90} paddingAngle={4}>
                  {severityData.map((entry, index) => (
                    <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          )}
        </article>
      </div>

      <div className="reports-secondary-grid">
        <article className="card reports-panel">
          <div className="reports-panel__header">
            <h3>Alertas automáticas</h3>
            <p className="card-subtitle">Monitoreo corporativo de errores y sincronización.</p>
          </div>
          {alerts.length === 0 ? (
            <p className="muted-text">Sin alertas activas en el periodo seleccionado.</p>
          ) : (
            <ul className="reports-alerts">
              {alerts.map((alert) => {
                const severityLevel = alert.level;
                const label = severityLabels[severityLevel] ?? severityLevel;
                return (
                  <li key={`${alert.type}-${alert.module ?? "global"}-${alert.message}`}
                      className={`reports-alert reports-alert--${severityLevel}`}>
                    <div className="reports-alert__header">
                      <span className="reports-alert__badge">{label}</span>
                      <span className="reports-alert__module">{alert.module ?? "global"}</span>
                      <span className="reports-alert__count">{alert.count} eventos</span>
                    </div>
                    <p className="reports-alert__message">{alert.message}</p>
                    <p className="reports-alert__timestamp">Último evento: {formatDateTime(alert.occurred_at)}</p>
                  </li>
                );
              })}
            </ul>
          )}
        </article>

        <article className="card reports-panel">
          <div className="reports-panel__header">
            <h3>Actividad reciente</h3>
            <p className="card-subtitle">Bitácora global de eventos registrados.</p>
          </div>
          {recentLogs.length === 0 ? (
            <p className="muted-text">No se encontraron registros para los filtros aplicados.</p>
          ) : (
            <ScrollableTable
              items={recentLogs}
              itemKey={(item) => item.id_log}
              title="Eventos"
              ariaLabel="Tabla de eventos recientes"
              renderHead={() => (
                <>
                  <th scope="col">Fecha</th>
                  <th scope="col">Módulo</th>
                  <th scope="col">Acción</th>
                  <th scope="col">Severidad</th>
                  <th scope="col">Usuario</th>
                </>
              )}
              renderRow={(item) => (
                <tr>
                  <td data-label="Fecha">{formatDateTime(item.fecha)}</td>
                  <td data-label="Módulo">{item.modulo}</td>
                  <td data-label="Acción">{item.accion}</td>
                  <td data-label="Severidad">{severityLabels[item.nivel]}</td>
                  <td data-label="Usuario">{item.usuario ?? "Sistema"}</td>
                </tr>
              )}
            />
          )}
        </article>

        <article className="card reports-panel">
          <div className="reports-panel__header">
            <h3>Errores del sistema</h3>
            <p className="card-subtitle">Incidentes críticos y trazas registradas.</p>
          </div>
          {recentErrors.length === 0 ? (
            <p className="muted-text">Sin errores registrados en el periodo seleccionado.</p>
          ) : (
            <ScrollableTable
              items={recentErrors}
              itemKey={(item) => item.id_error}
              title="Errores"
              ariaLabel="Tabla de errores recientes"
              renderHead={() => (
                <>
                  <th scope="col">Fecha</th>
                  <th scope="col">Módulo</th>
                  <th scope="col">Mensaje</th>
                  <th scope="col">Responsable</th>
                </>
              )}
              renderRow={(item) => (
                <tr>
                  <td data-label="Fecha">{formatDateTime(item.fecha)}</td>
                  <td data-label="Módulo">{item.modulo}</td>
                  <td data-label="Mensaje">{item.mensaje}</td>
                  <td data-label="Responsable">{item.usuario ?? "Sistema"}</td>
                </tr>
              )}
            />
          )}
        </article>
      </div>
    </section>
  );
}

export default GlobalReportsDashboard;
