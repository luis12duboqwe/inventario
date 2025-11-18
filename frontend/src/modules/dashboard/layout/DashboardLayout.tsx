import { useEffect, useMemo, useState, isValidElement } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
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
  ShoppingBag,
  LifeBuoy,
  SunMoon,
  UserCog,
  Wrench,
  MapPin,
  Smartphone,
} from "lucide-react";

import BackToTopButton from "../../../shared/components/BackToTopButton";
import CompactModeToggle from "../../../shared/components/CompactModeToggle";
import GlobalMetrics from "../components/GlobalMetrics";
import StockAlertsWidget from "../components/StockAlertsWidget";
import TechMonitor from "../components/TechMonitor";
import Sidebar, { type SidebarNavItem } from "../components/Sidebar";
import { useDashboard } from "../context/DashboardContext";
import type { ToastMessage } from "../context/DashboardContext";
import { getRiskAlerts, type RiskAlert } from "../../../api";
import Button from "../../../shared/components/ui/Button";
import PageHeader from "../../../shared/components/ui/PageHeader";
import AdminControlPanel, {
  type AdminControlPanelModule,
} from "../components/AdminControlPanel";
import ActionIndicatorBar from "../components/ActionIndicatorBar";
import type { NotificationCenterItem } from "../components/NotificationCenter";

function formatRelativeTime(date: Date) {
  return new Intl.RelativeTimeFormat("es", { numeric: "auto" }).format(
    Math.round((date.getTime() - Date.now()) / 60000),
    "minute",
  );
}

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
  warning: (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M10.29 3.86 1.82 18.14A2 2 0 0 0 3.53 21h16.94a2 2 0 0 0 1.71-2.86L13.71 3.86a2 2 0 0 0-3.42 0ZM12 9a1 1 0 0 1 1 1v3.5a1 1 0 0 1-2 0V10a1 1 0 0 1 1-1Zm0 8a1.25 1.25 0 1 1 0-2.5A1.25 1.25 0 0 1 12 17Z"
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
    outboxConflicts,
    lastOutboxConflict,
    observability,
    observabilityError,
    refreshObservability,
    token,
  } = useDashboard();
  const location = useLocation();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [riskAlerts, setRiskAlerts] = useState<RiskAlert[]>([]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("softmobile_last_module", location.pathname);
    }
    // Deferimos el cierre al siguiente tick para evitar setState sincrónico dentro del efecto.
    if (!isSidebarOpen) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      setIsSidebarOpen(false);
    }, 0);
    return () => window.clearTimeout(timeoutId);
  }, [location.pathname, isSidebarOpen]);

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

  useEffect(() => {
    if (!token) {
      return;
    }
    getRiskAlerts(token)
      .then((response) => setRiskAlerts(response.alerts))
      .catch(() => setRiskAlerts([]));
  }, [token]);

  const toggleSidebar = () => {
    setIsSidebarOpen((current) => !current);
  };

  const closeSidebar = () => {
    setIsSidebarOpen(false);
  };

  const isAdmin = currentUser?.roles.some((role) => role.name === "ADMIN") ?? false;
  const isManager = currentUser?.roles.some((role) => role.name === "GERENTE") ?? false;
  const isOperator = currentUser?.roles.some((role) => role.name === "OPERADOR") ?? false;

  const observabilityNotifications = observability?.notifications ?? [];
  const techNotificationItems = useMemo<NotificationCenterItem[]>(() => {
    if (observabilityNotifications.length === 0) {
      return [];
    }
    return observabilityNotifications.map((notification) => {
      const severity = (notification.severity ?? "info").toLowerCase();
      const variant: NotificationCenterItem["variant"] =
        severity === "critical" || severity === "error"
          ? "error"
          : severity === "warning"
            ? "warning"
            : "info";
      const occurredLabel = notification.occurred_at
        ? new Date(notification.occurred_at).toLocaleString("es-MX", {
            dateStyle: "short",
            timeStyle: "short",
          })
        : null;
      const description = occurredLabel
        ? `${notification.message} · ${occurredLabel}`
        : notification.message;
      return {
        id: `tech-${notification.id}`,
        title: notification.title,
        description,
        variant,
      } satisfies NotificationCenterItem;
    });
  }, [observabilityNotifications]);

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
        to: "/dashboard/mobile",
        label: "Móvil",
        description: "Conteos, recepciones y consulta rápida en dispositivos móviles.",
        icon: <Smartphone className="icon" aria-hidden="true" />,
        isEnabled: true,
      },
      {
        to: "/sales",
        label: "Ventas",
        description: "POS, cotizaciones, devoluciones y clientes corporativos.",
        icon: <ShoppingBag className="icon" aria-hidden="true" />,
        isEnabled: enablePurchasesSales,
        children: [
          { to: "/sales", label: "Resumen" },
          { to: "/sales/pos", label: "POS" },
          { to: "/sales/quotes", label: "Cotizaciones" },
          { to: "/sales/returns", label: "Devoluciones" },
          { to: "/sales/customers", label: "Clientes" },
          { to: "/sales/cash-close", label: "Cierre de caja" },
        ],
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
        to: "/dashboard/help",
        label: "Ayuda",
        description: "Guías contextuales, manuales y modo demostración.",
        icon: <HelpCircle className="icon" aria-hidden="true" />,
        isEnabled: true,
      },
      {
        to: "/dashboard/support",
        label: "Soporte",
        description: "Feedback clasificado y métricas de priorización por uso.",
        icon: <LifeBuoy className="icon" aria-hidden="true" />,
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
        to: "/dashboard/stores",
        label: "Sucursales",
        description: "Alta y administración de sucursales corporativas.",
        icon: <MapPin className="icon" aria-hidden="true" />,
        isEnabled: isAdmin || isManager,
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
    [enableAnalyticsAdv, enablePurchasesSales, enableTransfers, isAdmin, isManager],
  );

  const availableNavItems = navItems.filter((item) => item.isEnabled);
  const sidebarItems: SidebarNavItem[] = availableNavItems.map(({ to, label, icon, children }) => {
    const base: SidebarNavItem = { to, label, icon };
    if (children && children.length > 0) {
      return { ...base, children };
    }
    return base;
  });

  const activeNav =
    availableNavItems.find((item) => location.pathname.startsWith(item.to)) ?? availableNavItems[0];
  const moduleTitle = activeNav?.label ?? "Centro de control";
  const moduleDescription =
    activeNav?.description ?? "Supervisa Softmobile 2025 v2.2.0 y mantén la operación sin interrupciones.";

  const handleQuickHelp = () => {
    navigate("/dashboard/help", { state: { from: location.pathname } });
  };

  const notificationCount =
    toasts.length +
    (message ? 1 : 0) +
    (error ? 1 : 0) +
    (networkAlert ? 1 : 0) +
    (syncStatus ? 1 : 0) +
    (outboxConflicts > 0 ? 1 : 0) +
    (observabilityError ? 1 : 0) +
    techNotificationItems.length +
    riskAlerts.length;
  const notificationSummary =
    notificationCount === 0
      ? "No hay notificaciones activas en este momento."
      : notificationCount === 1
        ? "Tienes 1 notificación activa en el panel."
        : `Tienes ${notificationCount} notificaciones activas en el panel.`;

  const panelNotificationItems = useMemo<NotificationCenterItem[]>(() => {
    const items: NotificationCenterItem[] = [];

    if (message) {
      items.push({
        id: "panel-message",
        title: "Operación completada",
        description: message,
        variant: "success",
      });
    }

    if (error) {
      items.push({
        id: "panel-error",
        title: "Error detectado",
        description: error,
        variant: "error",
      });
    }

    riskAlerts.forEach((alert) => {
      items.push({
        id: `risk-${alert.code}`,
        title: alert.title,
        description: alert.description,
        variant: alert.severity === "critica" || alert.severity === "alta" ? "error" : "warning",
      });
    });

    if (outboxError) {
      items.push({
        id: "panel-outbox-error",
        title: "Error de sincronización",
        description: outboxError,
        variant: "error",
      });
    }

    if (outboxConflicts > 0) {
      items.push({
        id: "panel-outbox-conflicts",
        title: "Conflictos en sync_outbox",
        description:
          lastOutboxConflict != null
            ? `Último conflicto: ${lastOutboxConflict.toLocaleString("es-MX")}`
            : "Se detectaron conflictos con prioridad last-write-wins.",
        variant: "warning",
      });
    }

    if (networkAlert) {
      items.push({
        id: "panel-network",
        title: "Alerta de red",
        description: networkAlert,
        variant: "warning",
      });
    }

    if (syncStatus) {
      const isSyncError = syncStatus.toLowerCase().includes("error");
      items.push({
        id: "panel-sync",
        title: isSyncError ? "Sincronización con incidencias" : "Estado de sincronización",
        description: syncStatus,
        variant: isSyncError ? "error" : "info",
      });
    } else if (lastInventoryRefresh) {
      items.push({
        id: "panel-sync-last",
        title: "Última sincronización de inventario",
        description: formatRelativeTime(lastInventoryRefresh),
        variant: "info",
      });
    }

    if (observabilityError) {
      items.push({
        id: "panel-observability-error",
        title: "Observabilidad sin respuesta",
        description: observabilityError,
        variant: "warning",
      });
    }

    techNotificationItems.forEach((item) => {
      items.push(item);
    });

    toasts.forEach((toast) => {
      items.push({
        id: `panel-toast-${toast.id}`,
        title:
          toast.variant === "success"
            ? "Notificación positiva"
            : toast.variant === "error"
              ? "Notificación de error"
              : "Notificación informativa",
        description: toast.message,
        variant: toast.variant,
      });
    });

    return items;
  }, [
    error,
    observabilityError,
    lastInventoryRefresh,
    message,
    networkAlert,
    outboxConflicts,
    lastOutboxConflict,
    techNotificationItems,
    outboxError,
    syncStatus,
    toasts,
  ]);

  const panelModules = useMemo<AdminControlPanelModule[]>(() => {
    return availableNavItems.map((item) => {
      const isActive = item.label === moduleTitle;
      const badges: string[] = [];
      let badgeVariant: AdminControlPanelModule["badgeVariant"] = "default";
      const srNotices: string[] = [];

      if (isActive) {
        badges.push("Abierto");
        srNotices.push("Módulo abierto actualmente.");
      }

      const syncNeedsAttention =
        item.label === "Sincronización" && (networkAlert || outboxError || (syncStatus ?? "").toLowerCase().includes("error"));
      const operationsNeedsAttention =
        item.label === "Operaciones" && Boolean(error || outboxError);
      const reportsHasMessage = item.label === "Reportes" && Boolean(message);

      if (syncNeedsAttention) {
        badgeVariant = networkAlert ? "warning" : "danger";
        badges.push(networkAlert ? "Revisar conexión" : "Sincronización pendiente");
        srNotices.push(
          networkAlert
            ? "Atención: revisar la conexión antes de continuar con este módulo."
            : "Atención: la sincronización presenta incidencias que requieren revisión.",
        );
      } else if (operationsNeedsAttention) {
        badgeVariant = "danger";
        badges.push("Revisar procesos");
        srNotices.push("Atención: operaciones con errores pendientes.");
      } else if (reportsHasMessage) {
        badgeVariant = "info";
        badges.push("Nuevo aviso");
        srNotices.push("Existe un aviso nuevo asociado a reportes.");
      }

      const module: AdminControlPanelModule = {
        to: item.to,
        label: item.label,
        description: item.description,
        icon: isValidElement(item.icon) ? item.icon : <HelpCircle className="icon" aria-hidden="true" />,
        badgeVariant,
        isActive,
      };

      const badgeText = badges.length > 0 ? badges.join(" · ") : null;
      if (badgeText) {
        module.badge = badgeText;
      }

      const srHint = srNotices.length > 0 ? srNotices.join(" ") : null;
      if (srHint) {
        module.srHint = srHint;
      }

      return module;
    });
  }, [
    availableNavItems,
    error,
    message,
    moduleTitle,
    networkAlert,
    outboxError,
    syncStatus,
  ]);

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

        <main className="dashboard-content" id="main-content">
          <AdminControlPanel
            modules={panelModules}
            roleVariant={roleVisual.variant}
            notifications={notificationCount}
            notificationItems={panelNotificationItems}
            riskAlerts={riskAlerts}
          />

          <TechMonitor />
          <GlobalMetrics />
          <StockAlertsWidget />

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
