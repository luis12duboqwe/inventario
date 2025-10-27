import { Suspense, lazy, memo, useMemo, useState, useCallback, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Navigate, createBrowserRouter, useLocation, useRoutes } from "react-router-dom";
import Button from "../shared/components/ui/Button";
import {
  bootstrapAdmin,
  getBootstrapStatus,
  type BootstrapStatus,
  type Credentials,
} from "../services/api/auth";
import type { BootstrapFormValues } from "../shared/components/BootstrapForm";

const Dashboard = lazy(() => import("../shared/components/Dashboard"));
const WelcomeHero = lazy(() => import("../shared/components/WelcomeHero"));
const LoginForm = lazy(() => import("../shared/components/LoginForm"));
const BootstrapForm = lazy(() => import("../shared/components/BootstrapForm"));

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

export const RouterLoader = memo(function RouterLoader() {
  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>Cargando aplicación…</span>
    </div>
  );
});

const RouterFallback = memo(function RouterFallback() {
  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>Cargando panel principal…</span>
    </div>
  );
});

const ModuleFallback = memo(function ModuleFallback() {
  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>Cargando módulo…</span>
    </div>
  );
});

const AuthFallback = memo(function AuthFallback() {
  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>Preparando acceso seguro…</span>
    </div>
  );
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
          ),
        },
        {
          path: "*",
          element: <Navigate to="/login" replace />,
        },
      ];
    }

    return [
      {
        path: "/dashboard/*",
        element: (
          <DashboardScene
            token={token}
            theme={theme}
            onToggleTheme={onToggleTheme}
            onLogout={onLogout}
          />
        ),
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
  const [activeTab, setActiveTab] = useState<"login" | "bootstrap">("login");

  const {
    data: bootstrapStatus,
    error: bootstrapStatusError,
    refetch: refetchBootstrapStatus,
  } = useQuery<BootstrapStatus>({
    queryKey: ["auth", "bootstrap-status"],
    queryFn: getBootstrapStatus,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    const disponible = bootstrapStatus?.disponible;
    if (disponible === true) {
      setActiveTab("bootstrap");
    } else if (disponible === false) {
      setActiveTab("login");
    }
  }, [bootstrapStatus?.disponible]);

  useEffect(() => {
    if (activeTab !== "bootstrap") {
      setBootstrapSuccess(null);
    }
  }, [activeTab]);

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
    setActiveTab("login");
  }, []);

  const handleShowBootstrap = useCallback(() => {
    if (!canDisplayBootstrap) {
      return;
    }
    setActiveTab("bootstrap");
  }, [canDisplayBootstrap]);

  const handleBootstrapSubmit = useCallback(
    async (values: BootstrapFormValues) => {
      setBootstrapSuccess(null);
      try {
        await bootstrapMutation.mutateAsync(values);
        setBootstrapSuccess("Cuenta creada correctamente. Iniciando sesión…");
        await refetchBootstrapStatus();
        await onLogin({ username: values.username, password: values.password });
      } catch (submitError) {
        // eslint-disable-next-line no-console
        console.warn("No fue posible completar el registro inicial", submitError);
      }
    },
    [bootstrapMutation, onLogin, refetchBootstrapStatus],
  );

  const description =
    activeTab === "bootstrap"
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
          <h2 className="accent-title">{activeTab === "bootstrap" ? "Registro inicial" : "Ingreso seguro"}</h2>
          {canDisplayBootstrap ? (
            <div className="login-card__switcher" role="tablist" aria-label="Modos de acceso">
              <Button
                type="button"
                variant={activeTab === "login" ? "primary" : "ghost"}
                size="sm"
                onClick={handleShowLogin}
                aria-pressed={activeTab === "login"}
              >
                Iniciar sesión
              </Button>
              <Button
                type="button"
                variant={activeTab === "bootstrap" ? "secondary" : "ghost"}
                size="sm"
                onClick={handleShowBootstrap}
                aria-pressed={activeTab === "bootstrap"}
                disabled={!allowBootstrap && bootstrapStatus?.disponible === false}
              >
                Crear cuenta inicial
              </Button>
            </div>
          ) : null}
        </div>
        <p className="login-card__description">{description}</p>
        {statusErrorMessage ? <div className="alert warning">{statusErrorMessage}</div> : null}
        {activeTab === "bootstrap" && canDisplayBootstrap ? (
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
    },
  ]);
}
