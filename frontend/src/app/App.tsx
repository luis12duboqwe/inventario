import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { RouterProvider } from "react-router-dom";
import { createAppRouter, type ThemeMode } from "../router";
import Loader from "../shared/components/Loader";
import type { Credentials } from "../api";
import { useAuth } from "../auth/useAuth"; // [PACK28-app]
import ErrorBoundary from "../components/boundaries/ErrorBoundary";
import SkipLink from "../components/a11y/SkipLink";
import { startWebVitalsLite } from "../lib/metrics/webVitalsLite";

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
    <ErrorBoundary>
      <div className={`app-root${!isAuthenticated ? " login-mode" : ""}`}>
        <SkipLink />
        <Suspense fallback={<Loader variant="overlay" message="Cargando interfaz…" />}>
          <RouterProvider router={router} />
        </Suspense>
      </div>
    </ErrorBoundary>
  );
}

export default App;
