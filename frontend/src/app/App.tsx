import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { createAppRouter, type ThemeMode } from "../router";
import Loader from "../shared/components/Loader";
import {
  getCurrentUser as fetchCurrentUser,
  login,
  logout,
  type Credentials,
  UNAUTHORIZED_EVENT,
  type UserAccount,
} from "../services/api/auth";
import { getAuthToken } from "../services/api/http";
import ErrorBoundary from "../components/boundaries/ErrorBoundary";
import SkipLink from "../components/a11y/SkipLink";
import { startWebVitalsLite } from "../lib/metrics/webVitalsLite";
import { AuthzProvider, type CurrentUser } from "../auth/useAuthz";

const AUTHZ_ROLE_NAMES: CurrentUser["role"][] = ["ADMIN", "GERENTE", "OPERADOR", "INVITADO"];

function normalizeRoleName(value?: string | null): CurrentUser["role"] | null {
  if (!value) {
    return null;
  }
  const normalized = value.toUpperCase() as CurrentUser["role"];
  return AUTHZ_ROLE_NAMES.includes(normalized) ? normalized : null;
}

function mapAccountToCurrentUser(account: UserAccount): CurrentUser {
  let resolvedRole: CurrentUser["role"] | null = null;
  for (const role of account.roles ?? []) {
    resolvedRole = normalizeRoleName(role.name);
    if (resolvedRole) {
      break;
    }
  }
  if (!resolvedRole) {
    resolvedRole = normalizeRoleName(account.rol) ?? "INVITADO";
  }

  return {
    id: String(account.id),
    name: account.full_name?.trim() || account.username,
    role: resolvedRole,
  };
}

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
  const queryClient = useQueryClient();

  const loginMutation = useMutation({
    mutationFn: login,
    onMutate: () => {
      setError(null);
    },
    onSuccess: (response) => {
      setToken(response.access_token);
      queryClient.invalidateQueries({ queryKey: ["auth", "current-user"] });
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
    queryClient.removeQueries({ queryKey: ["auth", "current-user"] });
  }, [queryClient]);

  const { data: currentUserAccount } = useQuery({
    queryKey: ["auth", "current-user"],
    queryFn: fetchCurrentUser,
    enabled: Boolean(token),
    staleTime: 60_000,
  });

  const authzUser = useMemo<CurrentUser | null>(() => {
    if (!token || !currentUserAccount) {
      return null;
    }
    return mapAccountToCurrentUser(currentUserAccount);
  }, [currentUserAccount, token]);

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
    <AuthzProvider user={authzUser}>
      <ErrorBoundary>
        <div className={`app-root${!token ? " login-mode" : ""}`}>
          <SkipLink />
          <Suspense fallback={<Loader variant="overlay" message="Cargando interfaz…" />}>
            <RouterProvider router={router} />
          </Suspense>
        </div>
      </ErrorBoundary>
    </AuthzProvider>
  );
}

export default App;
