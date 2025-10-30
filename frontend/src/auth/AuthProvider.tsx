import { isAxiosError } from "axios";
import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { AuthProfile, Credentials } from "../api";
import {
  UNAUTHORIZED_EVENT,
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  refreshAccessToken,
} from "../services/api/auth";
import { getAuthToken } from "../services/api/http";
import { AuthzProvider, type CurrentUser as AuthzUser, type Role } from "./useAuthz";

// [PACK28-auth-provider]
type AuthContextValue = {
  user: AuthProfile | null;
  role: Role | null;
  accessToken: string | null;
  isLoading: boolean;
  lastError: string | null;
  login: (credentials: Credentials) => Promise<AuthProfile>;
  logout: () => void;
  refresh: () => Promise<string | null>;
  clearError: () => void;
};

// [PACK28-auth-provider]
const AuthContext = createContext<AuthContextValue>({
  user: null,
  role: null,
  accessToken: null,
  isLoading: true,
  lastError: null,
  async login() {
    throw new Error("AuthProvider no inicializado");
  },
  logout() {
    throw new Error("AuthProvider no inicializado");
  },
  async refresh() {
    throw new Error("AuthProvider no inicializado");
  },
  clearError() {
    throw new Error("AuthProvider no inicializado");
  },
});

// [PACK28-auth-provider]
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthProfile | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(() => getAuthToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastError, setLastError] = useState<string | null>(null);

  const role = user ? (user.role as Role | null) : null;

  const syncAccessToken = useCallback((token: string | null) => {
    setAccessToken(token);
  }, []);

  const loadProfile = useCallback(async () => {
    setIsLoading(true);
    try {
      const profile = await getCurrentUser();
      setUser(profile);
      syncAccessToken(getAuthToken());
      setLastError(null);
    } catch (error) {
      setUser(null);
      syncAccessToken(null);
      if (isAxiosError(error) && error.response?.status === 401) {
        setLastError(null);
      } else {
        const message =
          error instanceof Error ? error.message : "No fue posible validar tu sesión.";
        setLastError(message);
      }
    } finally {
      setIsLoading(false);
    }
  }, [syncAccessToken]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    const handleUnauthorized = (event: Event) => {
      const message = (event as CustomEvent<string | undefined>).detail;
      setLastError(message ?? "Tu sesión expiró. Inicia sesión nuevamente.");
      void logoutRequest().catch(() => {
        /* ignoramos errores al cerrar sesión forzada */
      });
      setUser(null);
      syncAccessToken(null);
    };
    if (typeof window !== "undefined") {
      window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized as EventListener);
    }
    return () => {
      if (typeof window !== "undefined") {
        window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized as EventListener);
      }
    };
  }, [syncAccessToken]);

  const login = useCallback(
    async (credentials: Credentials) => {
      setIsLoading(true);
      try {
        const session = await loginRequest(credentials);
        syncAccessToken(session.access_token);
        const profile = await getCurrentUser();
        setUser(profile);
        setLastError(null);
        return profile;
      } catch (error) {
        setUser(null);
        syncAccessToken(null);
        const message =
          error instanceof Error ? error.message : "No fue posible iniciar sesión.";
        setLastError(message);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    [syncAccessToken],
  );

  const logout = useCallback(() => {
    void logoutRequest().catch(() => {
      /* ignoramos errores al cerrar sesión manual */
    });
    setUser(null);
    syncAccessToken(null);
  }, [syncAccessToken]);

  const refresh = useCallback(async () => {
    try {
      const session = await refreshAccessToken();
      const token = session?.access_token ?? null;
      syncAccessToken(token);
      if (!token) {
        setUser(null);
      }
      return token;
    } catch (error) {
      logout();
      throw error;
    }
  }, [logout, syncAccessToken]);

  const clearError = useCallback(() => {
    setLastError(null);
  }, []);

  const authzUser = useMemo<AuthzUser | null>(() => {
    if (!user) {
      return null;
    }
    return {
      id: String(user.id),
      name: user.name,
      role: (user.role as Role) ?? "INVITADO",
    };
  }, [user]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      role,
      accessToken,
      isLoading,
      lastError,
      login,
      logout,
      refresh,
      clearError,
    }),
    [user, role, accessToken, isLoading, lastError, login, logout, refresh, clearError],
  );

  return (
    <AuthContext.Provider value={value}>
      <AuthzProvider user={authzUser}>{children}</AuthzProvider>
    </AuthContext.Provider>
  );
}

export { AuthContext };
export default AuthProvider;
