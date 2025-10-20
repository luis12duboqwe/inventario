import { Suspense, lazy, memo, useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import LoginForm from "./components/LoginForm";
import BootstrapForm, { type BootstrapFormValues } from "./components/BootstrapForm";
import Button from "./components/ui/Button";
import { type BootstrapStatus, Credentials, bootstrapAdmin, getBootstrapStatus, login } from "./api";
import WelcomeHero from "./components/WelcomeHero";

const Dashboard = lazy(() => import("./components/Dashboard"));

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
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("softmobile_token"));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<ThemeMode>(() => resolveInitialTheme());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("softmobile_theme", theme);
  }, [theme]);

  const themeLabel = useMemo(() => (theme === "dark" ? "oscuro" : "claro"), [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  const handleLogin = useCallback(async (credentials: Credentials) => {
    try {
      setLoading(true);
      setError(null);
      const response = await login(credentials);
      localStorage.setItem("softmobile_token", response.access_token);
      setToken(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleLogout = useCallback(() => {
    localStorage.removeItem("softmobile_token");
    setToken(null);
  }, []);

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
  const [bootstrapStatus, setBootstrapStatus] = useState<BootstrapStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [bootstrapLoading, setBootstrapLoading] = useState(false);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const [bootstrapSuccess, setBootstrapSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"login" | "bootstrap">("login");

  useEffect(() => {
    let cancelled = false;
    getBootstrapStatus()
      .then((status) => {
        if (cancelled) {
          return;
        }
        setBootstrapStatus(status);
        setStatusError(null);
      })
      .catch((fetchError) => {
        if (cancelled) {
          return;
        }
        const message =
          fetchError instanceof Error
            ? fetchError.message
            : "No fue posible verificar el estado del registro inicial.";
        setStatusError(message);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const disponible = bootstrapStatus?.disponible;
    if (disponible === true) {
      setActiveTab("bootstrap");
    } else if (disponible === false) {
      setActiveTab("login");
    }
  }, [bootstrapStatus?.disponible]);

  const canDisplayBootstrap = bootstrapStatus?.disponible !== false;
  const allowBootstrap = bootstrapStatus?.disponible === true;

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
      try {
        setBootstrapLoading(true);
        setBootstrapError(null);
        setBootstrapSuccess(null);
        await bootstrapAdmin({
          username: values.username,
          password: values.password,
          full_name: values.fullName,
          telefono: values.telefono,
        });
        setBootstrapStatus((current) => ({
          disponible: false,
          usuarios_registrados: (current?.usuarios_registrados ?? 0) + 1,
        }));
        setBootstrapSuccess("Cuenta creada correctamente. Iniciando sesión…");
        await onLogin({ username: values.username, password: values.password });
      } catch (submitError) {
        const message =
          submitError instanceof Error
            ? submitError.message
            : "No fue posible registrar la cuenta inicial.";
        setBootstrapError(message);
        if (message.includes("usuarios registrados")) {
          setBootstrapStatus((current) => ({
            disponible: false,
            usuarios_registrados: Math.max(current?.usuarios_registrados ?? 1, 1),
          }));
        }
      } finally {
        setBootstrapLoading(false);
      }
    },
    [onLogin],
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
        {statusError ? <div className="alert warning">{statusError}</div> : null}
        {activeTab === "bootstrap" && canDisplayBootstrap ? (
          <BootstrapForm
            loading={bootstrapLoading || loading}
            error={bootstrapError}
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
