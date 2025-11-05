import React, { Suspense, memo, useMemo, useState, useCallback } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Navigate, createBrowserRouter, useLocation, useRoutes } from "react-router-dom";
// [PACK20-SALES-ROUTES-START]
import { SalesRoutes } from "../modules/sales";
// [PACK20-SALES-ROUTES-END]
export { SalesRoutes as __Pack20SalesRoutesKeep };
// [PACK29-*] Ruta dedicada a reportes operativos
import { ReportsRoutes } from "../modules/reports";
export { ReportsRoutes as __Pack29ReportsRoutesKeep };
import Loader from "../shared/components/Loader";
import Button from "../shared/components/ui/Button";
import AppErrorBoundary from "../shared/components/AppErrorBoundary"; // [PACK36-router]
// [PACK28-router-guards]
import RequireAuth from "./guards/RequireAuth";
// [PACK28-router-guards]
import RequireRole from "./guards/RequireRole";
import RouteErrorElement from "./RouteErrorElement"; // [PACK36-router]
import {
  bootstrapAdmin,
  getBootstrapStatus,
  type BootstrapStatus,
  type Credentials,
} from "../services/api/auth";
import type { BootstrapFormValues } from "../shared/components/BootstrapForm";

const Dashboard = React.lazy(() => import("../shared/components/Dashboard"));
const WelcomeHero = React.lazy(() => import("../shared/components/WelcomeHero"));
const LoginForm = React.lazy(() => import("../shared/components/LoginForm"));
const BootstrapForm = React.lazy(() => import("../shared/components/BootstrapForm"));

export type ThemeMode = "dark" | "light";

export type AppRouterProps = {
  token: string | null;
  loading: boolean;
  error: string | null;
  theme: ThemeMode;
  themeLabel: string;
  onToggleTheme: () => void;
  onLogin: (credentials: Credentials) => Promise<void>;
  onLogout: () => void;
};

const RouterFallback = memo(function RouterFallback() {
  return <Loader message="Cargando panel principal…" />;
});

const ModuleFallback = memo(function ModuleFallback() {
  return <Loader message="Cargando módulo…" />;
});

const AuthFallback = memo(function AuthFallback() {
  return <Loader message="Preparando acceso seguro…" />;
});

const AppRouter = memo(function AppRouter({
  token,
  loading,
  error,
  theme,
  themeLabel,
  onToggleTheme,
  onLogin,
  onLogout,
}: AppRouterProps) {
  const location = useLocation();

  const routes = useMemo(() => {
    if (!token) {
      return [
        {
          path: "/login",
          element: (
            <AppErrorBoundary
              // [PACK36-router]
              variant="inline"
              title="Inicio de sesión no disponible"
              description="Reintenta ingresar; si el problema persiste contacta a soporte."
            >
              <Suspense fallback={<AuthFallback />}>
                <LoginScene
                  theme={theme}
                  themeLabel={themeLabel}
                  onToggleTheme={onToggleTheme}
                  loading={loading}
                  error={error}
                  onLogin={onLogin}
                />
              </Suspense>
            </AppErrorBoundary>
          ),
          errorElement: <RouteErrorElement scope="/login" />,
        },
        {
          path: "*",
          element: <Navigate to="/login" replace />,
        },
      ];
    }

    return [
      {
        path: "/login",
        element: <Navigate to="/dashboard/inventory" replace />,
      },
      {
        path: "/dashboard/*",
        element: (
          <RequireAuth>
            <AppErrorBoundary
              // [PACK36-router]
              variant="inline"
              title="Panel principal con inconvenientes"
              description="Intentaremos recuperar la vista. Si el error continúa, actualiza la página."
            >
              <DashboardScene
                token={token}
                theme={theme}
                onToggleTheme={onToggleTheme}
                onLogout={onLogout}
              />
            </AppErrorBoundary>
          </RequireAuth>
        ),
        errorElement: <RouteErrorElement scope="/dashboard" />,
      },
      // [PACK20-SALES-MOUNT-START]
      {
        path: "/sales/*",
        element: (
          <RequireAuth>
            <RequireRole roles={["ADMIN", "GERENTE"]}>
              <AppErrorBoundary
                // [PACK36-router]
                variant="inline"
                title="Ventas no disponibles"
                description="Revisa la conexión y vuelve a intentar abrir el módulo de ventas."
              >
                <DashboardScene
                  token={token}
                  theme={theme}
                  onToggleTheme={onToggleTheme}
                  onLogout={onLogout}
                />
              </AppErrorBoundary>
            </RequireRole>
          </RequireAuth>
        ),
        errorElement: <RouteErrorElement scope="/sales" />,
      },
      // [PACK20-SALES-MOUNT-END]
      // [PACK29-*] Montaje de la ruta de reportes de ventas
      {
        path: "/reports/*",
        element: (
          <AppErrorBoundary
            // [PACK36-router]
            variant="inline"
            title="Reportes en mantenimiento"
            description="Intenta refrescar la vista; si se mantiene, contacta a soporte corporativo."
          >
            <DashboardScene
              token={token}
              theme={theme}
              onToggleTheme={onToggleTheme}
              onLogout={onLogout}
            />
          </AppErrorBoundary>
        ),
        errorElement: <RouteErrorElement scope="/reports" />,
      },
      {
        path: "*",
        element: <Navigate to="/dashboard/inventory" replace />,
      },
    ];
  }, [error, loading, onLogin, onLogout, onToggleTheme, theme, themeLabel, token]);

  const element = useRoutes(routes);

  return (
    <Suspense fallback={<RouterFallback />}>
      <AnimatePresence mode="wait">
        <motion.div key={location.pathname} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          {element}
        </motion.div>
      </AnimatePresence>
    </Suspense>
  );
});

AppRouter.displayName = "AppRouter";

export default AppRouter;

const LoginScene = memo(function LoginScene({
  theme,
  themeLabel,
  onToggleTheme,
  loading,
  error,
  onLogin,
}: {
  theme: ThemeMode;
  themeLabel: string;
  onToggleTheme: () => void;
  loading: boolean;
  error: string | null;
  onLogin: (credentials: Credentials) => Promise<void>;
}) {
  const [bootstrapSuccess, setBootstrapSuccess] = useState<string | null>(null);
  // El tab efectivo sigue la sugerencia del servidor salvo que el usuario elija manualmente
  const [userSelectedTab, setUserSelectedTab] = useState<"login" | "bootstrap" | null>(null);

  const {
    data: bootstrapStatus,
    error: bootstrapStatusError,
    refetch: refetchBootstrapStatus,
  } = useQuery<BootstrapStatus>({
    queryKey: ["auth", "bootstrap-status"],
    queryFn: getBootstrapStatus,
    staleTime: 5 * 60 * 1000,
  });

  // Determina el tab efectivo: servidor sugiere y el usuario puede anular manualmente
  const effectiveTab: "login" | "bootstrap" =
    userSelectedTab ?? (bootstrapStatus?.disponible === true ? "bootstrap" : "login");

  const bootstrapMutation = useMutation({
    mutationFn: async (values: BootstrapFormValues) => {
      await bootstrapAdmin({
        username: values.username,
        password: values.password,
        full_name: values.fullName,
        telefono: values.telefono,
      });
    },
  });

  const canDisplayBootstrap = bootstrapStatus?.disponible !== false;
  const allowBootstrap = bootstrapStatus?.disponible === true;
  const bootstrapLoading = bootstrapMutation.isPending;

  const statusErrorMessage = bootstrapStatusError
    ? bootstrapStatusError instanceof Error
      ? bootstrapStatusError.message
      : "No fue posible verificar el estado del registro inicial."
    : null;

  const bootstrapErrorMessage = bootstrapMutation.error
    ? bootstrapMutation.error instanceof Error
      ? bootstrapMutation.error.message
      : "No fue posible registrar la cuenta inicial."
    : null;

  const handleShowLogin = useCallback(() => {
    setBootstrapSuccess(null);
    setUserSelectedTab("login");
  }, []);

  const handleShowBootstrap = useCallback(() => {
    if (!canDisplayBootstrap) {
      return;
    }
    setBootstrapSuccess(null);
    setUserSelectedTab("bootstrap");
  }, [canDisplayBootstrap]);

  const handleBootstrapSubmit = useCallback(
    async (values: BootstrapFormValues) => {
      setBootstrapSuccess(null);
      try {
        await bootstrapMutation.mutateAsync(values);
        setBootstrapSuccess("Cuenta creada correctamente. Iniciando sesión…");
        await refetchBootstrapStatus();
        await onLogin({ username: values.username, password: values.password });
      } catch {
        setBootstrapSuccess(null);
      }
    },
    [bootstrapMutation, onLogin, refetchBootstrapStatus],
  );

  const description =
    effectiveTab === "bootstrap"
      ? "Registra la primera cuenta administradora para comenzar a usar Softmobile."
      : "Ingresa con tus credenciales corporativas para continuar.";

  return (
    <motion.main
      key="login"
      className="login-wrapper"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      <WelcomeHero themeLabel={themeLabel} onToggleTheme={onToggleTheme} activeTheme={theme} />
      <motion.section
        className="card login-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5, ease: "easeOut" }}
      >
        <div className="login-card__header">
          <h2 className="accent-title">{effectiveTab === "bootstrap" ? "Registro inicial" : "Ingreso seguro"}</h2>
          {canDisplayBootstrap ? (
            <div className="login-card__switcher" role="tablist" aria-label="Modos de acceso">
              <Button
                type="button"
                variant={effectiveTab === "login" ? "primary" : "ghost"}
                size="sm"
                onClick={handleShowLogin}
                aria-pressed={effectiveTab === "login"}
              >
                Iniciar sesión
              </Button>
              <Button
                type="button"
                variant={effectiveTab === "bootstrap" ? "secondary" : "ghost"}
                size="sm"
                onClick={handleShowBootstrap}
                aria-pressed={effectiveTab === "bootstrap"}
                disabled={!allowBootstrap && bootstrapStatus?.disponible === false}
              >
                Crear cuenta inicial
              </Button>
            </div>
          ) : null}
        </div>
        <p className="login-card__description">{description}</p>
        {statusErrorMessage ? <div className="alert warning">{statusErrorMessage}</div> : null}
        {effectiveTab === "bootstrap" && canDisplayBootstrap ? (
          <BootstrapForm
            loading={bootstrapLoading || loading}
            error={bootstrapErrorMessage}
            successMessage={bootstrapSuccess}
            onSubmit={handleBootstrapSubmit}
          />
        ) : (
          <LoginForm loading={loading} error={error} onSubmit={onLogin} />
        )}
        {allowBootstrap ? (
          <p className="login-card__hint" role="note">
            La primera cuenta creada tendrá privilegios de administración completa.
          </p>
        ) : null}
      </motion.section>
    </motion.main>
  );
});

LoginScene.displayName = "LoginScene";

const DashboardScene = memo(function DashboardScene({
  token,
  theme,
  onToggleTheme,
  onLogout,
}: {
  token: string;
  theme: ThemeMode;
  onToggleTheme: () => void;
  onLogout: () => void;
}) {
  return (
    <motion.div
      key="dashboard"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      <motion.div
        className="dashboard-shell-wrapper"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      >
        <Suspense fallback={<ModuleFallback />}>
          <Dashboard token={token} theme={theme} onToggleTheme={onToggleTheme} onLogout={onLogout} />
        </Suspense>
      </motion.div>
    </motion.div>
  );
});

DashboardScene.displayName = "DashboardScene";

export function createAppRouter(props: AppRouterProps) {
  return createBrowserRouter([
    {
      path: "*",
      element: <AppRouter {...props} />,
      errorElement: <RouteErrorElement scope="router" />, // [PACK36-router]
    },
  ]);
}
