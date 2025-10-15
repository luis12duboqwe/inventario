import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import Dashboard from "./components/Dashboard";
import LoginForm from "./components/LoginForm";
import { Credentials, login } from "./api";
import WelcomeHero from "./components/WelcomeHero";

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

  const toggleTheme = () => {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  };

  const handleLogin = async (credentials: Credentials) => {
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
  };

  const handleLogout = () => {
    localStorage.removeItem("softmobile_token");
    setToken(null);
  };

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

function AppRouter({ token, loading, error, theme, themeLabel, onToggleTheme, onLogin, onLogout }: AppRouterProps) {
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
              element={<DashboardScene token={token} theme={theme} onToggleTheme={onToggleTheme} onLogout={onLogout} />}
            />
            <Route path="*" element={<Navigate to="/dashboard/inventory" replace />} />
          </>
        )}
      </Routes>
    </AnimatePresence>
  );
}

type LoginSceneProps = {
  theme: ThemeMode;
  themeLabel: string;
  onToggleTheme: () => void;
  loading: boolean;
  error: string | null;
  onLogin: (credentials: Credentials) => Promise<void>;
};

function LoginScene({ theme, themeLabel, onToggleTheme, loading, error, onLogin }: LoginSceneProps) {
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
        <h2 className="accent-title">Ingreso seguro</h2>
        <LoginForm loading={loading} error={error} onSubmit={onLogin} />
      </motion.section>
    </motion.main>
  );
}

type DashboardSceneProps = {
  token: string;
  theme: ThemeMode;
  onToggleTheme: () => void;
  onLogout: () => void;
};

function DashboardScene({ token, theme, onToggleTheme, onLogout }: DashboardSceneProps) {
  return (
    <motion.div
      key="dashboard"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      <header className="topbar">
        <div>
          <h1>Softmobile Inventario</h1>
          <p className="topbar-subtitle">Sesión activa para captura, reportes y sincronización multi‑tienda.</p>
        </div>
        <div className="topbar-controls">
          <button className="secondary" type="button" onClick={onToggleTheme} aria-pressed={theme === "light"}>
            Tema {theme === "dark" ? "oscuro" : "claro"}
          </button>
          <button type="button" onClick={onLogout}>
            Cerrar sesión
          </button>
        </div>
      </header>
      <motion.main
        className="app-container"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      >
        <Dashboard token={token} />
      </motion.main>
    </motion.div>
  );
}

export default App;
