import { useMemo } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  BarChart3,
  Boxes,
  Cog,
  Repeat,
  ShieldCheck,
  UserCog,
  Wrench,
} from "lucide-react";
import { useDashboard } from "../context/DashboardContext";
import GlobalMetrics from "../components/GlobalMetrics";
import type { ToastMessage } from "../context/DashboardContext";

type NavItem = {
  to: string;
  label: string;
  icon: JSX.Element;
  isEnabled: boolean;
};

const toastIcons: Record<ToastMessage["variant"], JSX.Element> = {
  success: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20Zm4.24 7.53-5.3 5.34-2.18-2.19a1 1 0 0 0-1.41 1.42l2.88 2.87a1 1 0 0 0 1.41 0l6-6a1 1 0 1 0-1.41-1.41Z"
      />
    </svg>
  ),
  error: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20Zm3.54 5.46a1 1 0 0 0-1.41 0L12 9.59l-2.12-2.13a1 1 0 0 0-1.41 1.42L10.59 11l-2.12 2.12a1 1 0 1 0 1.41 1.41L12 12.41l2.12 2.12a1 1 0 0 0 1.41-1.41L13.41 11l2.12-2.12a1 1 0 0 0 0-1.42Z"
      />
    </svg>
  ),
  info: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20Zm0 4a1.25 1.25 0 1 0 0 2.5A1.25 1.25 0 0 0 12 6Zm1.25 4h-2.5a1 1 0 0 0 0 2h.75v5h-1a1 1 0 0 0 0 2h3a1 1 0 0 0 0-2h-1v-6a1 1 0 0 0-1-1Z"
      />
    </svg>
  ),
};

function DashboardLayout() {
  const {
    enableAnalyticsAdv,
    enablePurchasesSales,
    enableTransfers,
    currentUser,
    message,
    error,
    setMessage,
    setError,
    toasts,
    dismissToast,
    networkAlert,
    dismissNetworkAlert,
  } = useDashboard();
  const location = useLocation();

  const isAdmin = currentUser?.roles.some((role) => role.name === "ADMIN") ?? false;

  const navItems: NavItem[] = useMemo(
    () => [
      {
        to: "/dashboard/inventory",
        label: "Inventario",
        icon: <Boxes className="icon" aria-hidden="true" />,
        isEnabled: true,
      },
      {
        to: "/dashboard/operations",
        label: "Operaciones",
        icon: <Cog className="icon" aria-hidden="true" />,
        isEnabled: enablePurchasesSales || enableTransfers,
      },
      {
        to: "/dashboard/analytics",
        label: "Analítica",
        icon: <BarChart3 className="icon" aria-hidden="true" />,
        isEnabled: enableAnalyticsAdv,
      },
      {
        to: "/dashboard/security",
        label: "Seguridad",
        icon: <ShieldCheck className="icon" aria-hidden="true" />,
        isEnabled: true,
      },
      {
        to: "/dashboard/sync",
        label: "Sincronización",
        icon: <Repeat className="icon" aria-hidden="true" />,
        isEnabled: true,
      },
      {
        to: "/dashboard/users",
        label: "Usuarios",
        icon: <UserCog className="icon" aria-hidden="true" />,
        isEnabled: isAdmin,
      },
      {
        to: "/dashboard/repairs",
        label: "Reparaciones",
        icon: <Wrench className="icon" aria-hidden="true" />,
        isEnabled: enablePurchasesSales,
      },
    ],
    [enableAnalyticsAdv, enablePurchasesSales, enableTransfers, isAdmin]
  );

  const availableNavItems = navItems.filter((item) => item.isEnabled);

  return (
    <div className="dashboard">
      <div className="toast-container" aria-live="assertive" aria-atomic="true">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              className={`toast ${toast.variant}`}
              role="status"
              initial={{ opacity: 0, x: 32, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 32, scale: 0.95 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
              layout
            >
              <span className="toast-icon" aria-hidden="true">
                {toastIcons[toast.variant]}
              </span>
              <span className="toast-message">{toast.message}</span>
              <button
                className="toast-dismiss"
                type="button"
                onClick={() => dismissToast(toast.id)}
                aria-label="Cerrar notificación"
              >
                ×
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {networkAlert ? (
          <motion.div
            key="network-alert"
            className="alert warning network-alert"
            role="alert"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
          >
            <span aria-hidden="true">⚠️</span>
            <span>{networkAlert}</span>
            <button
              className="alert-dismiss"
              type="button"
              onClick={dismissNetworkAlert}
              aria-label="Descartar alerta de red"
            >
              ×
            </button>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <header className="dashboard-header">
        <h1>Softmobile 2025 · Centro de control</h1>
        <p className="muted-text">Gestiona inventario, operaciones y seguridad desde áreas especializadas.</p>
      </header>

      <GlobalMetrics />

      <nav className="dashboard-nav" aria-label="Secciones del panel">
        {availableNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `dashboard-nav-item${isActive ? " active" : ""}`}
          >
            <span className="dashboard-nav-icon" aria-hidden="true">
              {item.icon}
            </span>
            <span className="dashboard-nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <AnimatePresence>
        {message ? (
          <motion.div
            key="dashboard-message"
            className="alert success"
            role="status"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25 }}
          >
            <div>{message}</div>
            <button className="alert-dismiss" type="button" onClick={() => setMessage(null)} aria-label="Cerrar aviso">
              ×
            </button>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <AnimatePresence>
        {error ? (
          <motion.div
            key="dashboard-error"
            className="alert error"
            role="alert"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25 }}
          >
            <div>{error}</div>
            <button className="alert-dismiss" type="button" onClick={() => setError(null)} aria-label="Cerrar error">
              ×
            </button>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        <motion.section
          key={location.pathname}
          className="dashboard-section"
          aria-live="polite"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
        >
          <Outlet />
        </motion.section>
      </AnimatePresence>
    </div>
  );
}

export default DashboardLayout;
