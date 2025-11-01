import type {
  SyncHybridForecast,
  SyncHybridModuleBreakdownItem,
  SyncHybridOverview,
  SyncHybridProgress,
  SyncQueueSummary,
} from "../../../api";

const numberFormatter = new Intl.NumberFormat("es-MX");
const percentFormatter = new Intl.NumberFormat("es-MX", {
  maximumFractionDigits: 1,
  minimumFractionDigits: 0,
});

function formatPercent(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "—";
  }
  return `${percentFormatter.format(Math.max(0, Math.min(100, value)))} %`;
}

function formatNumber(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "—";
  }
  return numberFormatter.format(value);
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  try {
    return new Date(value).toLocaleString("es-MX");
  } catch (error) {
    return "—";
  }
}

function formatMinutes(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "—";
  }
  if (value < 1) {
    return "< 1 minuto";
  }
  const hours = Math.floor(value / 60);
  const minutes = Math.round(value % 60);
  if (hours <= 0) {
    return `${minutes} min`;
  }
  if (minutes === 0) {
    return `${hours} h`;
  }
  return `${hours} h ${minutes} min`;
}

type SyncSummaryProps = {
  summary: SyncQueueSummary | null;
  progress: SyncHybridProgress | null;
  forecast: SyncHybridForecast | null;
  breakdown: SyncHybridModuleBreakdownItem[];
  overview: SyncHybridOverview | null;
};

function renderBreakdownRow(item: SyncHybridModuleBreakdownItem) {
  return (
    <tr key={item.module}>
      <td className="sync-branch-name">
        <strong>{item.label}</strong>
        <small>{item.module}</small>
      </td>
      <td>{formatPercent(item.percent)}</td>
      <td>{formatNumber(item.pending)}</td>
      <td>{formatNumber(item.failed)}</td>
      <td>{`${formatNumber(item.queue.pending)}/${formatNumber(item.queue.failed)}`}</td>
      <td>{`${formatNumber(item.outbox.pending)}/${formatNumber(item.outbox.failed)}`}</td>
    </tr>
  );
}

export function SyncSummary({ summary, progress, forecast, breakdown, overview }: SyncSummaryProps) {
  const total = progress?.total ?? summary?.total ?? 0;
  const processed = progress?.processed ?? summary?.processed ?? 0;
  const pending = progress?.pending ?? summary?.pending ?? 0;
  const failed = progress?.failed ?? summary?.failed ?? 0;
  const percent =
    overview?.percent ?? progress?.percent ?? summary?.percent ?? (total === 0 ? 100 : (processed / total) * 100);

  const lastUpdated = summary?.last_updated ?? overview?.generated_at ?? null;
  const oldestPending = summary?.oldest_pending ?? overview?.remaining?.estimated_completion ?? null;

  const eventsPerMinute = forecast?.events_per_minute ?? null;
  const successRate = forecast?.success_rate ?? null;
  const backlogPending = forecast?.backlog_pending ?? overview?.remaining?.pending ?? null;
  const backlogFailed = forecast?.backlog_failed ?? overview?.remaining?.failed ?? null;
  const estimatedMinutes = forecast?.estimated_minutes_remaining ?? overview?.remaining?.estimated_minutes_remaining ?? null;
  const estimatedCompletion = forecast?.estimated_completion ?? overview?.remaining?.estimated_completion ?? null;

  const modules = breakdown.length > 0 ? breakdown : overview?.breakdown ?? [];

  return (
    <section aria-labelledby="sync-summary-heading">
      <div className="sync-dashboard__summary">
        <article className="sync-metric">
          <span>Avance total</span>
          <strong>{formatPercent(percent)}</strong>
          <small>
            {formatNumber(processed)} de {formatNumber(total)} eventos procesados
          </small>
        </article>
        <article className="sync-metric">
          <span>En cola</span>
          <strong>{formatNumber(pending)}</strong>
          <small>Última actualización: {formatDate(lastUpdated)}</small>
        </article>
        <article className="sync-metric">
          <span>Fallidos</span>
          <strong>{formatNumber(failed)}</strong>
          <small>Próxima revisión: {formatDate(oldestPending)}</small>
        </article>
        <article className="sync-metric">
          <span>Ritmo reciente</span>
          <strong>{eventsPerMinute ? `${eventsPerMinute.toFixed(1)} evt/min` : "—"}</strong>
          <small>Tasa de éxito: {formatPercent(successRate)}</small>
        </article>
        <article className="sync-metric">
          <span>Backlog</span>
          <strong>{formatNumber(backlogPending)}</strong>
          <small>Fallidos pendientes: {formatNumber(backlogFailed)}</small>
        </article>
        <article className="sync-metric">
          <span>Estimación</span>
          <strong>{formatMinutes(estimatedMinutes)}</strong>
          <small>Final estimado: {formatDate(estimatedCompletion)}</small>
        </article>
      </div>

      {modules.length > 0 ? (
        <div className="sync-dashboard__logs" aria-live="polite">
          <h2 id="sync-summary-heading">Desglose por módulo</h2>
          <div className="card">
            <table className="sync-branch-table">
              <thead>
                <tr>
                  <th>Módulo</th>
                  <th>Avance</th>
                  <th>Pendientes</th>
                  <th>Fallidos</th>
                  <th>Cola local</th>
                  <th>Outbox remoto</th>
                </tr>
              </thead>
              <tbody>{modules.map(renderBreakdownRow)}</tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export default SyncSummary;
