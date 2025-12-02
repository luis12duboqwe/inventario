import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig, type InternalAxiosRequestConfig } from "axios";
import {
  clearApiBaseUrlOverride,
  getApiBaseUrl,
  setApiBaseUrlOverride,
} from "../config/api";
import { TOKEN_STORAGE_KEY } from "../config/constants";
import { emitClientWarning } from "../utils/clientLog";

export const UNAUTHORIZED_EVENT = "softmobile:unauthorized";
export const NETWORK_EVENT = "softmobile:network_error";
export const NETWORK_RECOVERY_EVENT = "softmobile:network_recovery";

function readStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch (error) {
    emitClientWarning("No se pudo leer el token de autenticación", error);
    return null;
  }
}

let inMemoryToken: string | null = readStoredToken();
let refreshPromise: Promise<string | null> | null = null;

export function getAuthToken(): string | null {
  return inMemoryToken ?? readStoredToken();
}

export function setAuthToken(token: string | null): void {
  inMemoryToken = token;
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (token) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch (error) {
    emitClientWarning("No se pudo persistir el token de autenticación", error);
  }
}

export function clearAuthToken(): void {
  setAuthToken(null);
}

function dispatchUnauthorized(detail?: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent<string | undefined>(UNAUTHORIZED_EVENT, { detail }));
}

function dispatchNetworkError(detail?: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent<string | undefined>(NETWORK_EVENT, { detail }));
}

function dispatchNetworkRecovery(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new CustomEvent(NETWORK_RECOVERY_EVENT));
}

export function parseFilenameFromDisposition(header: string | null, fallback: string): string {
  if (!header) {
    return fallback;
  }

  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }

  const asciiMatch = header.match(/filename="?([^";]+)"?/i);
  if (asciiMatch?.[1]) {
    return asciiMatch[1];
  }

  return fallback;
}

let apiBaseUrl = getApiBaseUrl();

async function requestRefreshToken(): Promise<string | null> {
  try {
    const response = await axios.post<{ access_token?: string | null }>(
      `${apiBaseUrl}/auth/refresh`,
      {},
      {
        withCredentials: true,
      },
    );
    const newToken = response.data.access_token ?? null;
    if (newToken) {
      setAuthToken(newToken);
    } else {
      clearAuthToken();
    }
    return newToken;
  } catch {
    clearAuthToken();
    return null;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = requestRefreshToken().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

type RetryConfig = AxiosRequestConfig & { __isRetryRequest?: boolean };

function attachAuthorization(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
  const token = getAuthToken();
  if (token) {
    // Asegurar cabeceras sin romper el tipo AxiosHeaders
    config.headers = (config.headers ?? ({} as unknown as typeof config.headers));
    const headers = config.headers as unknown as Record<string, string>;
    if (!headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return config;
}

export function createHttpClient(baseUrl: string = apiBaseUrl): AxiosInstance {
  const instance = axios.create({
    baseURL: baseUrl,
    withCredentials: true,
  });

  instance.interceptors.request.use((config) => attachAuthorization(config));

  instance.interceptors.response.use(
    (response) => {
      dispatchNetworkRecovery();
      return response;
    },
    async (error: AxiosError) => {
      const { response, config } = error;

      // Network Error (no response)
      if (!response) {
        dispatchNetworkError("No fue posible contactar la API de Softmobile. Verifica tu conexión.");
      } else if (response.status >= 500) {
        dispatchNetworkError(`La API respondió con un estado ${response.status}.`);
      }

      const retryConfig = (config ?? {}) as RetryConfig;
      if (response?.status === 401 && !retryConfig.__isRetryRequest) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          retryConfig.__isRetryRequest = true;
          retryConfig.headers = {
            ...(retryConfig.headers ?? {}),
            Authorization: `Bearer ${refreshed}`,
          };
          return instance(retryConfig);
        }
        dispatchUnauthorized(response?.data as string | undefined);
      }
      if (response?.status === 401) {
        dispatchUnauthorized(response?.data as string | undefined);
      }
      throw error;
    },
  );

  return instance;
}

export function getCurrentApiBaseUrl(): string {
  return apiBaseUrl;
}

export function reconfigureHttpClientBaseUrl(nextBaseUrl: string): string {
  apiBaseUrl = nextBaseUrl;
  httpClient.defaults.baseURL = nextBaseUrl;
  return apiBaseUrl;
}

export function applyApiBaseUrlOverride(nextBaseUrl: string): string | null {
  const normalized = setApiBaseUrlOverride(nextBaseUrl);
  if (normalized) {
    reconfigureHttpClientBaseUrl(normalized);
  }
  return normalized;
}

export function resetApiBaseUrlOverride(): string {
  clearApiBaseUrlOverride();
  const resolved = getApiBaseUrl();
  return reconfigureHttpClientBaseUrl(resolved);
}

export const httpClient = createHttpClient(apiBaseUrl);

export default httpClient;
