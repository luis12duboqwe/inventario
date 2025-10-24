import { Suspense, lazy, memo, useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import LoginForm from "../shared/components/LoginForm";
import BootstrapForm, { type BootstrapFormValues } from "../shared/components/BootstrapForm";
import Button from "../shared/components/ui/Button";
import {
  bootstrapAdmin,
  getBootstrapStatus,
  login,
  logout,
  type BootstrapStatus,
  type Credentials,
  UNAUTHORIZED_EVENT,
} from "../services/api/auth";
import { getAuthToken } from "../services/api/http";
import WelcomeHero from "../shared/components/WelcomeHero";

const Dashboard = lazy(() => import("../shared/components/Dashboard"));

type ThemeMode = "dark" | "light";

function resolveInitialTheme(): ThemeMode {
  if (typeof window === "undefined") {
    return "dark";
  }
  const stored = window.localStorage.getItem("softmobile_theme");
  if (stored === "dark" || stored === "light") {
    return stored;
  }
  const prefersLight = window.matchMedia?.("(prefers-color-scheme: light)")?.matches;
  if (prefersLight) {
    return "light";
  }
  return "dark";
}

function App() {
  const [token, setToken] = useState<string | null>(() => getAuthToken());
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<ThemeMode>(() => resolveInitialTheme());

  const loginMutation = useMutation({
    mutationFn: login,
    onMutate: () => {
      setError(null);
    },
    onSuccess: (response) => {
      setToken(response.access_token);
    },
    onError: (mutationError: unknown) => {
      const message =
        mutationError instanceof Error ? mutationError.message : "Error desconocido";
      setError(message);
    },
  });

  const loading = loginMutation.isPending;
  const resetLoginMutation = loginMutation.reset;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("softmobile_theme", theme);
  }, [theme]);

  const themeLabel = useMemo(() => (theme === "dark" ? "oscuro" : "claro"), [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  const handleLogin = useCallback(
    async (credentials: Credentials) => {
      await loginMutation.mutateAsync(credentials);
    },
    [loginMutation],
  );

  const handleLogout = useCallback(() => {
    logout();
    setToken(null);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const handleUnauthorized = (event: Event) => {
      const customEvent = event as CustomEvent<string | undefined>;
      const message = customEvent.detail ?? "Tu sesión expiró. Inicia sesión nuevamente.";
      setError(message);
      resetLoginMutation();
      handleLogout();
    };
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => {
      window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, [handleLogout, resetLoginMutation]);

  return (
    <BrowserRouter>
      <div className={`app-root${!token ? " login-mode" : ""}`}>
        <AppRouter
          token={token}
          loading={loading}
          error={error}
          theme={theme}
          themeLabel={themeLabel}
          onToggleTheme={toggleTheme}
          onLogin={handleLogin}
          onLogout={handleLogout}
        />
      </div>
    </BrowserRouter>
  );
}

type AppRouterProps = {
  token: string | null;
  loading: boolean;
  error: string | null;
  theme: ThemeMode;
  themeLabel: string;
  onToggleTheme: () => void;
  onLogin: (credentials: Credentials) => Promise<void>;
  onLogout: () => void;
};

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

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        {!token ? (
          <>
            <Route
              path="/login"
              element={
                <LoginScene
                  theme={theme}
                  themeLabel={themeLabel}
                  onToggleTheme={onToggleTheme}
                  loading={loading}
                  error={error}
                  onLogin={onLogin}
                />
              }
            />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </>
        ) : (
          <>
            <Route
              path="/dashboard/*"
              element={
                <DashboardScene token={token} theme={theme} onToggleTheme={onToggleTheme} onLogout={onLogout} />
              }
            />
            <Route path="*" element={<Navigate to="/dashboard/inventory" replace />} />
          </>
        )}
      </Routes>
    </AnimatePresence>
  );
});

type LoginSceneProps = {
  theme: ThemeMode;
  themeLabel: string;
  onToggleTheme: () => void;
  loading: boolean;
  error: string | null;
  onLogin: (credentials: Credentials) => Promise<void>;
};

const LoginScene = memo(function LoginScene({
  theme,
  themeLabel,
  onToggleTheme,
  loading,
  error,
  onLogin,
}: LoginSceneProps) {
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

type DashboardSceneProps = {
  token: string;
  theme: ThemeMode;
  onToggleTheme: () => void;
  onLogout: () => void;
};

const ModuleFallback = memo(function ModuleFallback() {
  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>Cargando módulo…</span>
    </div>
  );
});

const DashboardScene = memo(function DashboardScene({ token, theme, onToggleTheme, onLogout }: DashboardSceneProps) {
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

export default App;
