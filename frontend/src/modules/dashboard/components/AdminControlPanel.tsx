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
};

export type AdminControlPanelProps = {
  modules: AdminControlPanelModule[];
  roleVariant: "admin" | "manager" | "operator" | "guest";
  notifications: number;
  notificationItems: NotificationCenterItem[];
};

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

  const moduleCards = useMemo<(AdminControlPanelModule & { descriptionId: string })[]>(
    () =>
      modules.map((module) => {
        const sanitizedId = module.to.replace(/[^a-zA-Z0-9]/g, "-");
        const descriptionId = `${sanitizedId}-description`;
        return {
          ...module,
          descriptionId,
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
      <div className="admin-control-panel__grid" role="list">
        {moduleCards.map((module) => (
          <Link
            key={module.to}
            to={module.to}
            className={`admin-control-panel__card admin-control-panel__card--${roleVariant}`}
            role="listitem"
            aria-describedby={module.descriptionId}
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
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

export default AdminControlPanel;
