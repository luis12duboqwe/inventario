import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import NotificationCenter, {
  type NotificationCenterItem,
} from "./NotificationCenter";

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
    (AdminControlPanelModule & { descriptionId: string; ariaLabel: string; state: "active" | "inactive" })[]
  >(
    () =>
      modules.map((module) => {
        const sanitizedId = module.to.replace(/[^a-zA-Z0-9]/g, "-");
        const descriptionId = `${sanitizedId}-description`;
        const state = module.isActive ? "active" : "inactive";
        const ariaLabel = module.srHint
          ? `${module.label}. ${module.srHint}`
          : module.label;
        return {
          ...module,
          descriptionId,
          ariaLabel,
          state,
        };
      }),
    [modules],
  );

  return (
    <section className="admin-control-panel" aria-label="Panel central de administración">
      <header className="admin-control-panel__header">
        <div>
          <h2>Centro de control Softmobile</h2>
          <p>
            Accede rápidamente a los módulos clave y supervisa el estado general de la
            operación sin abandonar el panel principal.
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
      <ul className="admin-control-panel__grid" role="list">
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
                    className={`admin-control-panel__badge admin-control-panel__badge--${module.badgeVariant ?? "default"}`}
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
