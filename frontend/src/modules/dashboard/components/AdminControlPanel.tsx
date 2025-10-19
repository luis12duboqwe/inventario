import { Link } from "react-router-dom";

export type AdminControlPanelModule = {
  to: string;
  label: string;
  description: string;
  icon: JSX.Element;
  badge?: string;
};

export type AdminControlPanelProps = {
  modules: AdminControlPanelModule[];
  roleVariant: "admin" | "manager" | "operator" | "guest";
  notifications: number;
};

function AdminControlPanel({ modules, roleVariant, notifications }: AdminControlPanelProps) {
  const hasNotifications = notifications > 0;
  const notificationLabel = hasNotifications
    ? notifications === 1
      ? "1 notificación activa"
      : `${notifications} notificaciones activas`
    : "Sin notificaciones pendientes";

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
        <div
          className={`admin-control-panel__notifications admin-control-panel__notifications--${roleVariant}`}
          role="status"
          aria-live="polite"
        >
          <span className="admin-control-panel__notifications-icon" aria-hidden="true">
            🔔
          </span>
          <span className="admin-control-panel__notifications-label">{notificationLabel}</span>
        </div>
      </header>
      <div className="admin-control-panel__grid" role="list">
        {modules.map((module) => (
          <Link
            key={module.to}
            to={module.to}
            className={`admin-control-panel__card admin-control-panel__card--${roleVariant}`}
            role="listitem"
          >
            <span className="admin-control-panel__icon" aria-hidden="true">
              {module.icon}
            </span>
            <div className="admin-control-panel__content">
              <h3>{module.label}</h3>
              <p>{module.description}</p>
              {module.badge ? (
                <span className="admin-control-panel__badge" aria-label={module.badge}>
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
