import { useEffect, useMemo, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  BarChart3,
  BellRing,
  Boxes,
  Cog,
  Menu,
  HelpCircle,
  LogOut,
  Repeat,
  Search,
  ShieldCheck,
  SunMoon,
  UserCog,
  Wrench,
} from "lucide-react";

import BackToTopButton from "../../../components/BackToTopButton";
import CompactModeToggle from "../../../components/CompactModeToggle";
import GlobalMetrics from "../components/GlobalMetrics";
import Sidebar, { type SidebarNavItem } from "../components/Sidebar";
import { useDashboard } from "../context/DashboardContext";
import type { ToastMessage } from "../context/DashboardContext";
import Button from "../../../components/ui/Button";
import PageHeader from "../../../components/ui/PageHeader";
import AdminControlPanel from "../components/AdminControlPanel";
import ActionIndicatorBar from "../components/ActionIndicatorBar";

type NavItem = SidebarNavItem & {
  description: string;
  isEnabled: boolean;
};

type Props = {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  onLogout: () => void;
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

function DashboardLayout({ theme, onToggleTheme, onLogout }: Props) {
  const {
    enableAnalyticsAdv,
    enablePurchasesSales,
    enableTransfers,
    currentUser,
    message,
    error,
    setMessage,
    setError,
    pushToast,
    toasts,
    dismissToast,
    networkAlert,
    dismissNetworkAlert,
    globalSearchTerm,
    setGlobalSearchTerm,
    compactMode,
    loading,
    syncStatus,
    lastInventoryRefresh,
    outboxError,
  } = useDashboard();
  const location = useLocation();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("softmobile_last_module", location.pathname);
    }
    setIsSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!isSidebarOpen) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isSidebarOpen]);

  const toggleSidebar = () => {
    setIsSidebarOpen((current) => !current);
  };

  const closeSidebar = () => {
    setIsSidebarOpen(false);
  };

  const isAdmin = currentUser?.roles.some((role) => role.name === "ADMIN") ?? false;
  const isManager = currentUser?.roles.some((role) => role.name === "GERENTE") ?? false;
  const isOperator = currentUser?.roles.some((role) => role.name === "OPERADOR") ?? false;

  const roleVisual = useMemo(() => {
    if (isAdmin) {
      return {
        label: "Perfil administrador",
        description: "Acceso completo a módulos críticos, auditoría y control global.",
        className: "role-admin",
        variant: "admin" as const,
      };
    }
    if (isManager) {
      return {
        label: "Perfil gerente",
        description: "Monitoreo operativo y analítico con capacidades aprobatorias.",
        className: "role-manager",
        variant: "manager" as const,
      };
    }
    if (isOperator) {
      return {
        label: "Perfil operador",
        description: "Acceso guiado para registrar ventas, transferencias y seguimiento.",
        className: "role-operator",
        variant: "operator" as const,
      };
    }
    return {
      label: "Perfil invitado",
      description: "Acceso restringido. Solicita permisos para operar módulos críticos.",
      className: "role-guest",
      variant: "guest" as const,
    };
  }, [isAdmin, isManager, isOperator]);

  const navItems: NavItem[] = useMemo(
    () => [
      {
        to: "/dashboard/inventory",
        label: "Inventario",
        description: "Inventario corporativo, auditorías y respaldos en vivo.",
        icon: <Boxes className="icon" aria-hidden="true" />,
        isEnabled: true,
      },
      {
        to: "/dashboard/operations",
        label: "Operaciones",
        description: "Compras, ventas, devoluciones y transferencias sincronizadas.",
        icon: <Cog className="icon" aria-hidden="true" />,
        isEnabled: enablePurchasesSales || enableTransfers,
      },
      {
        to: "/dashboard/analytics",
        label: "Analítica",
        description: "Indicadores avanzados de rotación, aging y proyecciones.",
        icon: <BarChart3 className="icon" aria-hidden="true" />,
        isEnabled: enableAnalyticsAdv,
      },
      {
        to: "/dashboard/reports",
        label: "Reportes",
        description: "Alertas críticas, bitácora global y exportaciones corporativas.",
        icon: <BellRing className="icon" aria-hidden="true" />,
        isEnabled: true,
      },
      {
        to: "/dashboard/security",
        label: "Seguridad",
        description: "Autenticación, auditoría y políticas de acceso corporativo.",
        icon: <ShieldCheck className="icon" aria-hidden="true" />,
        isEnabled: true,
      },
      {
        to: "/dashboard/sync",
        label: "Sincronización",
        description: "Cola híbrida, historial y reintentos locales supervisados.",
        icon: <Repeat className="icon" aria-hidden="true" />,
        isEnabled: true,
      },
      {
        to: "/dashboard/users",
        label: "Usuarios",
        description: "Gestión de roles, sesiones activas y ajustes sensibles.",
        icon: <UserCog className="icon" aria-hidden="true" />,
        isEnabled: isAdmin,
      },
      {
        to: "/dashboard/repairs",
        label: "Reparaciones",
        description: "Órdenes, repuestos y control de costos vinculados al inventario.",
        icon: <Wrench className="icon" aria-hidden="true" />,
        isEnabled: enablePurchasesSales,
      },
    ],
    [enableAnalyticsAdv, enablePurchasesSales, enableTransfers, isAdmin],
  );

  const availableNavItems = navItems.filter((item) => item.isEnabled);
  const sidebarItems: SidebarNavItem[] = availableNavItems.map(({ to, label, icon }) => ({
    to,
    label,
    icon,
  }));

  const activeNav =
    availableNavItems.find((item) => location.pathname.startsWith(item.to)) ?? availableNavItems[0];
  const moduleTitle = activeNav?.label ?? "Centro de control";
  const moduleDescription =
    activeNav?.description ?? "Supervisa Softmobile 2025 v2.2.0 y mantén la operación sin interrupciones.";

  const handleQuickHelp = () => {
    setMessage("Consulta docs/logs/softmobile_v2.2_mejoras_ui_navegacion.md para la guía de navegación actualizada.");
    pushToast({
      message: "Guía rápida disponible en docs/logs/softmobile_v2.2_mejoras_ui_navegacion.md",
      variant: "info",
    });
  };

  const notificationCount =
    toasts.length + (message ? 1 : 0) + (error ? 1 : 0) + (networkAlert ? 1 : 0) + (syncStatus ? 1 : 0);
  const notificationSummary =
    notificationCount === 0
      ? "No hay notificaciones activas en este momento."
      : notificationCount === 1
        ? "Tienes 1 notificación activa en el panel."
        : `Tienes ${notificationCount} notificaciones activas en el panel.`;

  return (
    <div
      className={`dashboard-shell${compactMode ? " compact-mode" : ""} ${roleVisual.className}`}
      data-role-variant={roleVisual.variant}
    >
      <Sidebar
        items={sidebarItems}
        currentPath={location.pathname}
        mobileOpen={isSidebarOpen}
        onNavigate={closeSidebar}
      />
      <AnimatePresence>
        {isSidebarOpen ? (
          <motion.button
            key="sidebar-backdrop"
            type="button"
            className="dashboard-sidebar-backdrop"
            onClick={closeSidebar}
            aria-label="Cerrar menú lateral"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          />
        ) : null}
      </AnimatePresence>
      <div className="dashboard-main">
        <div className="dashboard-role-banner" role="complementary" aria-live="polite">
          <span className="dashboard-role-badge">{roleVisual.label}</span>
          <p>{roleVisual.description}</p>
        </div>
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
          <span className="sr-only" aria-live="polite">{notificationSummary}</span>
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

        <PageHeader
          title={moduleTitle}
          description={moduleDescription}
          actions={
            <div className="page-header__actions-row">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="page-header__action--menu"
                onClick={toggleSidebar}
                aria-expanded={isSidebarOpen}
                aria-controls="dashboard-navigation"
                leadingIcon={<Menu size={16} aria-hidden="true" />}
              >
                {isSidebarOpen ? "Cerrar menú" : "Menú"}
              </Button>
              <label className="app-search" aria-label="Buscador global">
                <Search size={16} aria-hidden="true" />
                <input
                  type="search"
                  value={globalSearchTerm}
                  onChange={(event) => setGlobalSearchTerm(event.target.value)}
                  placeholder="Buscar en Softmobile"
                />
              </label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleQuickHelp}
                leadingIcon={<HelpCircle size={16} aria-hidden="true" />}
              >
                Ayuda rápida
              </Button>
              <CompactModeToggle />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onToggleTheme}
                aria-pressed={theme === "light"}
                leadingIcon={<SunMoon size={16} aria-hidden="true" />}
              >
                Tema {theme === "dark" ? "oscuro" : "claro"}
              </Button>
              <Button
                type="button"
                variant="danger"
                size="sm"
                onClick={onLogout}
                leadingIcon={<LogOut size={16} aria-hidden="true" />}
              >
                Cerrar sesión
              </Button>
            </div>
          }
        />

        <ActionIndicatorBar
          loading={loading}
          hasSuccessMessage={Boolean(message)}
          hasError={Boolean(error || outboxError)}
          errorMessage={error ?? outboxError}
          syncStatus={syncStatus}
          networkAlert={networkAlert}
          lastInventoryRefresh={lastInventoryRefresh}
        />

        <main className="dashboard-content">
          <AdminControlPanel
            modules={availableNavItems.map((item) => ({
              to: item.to,
              label: item.label,
              description: item.description,
              icon: item.icon,
              badge: item.label === moduleTitle ? "Abierto" : undefined,
            }))}
            roleVariant={roleVisual.variant}
            notifications={notificationCount}
          />

          <GlobalMetrics />

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
                <button
                  className="alert-dismiss"
                  type="button"
                  onClick={() => setMessage(null)}
                  aria-label="Cerrar aviso"
                >
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
                <button
                  className="alert-dismiss"
                  type="button"
                  onClick={() => setError(null)}
                  aria-label="Cerrar error"
                >
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
        </main>

        <BackToTopButton />
      </div>
    </div>
  );
}

export default DashboardLayout;
