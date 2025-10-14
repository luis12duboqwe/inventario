import { useEffect, useMemo, useState } from "react";
import Dashboard from "./components/Dashboard";
import LoginForm from "./components/LoginForm";
import { Credentials, login } from "./api";

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

  if (!token) {
    return (
      <div className="app-root login-mode">
        <main className="login-wrapper fade-in">
          <section className="card brand-card">
            <h1>Softmobile Inventario</h1>
            <p>
              Cliente corporativo para sincronizar existencias, capturar movimientos y generar respaldos con un solo
              panel.
            </p>
            <p className="badge">Versión tienda · Tema {themeLabel}</p>
            <button className="secondary" type="button" onClick={toggleTheme}>
              Cambiar a tema {theme === "dark" ? "claro" : "oscuro"}
            </button>
          </section>
          <section className="card login-card">
            <h2 className="accent-title">Ingreso seguro</h2>
            <LoginForm loading={loading} error={error} onSubmit={handleLogin} />
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="app-root">
      <header className="topbar fade-in">
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
      <main className="app-container fade-in">
        <Dashboard token={token} />
      </main>
    </div>
  );
}

export default App;
