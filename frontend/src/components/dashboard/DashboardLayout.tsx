import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useDashboard } from "./DashboardContext";
import InventorySection from "./InventorySection";
import OperationsSection from "./OperationsSection";
import AnalyticsSection from "./AnalyticsSection";
import SecuritySection from "./SecuritySection";
import SyncSection from "./SyncSection";
import GlobalMetrics from "./GlobalMetrics";
import UserManagement from "../UserManagement";
import type { ToastMessage } from "./DashboardContext";

type SectionKey = "inventory" | "operations" | "analytics" | "security" | "sync" | "users";

type SectionDefinition = {
  key: SectionKey;
  label: string;
  isEnabled: boolean;
  element: JSX.Element;
};

const DEFAULT_SECTION: SectionKey = "inventory";

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

const sectionIcons: Record<SectionKey, JSX.Element> = {
  inventory: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M4 4h16a2 2 0 0 1 2 2v3h-2V6H4v12h7v2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm15 8h-5v-2h5l-3-3 1.4-1.4L22.8 11l-.1.1-4.5 4.5L16.8 14 19 12Z"
      />
    </svg>
  ),
  operations: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M4 3h16a1 1 0 0 1 1 1v6h-2V5H5v14h6v2H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm8 6h9a1 1 0 0 1 0 2h-9a1 1 0 0 1 0-2Zm0 4h9a1 1 0 0 1 0 2h-9a1 1 0 0 1 0-2Zm0 4h6a1 1 0 0 1 0 2h-6a1 1 0 1 1 0-2Z"
      />
    </svg>
  ),
  analytics: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M5 3a2 2 0 0 0-2 2v13h-.5a1 1 0 0 0 0 2h19a1 1 0 0 0 0-2H21V5a2 2 0 0 0-2-2H5Zm12 15H7v-6h10v6Zm2-6v6h-1v-6h1ZM7 10V5h10v5H7Zm-2 9v-9h1v9H5Z"
      />
    </svg>
  ),
  security: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M12 2 4 5v6c0 5.52 3.58 10.74 8 11 4.42-.26 8-5.48 8-11V5l-8-3Zm0 4.18L17 7.6v3.4c0 4.14-2.56 8.26-5 8.5-2.44-.24-5-4.36-5-8.5V7.6l5-1.42ZM12 9a2 2 0 0 0-2 2v2a2 2 0 1 0 4 0v-2a2 2 0 0 0-2-2Z"
      />
    </svg>
  ),
  sync: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M12 4a8 8 0 0 1 6.32 12.9l2.06 2.06a1 1 0 0 1-1.42 1.42l-2.12-2.12A8 8 0 0 1 4 12H2l2.93-2.93L7.86 12H6a6 6 0 1 0 1.76-4.24 1 1 0 0 1-1.41-1.42A8 8 0 0 1 12 4Z"
      />
    </svg>
  ),
  users: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5Zm0 2c-4 0-7 2-7 5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1c0-3-3-5-7-5Zm0-7a3 3 0 1 1 3-3 3 3 0 0 1-3 3Zm-5.9 10c.5-1.5 2.53-3 5.9-3s5.4 1.5 5.9 3Z"
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
  } = useDashboard();
  const [active, setActive] = useState<SectionKey>(DEFAULT_SECTION);

  const isAdmin = currentUser?.roles.some((role) => role.name === "ADMIN") ?? false;

  const sections: SectionDefinition[] = useMemo(
    () => [
      { key: "inventory", label: "Inventario", isEnabled: true, element: <InventorySection /> },
      {
        key: "operations",
        label: "Operaciones",
        isEnabled: enablePurchasesSales || enableTransfers,
        element: <OperationsSection />,
      },
      {
        key: "analytics",
        label: "Analítica",
        isEnabled: enableAnalyticsAdv,
        element: <AnalyticsSection />,
      },
      { key: "security", label: "Seguridad", isEnabled: true, element: <SecuritySection /> },
      { key: "sync", label: "Sincronización", isEnabled: true, element: <SyncSection /> },
      { key: "users", label: "Usuarios", isEnabled: isAdmin, element: <UserManagement /> },
    ],
    [enableAnalyticsAdv, enablePurchasesSales, enableTransfers, isAdmin]
  );

  const availableSections = sections.filter((section) => section.isEnabled);

  useEffect(() => {
    if (!availableSections.some((section) => section.key === active) && availableSections.length > 0) {
      setActive(availableSections[0].key);
    }
  }, [active, availableSections]);

  const activeSection =
    availableSections.find((section) => section.key === active) ?? availableSections[0] ?? sections[0];

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
      <header className="dashboard-header">
        <h1>Softmobile 2025 · Centro de control</h1>
        <p className="muted-text">
          Gestiona inventario, operaciones y seguridad desde áreas especializadas.
        </p>
      </header>
      <GlobalMetrics />
      <nav className="dashboard-nav" aria-label="Secciones del panel">
        {availableSections.map((section) => (
          <button
            key={section.key}
            className={`dashboard-nav-item${section.key === active ? " active" : ""}`}
            type="button"
            onClick={() => setActive(section.key)}
          >
            <span className="dashboard-nav-icon" aria-hidden="true">
              {sectionIcons[section.key]}
            </span>
            <span className="dashboard-nav-label">{section.label}</span>
          </button>
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
        {activeSection ? (
          <motion.section
            key={activeSection.key}
            className="dashboard-section"
            aria-live="polite"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
          >
            {activeSection.element}
          </motion.section>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

export default DashboardLayout;

