import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import NotificationCenter, { type NotificationCenterItem } from "./NotificationCenter";
import type { RiskAlert } from "../../../api";

export type AdminControlPanelModule = {
  to: string;
  label: string;
  description: string;
  icon: JSX.Element;
  badge?: string;
  badgeVariant?: "default" | "warning" | "danger" | "info";
  isActive: boolean;
  srHint?: string;
};

export type AdminControlPanelProps = {
  modules: AdminControlPanelModule[];
  roleVariant: "admin" | "manager" | "operator" | "guest";
  notifications: number;
  notificationItems: NotificationCenterItem[];
  riskAlerts?: RiskAlert[];
};

/**
 * Panel central del dashboard que agrupa accesos rápidos y el centro de alertas.
 *
 * El componente mantiene sincronizado el resumen de notificaciones con
 * `NotificationCenter` y respeta los requisitos de accesibilidad del mandato
 * Softmobile (por ejemplo, `aria-current`, `srHint`). Las pruebas en
 * `AdminControlPanel.test.tsx` verifican los diferentes estados de tarjetas y
 * badges para evitar regresiones.
 */
function AdminControlPanel({
  modules,
  roleVariant,
  notifications,
  notificationItems,
  riskAlerts = [],
}: AdminControlPanelProps) {
  const hasNotifications = notifications > 0;
  const notificationLabel = hasNotifications
    ? notifications === 1
      ? "1 notificación activa"
      : `${notifications} notificaciones activas`
    : "Sin notificaciones pendientes";
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(hasNotifications);

  useEffect(() => {
    setIsNotificationsOpen(hasNotifications);
  }, [hasNotifications]);

  const moduleCards = useMemo<
    (AdminControlPanelModule & {
      descriptionId: string;
      ariaLabel: string;
      state: "active" | "inactive";
    })[]
  >(
    () =>
      modules.map((module) => {
        const sanitizedId = module.to.replace(/[^a-zA-Z0-9]/g, "-");
        const descriptionId = `${sanitizedId}-description`;
        const state = module.isActive ? "active" : "inactive";
        const ariaLabel = module.srHint ? `${module.label}. ${module.srHint}` : module.label;
        return {
          ...module,
          descriptionId,
          ariaLabel,
          state,
        };
      }),
    [modules],
  );

  const visibleRiskAlerts = useMemo(() => riskAlerts.slice(0, 4), [riskAlerts]);

  return (
    <section className="admin-control-panel" aria-label="Panel central de administración">
      <header className="admin-control-panel__header">
        <div>
          <h2>Centro de control Softmobile</h2>
          <p>
            Accede rápidamente a los módulos clave y supervisa el estado general de la operación sin
            abandonar el panel principal.
          </p>
        </div>
        <NotificationCenter
          open={isNotificationsOpen}
          onToggle={setIsNotificationsOpen}
          roleVariant={roleVariant}
          summary={notificationLabel}
          items={notificationItems}
        />
      </header>
      <section
        className="admin-control-panel__risk"
        aria-label="Panel de riesgos y alertas automáticas"
      >
        <div className="admin-control-panel__risk-header">
          <div>
            <h3>Riesgos operativos</h3>
            <p className="admin-control-panel__risk-subtitle">
              Descuentos inusuales, anulaciones recurrentes y eventos críticos.
            </p>
          </div>
          <span className="admin-control-panel__risk-pill" aria-live="polite">
            {riskAlerts.length > 0 ? `${riskAlerts.length} alertas` : "Sin alertas"}
          </span>
        </div>
        {visibleRiskAlerts.length > 0 ? (
          <ul className="admin-control-panel__risk-list">
            {visibleRiskAlerts.map((alert) => (
              <li
                key={alert.code}
                className={`admin-control-panel__risk-item admin-control-panel__risk-item--${alert.severity}`}
              >
                <div className="admin-control-panel__risk-item-header">
                  <span className="admin-control-panel__risk-label">{alert.title}</span>
                  <span
                    className="admin-control-panel__risk-severity"
                    aria-label={`Severidad ${alert.severity}`}
                  >
                    {alert.severity.toUpperCase()}
                  </span>
                </div>
                <p className="admin-control-panel__risk-description">{alert.description}</p>
                <div className="admin-control-panel__risk-meta">
                  <span className="badge muted">{alert.occurrences} eventos</span>
                  {alert.detail?.umbral ? (
                    <span className="badge info">Umbral {String(alert.detail.umbral)}%</span>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="admin-control-panel__risk-empty">
            Sin alertas de riesgo en el periodo supervisado.
          </p>
        )}
      </section>
      <ul className="admin-control-panel__grid">
        {moduleCards.map((module) => (
          <li key={module.to} className="admin-control-panel__grid-item">
            <Link
              to={module.to}
              className={`admin-control-panel__card admin-control-panel__card--${roleVariant}`}
              aria-describedby={module.descriptionId}
              aria-label={module.ariaLabel}
              aria-current={module.isActive ? "page" : undefined}
              data-state={module.state}
            >
              <span className="admin-control-panel__icon" aria-hidden="true">
                {module.icon}
              </span>
              <div className="admin-control-panel__content">
                <h3>{module.label}</h3>
                <p id={module.descriptionId}>{module.description}</p>
                {module.badge ? (
                  <span
                    className={`admin-control-panel__badge admin-control-panel__badge--${
                      module.badgeVariant ?? "default"
                    }`}
                    aria-label={module.badge}
                  >
                    {module.badge}
                  </span>
                ) : null}
                {module.srHint ? <span className="sr-only">{module.srHint}</span> : null}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default AdminControlPanel;
