import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig } from "axios";
import { getApiBaseUrl } from "../../config/api";

export const UNAUTHORIZED_EVENT = "softmobile:unauthorized";

const TOKEN_STORAGE_KEY = "softmobile_token";

function readStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch (error) {
    /* eslint-disable-next-line no-console */
    console.warn("No se pudo leer el token de autenticación", error);
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
    /* eslint-disable-next-line no-console */
    console.warn("No se pudo persistir el token de autenticación", error);
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

const API_BASE_URL = (import.meta.env.VITE_API_URL?.trim() ?? "") || getApiBaseUrl();

async function requestRefreshToken(): Promise<string | null> {
  try {
    const response = await axios.post<{ access_token?: string | null }>(
      `${API_BASE_URL}/auth/refresh`,
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
  } catch (error) {
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

function attachAuthorization(config: AxiosRequestConfig): AxiosRequestConfig {
  const token = getAuthToken();
  if (token) {
    config.headers = {
      ...(config.headers ?? {}),
      Authorization: `Bearer ${token}`,
    };
  }
  return config;
}

export function createHttpClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
  });

  instance.interceptors.request.use((config) => attachAuthorization(config));

  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const { response, config } = error;
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

export const httpClient = createHttpClient();

export default httpClient;
