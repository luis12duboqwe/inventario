import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { RouterProvider } from "react-router-dom";
import { createAppRouter, type ThemeMode } from "../router";
import Loader from "../shared/components/Loader";
import type { Credentials } from "../api";
import { useAuth } from "../auth/useAuth"; // [PACK28-app]
import AppErrorBoundary from "../shared/components/AppErrorBoundary"; // [PACK36-app-boundary]
import SkipLink from "../components/a11y/SkipLink";
import { startWebVitalsLite } from "../lib/metrics/webVitalsLite";
import { logUI } from "../services/audit"; // [PACK36-app-boundary]

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
  const { user, accessToken, isLoading: authLoading, login: authLogin, logout: authLogout, lastError, clearError } =
    useAuth(); // [PACK28-app]
  const [error, setError] = useState<string | null>(null);
  const [loginPending, setLoginPending] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>(() => resolveInitialTheme());

  useEffect(() => {
    startWebVitalsLite();
  }, []);

  useEffect(() => {
    const handleWindowError = (event: ErrorEvent) => {
      const meta = {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error ? String(event.error) : undefined,
      };
      void logUI({
        ts: Date.now(),
        module: "OTHER",
        action: "window.error", // [PACK36-app-boundary]
        meta,
      }).catch(() => {
        console.error("[App] error global", meta);
      });
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason instanceof Error ? event.reason.message : String(event.reason);
      const meta = {
        reason,
        stack: event.reason?.stack,
      };
      void logUI({
        ts: Date.now(),
        module: "OTHER",
        action: "window.unhandledrejection", // [PACK36-app-boundary]
        meta,
      }).catch(() => {
        console.error("[App] rechazo no controlado", meta);
      });
    };

    window.addEventListener("error", handleWindowError);
    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      window.removeEventListener("error", handleWindowError);
      window.removeEventListener("unhandledrejection", handleUnhandledRejection);
    };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("softmobile_theme", theme);
  }, [theme]);

  const themeLabel = useMemo(() => (theme === "dark" ? "oscuro" : "claro"), [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  useEffect(() => {
    if (lastError) {
      setError(lastError);
      clearError();
    }
  }, [clearError, lastError]);

  const handleLogin = useCallback(
    async (credentials: Credentials) => {
      setLoginPending(true);
      setError(null);
      try {
        await authLogin(credentials);
      } catch (loginError) {
        const message =
          loginError instanceof Error ? loginError.message : "Error desconocido";
        setError(message);
        throw loginError;
      } finally {
        setLoginPending(false);
      }
    },
    [authLogin],
  );

  const handleLogout = useCallback(() => {
    authLogout();
  }, [authLogout]);

  const router = useMemo(
    () =>
      createAppRouter({
        token: accessToken,
        loading: authLoading || loginPending,
        error,
        theme,
        themeLabel,
        onToggleTheme: toggleTheme,
        onLogin: handleLogin,
        onLogout: handleLogout,
      }),
    [
      accessToken,
      authLoading,
      error,
      handleLogin,
      handleLogout,
      loginPending,
      theme,
      themeLabel,
      toggleTheme,
    ],
  );

  useEffect(
    () => () => {
      router.dispose();
    },
    [router],
  );

  const isAuthenticated = Boolean(user && accessToken);

  return (
    <AppErrorBoundary>
      <div className={`app-root${!isAuthenticated ? " login-mode" : ""}`}>
        <SkipLink />
        <Suspense fallback={<Loader variant="overlay" message="Cargando interfaz…" />}>
          <RouterProvider router={router} />
        </Suspense>
      </div>
    </AppErrorBoundary>
  );
}

export default App;
