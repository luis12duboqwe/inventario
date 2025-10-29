import { Activity, RefreshCcw, ShieldAlert, Users as UsersIcon } from "lucide-react";

import type { UserDashboardMetrics } from "../../../api";
import LoadingOverlay from "../../../shared/components/LoadingOverlay";

const formatDateTime = (value: string | null | undefined): string => {
  if (!value) {
    return "—";
  }
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return new Intl.DateTimeFormat("es-MX", { dateStyle: "short", timeStyle: "short" }).format(date);
  } catch {
    return value;
  }
};

export type SummaryCardsProps = {
  dashboard: UserDashboardMetrics | null;
  loading: boolean;
  onRefresh: () => void;
};

function SummaryCards({ dashboard, loading, onRefresh }: SummaryCardsProps) {
  const totals = dashboard?.totals ?? { total: 0, active: 0, inactive: 0, locked: 0 };
  const recentActivity = dashboard?.recent_activity?.slice(0, 5) ?? [];
  const recentSessions = dashboard?.active_sessions?.slice(0, 5) ?? [];
  const alerts = dashboard?.audit_alerts;

  return (
    <section className="user-dashboard card-section">
      <header className="user-dashboard__header">
        <div>
          <h3>Panel de seguridad y accesos</h3>
          <p className="card-subtitle">Actividad reciente, sesiones activas y alertas corporativas</p>
        </div>
        <button type="button" className="button button-secondary" onClick={onRefresh} disabled={loading}>
          <RefreshCcw size={16} aria-hidden="true" />
          Actualizar
        </button>
      </header>
      <div className="user-dashboard__body">
        <div className="user-dashboard__totals">
          <div className="stat-card">
            <UsersIcon size={18} aria-hidden="true" />
            <div>
              <span className="stat-card__label">Usuarios totales</span>
              <strong className="stat-card__value">{totals.total}</strong>
            </div>
          </div>
          <div className="stat-card stat-card--success">
            <UsersIcon size={18} aria-hidden="true" />
            <div>
              <span className="stat-card__label">Activos</span>
              <strong className="stat-card__value">{totals.active}</strong>
            </div>
          </div>
          <div className="stat-card stat-card--warning">
            <UsersIcon size={18} aria-hidden="true" />
            <div>
              <span className="stat-card__label">Inactivos</span>
              <strong className="stat-card__value">{totals.inactive}</strong>
            </div>
          </div>
          <div className="stat-card stat-card--alert">
            <ShieldAlert size={18} aria-hidden="true" />
            <div>
              <span className="stat-card__label">Bloqueados</span>
              <strong className="stat-card__value">{totals.locked}</strong>
            </div>
          </div>
        </div>
        <div className="user-dashboard__columns">
          <div className="user-dashboard__column">
            <div className="user-dashboard__column-title">
              <Activity size={16} aria-hidden="true" />
              <h4>Actividad reciente</h4>
            </div>
            {recentActivity.length === 0 ? (
              <p className="muted-text">Sin movimientos relevantes en las últimas horas.</p>
            ) : (
              <ul className="user-dashboard__list">
                {recentActivity.map((item) => (
                  <li key={item.id}>
                    <div className={`badge badge-${item.severity}`} aria-label={`Severidad ${item.severity}`} />
                    <div>
                      <p className="user-dashboard__list-title">{item.action}</p>
                      <p className="user-dashboard__list-meta">
                        {formatDateTime(item.created_at)} · {item.performed_by_name ?? "Sistema"}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="user-dashboard__column">
            <div className="user-dashboard__column-title">
              <UsersIcon size={16} aria-hidden="true" />
              <h4>Sesiones activas</h4>
            </div>
            {recentSessions.length === 0 ? (
              <p className="muted-text">No hay sesiones corporativas activas.</p>
            ) : (
              <ul className="user-dashboard__list">
                {recentSessions.map((session) => (
                  <li key={session.session_id}>
                    <div className={`status-indicator status-${session.status}`} aria-hidden="true" />
                    <div>
                      <p className="user-dashboard__list-title">{session.username}</p>
                      <p className="user-dashboard__list-meta">Inicio: {formatDateTime(session.created_at)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="user-dashboard__column">
            <div className="user-dashboard__column-title">
              <ShieldAlert size={16} aria-hidden="true" />
              <h4>Alertas</h4>
            </div>
            {alerts ? (
              <div className="user-dashboard__alerts">
                <p>
                  <strong>Críticas:</strong> {alerts.critical}
                </p>
                <p>
                  <strong>Preventivas:</strong> {alerts.warning}
                </p>
                <p>
                  <strong>Informativas:</strong> {alerts.info}
                </p>
                <p>
                  <strong>Pendientes:</strong> {alerts.pending_count}
                </p>
              </div>
            ) : (
              <p className="muted-text">Sin alertas registradas.</p>
            )}
          </div>
        </div>
      </div>
      <LoadingOverlay visible={loading} label="Sincronizando panel de seguridad..." />
    </section>
  );
}

export default SummaryCards;
