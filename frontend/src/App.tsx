import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
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
    <div className={`app-root${!token ? " login-mode" : ""}`}>
      <AnimatePresence mode="wait">
        {!token ? (
          <motion.main
            key="login"
            className="login-wrapper"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            <WelcomeHero themeLabel={themeLabel} onToggleTheme={toggleTheme} activeTheme={theme} />
            <motion.section
              className="card login-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.5, ease: "easeOut" }}
            >
              <h2 className="accent-title">Ingreso seguro</h2>
              <LoginForm loading={loading} error={error} onSubmit={handleLogin} />
            </motion.section>
          </motion.main>
        ) : (
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
                <button className="secondary" type="button" onClick={toggleTheme} aria-pressed={theme === "light"}>
                  Tema {theme === "dark" ? "oscuro" : "claro"}
                </button>
                <button type="button" onClick={handleLogout}>
                  Cerrar sesión
                </button>
              </div>
            </header>
            <motion.main
              className="app-container"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
            >
              <Dashboard token={token} />
            </motion.main>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
