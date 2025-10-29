import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { createAppRouter, type ThemeMode } from "../router";
import Loader from "../shared/components/Loader";
import { login, logout, type Credentials, UNAUTHORIZED_EVENT } from "../services/api/auth";
import { getAuthToken } from "../services/api/http";
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

  const { mutateAsync: executeLogin, reset: resetLoginMutation, isPending: loading } = loginMutation;

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

  const handleLogin = useCallback(
    async (credentials: Credentials) => {
      await executeLogin(credentials);
    },
    [executeLogin],
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

  const router = useMemo(
    () =>
      createAppRouter({
        token,
        loading,
        error,
        theme,
        themeLabel,
        onToggleTheme: toggleTheme,
        onLogin: handleLogin,
        onLogout: handleLogout,
      }),
    [error, handleLogin, handleLogout, loading, theme, themeLabel, toggleTheme, token],
  );

  useEffect(
    () => () => {
      router.dispose();
    },
    [router],
  );

  return (
    <ErrorBoundary>
      <div className={`app-root${!token ? " login-mode" : ""}`}>
        <SkipLink />
        <Suspense fallback={<Loader variant="overlay" message="Cargando interfaz…" />}>
          <RouterProvider router={router} />
        </Suspense>
      </div>
    </ErrorBoundary>
  );
}

export default App;
