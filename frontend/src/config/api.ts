const DEFAULT_API_PORT = "8000";
const DEFAULT_PROTOCOL = "https";
const RELATIVE_API_BASE = "/api";
const CODESPACES_DOMAIN_REGEX = /-(\d+)\.(app\.github\.dev|githubpreview\.dev)$/;
const API_OVERRIDE_STORAGE_KEY = "softmobile_api_base_override";
const PRIVATE_IPV4_REGEX = /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/;

type RuntimeEnvironment = "codespaces" | "local" | "custom";

function normalizeBaseUrl(raw: string | null | undefined): string | null {
  if (!raw) {
    return null;
  }
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
  return withProtocol.replace(/\/+$/, "");
}

const ENV_API_URL = normalizeBaseUrl(import.meta.env.VITE_API_URL?.trim());

function normalizeProtocol(protocol: string | undefined): string {
  if (!protocol) {
    return "https";
  }
  const cleaned = protocol.endsWith(":") ? protocol.slice(0, -1) : protocol;
  if (cleaned === "http" || cleaned === "https") {
    return cleaned;
  }
  return "https";
}

function buildCodespacesUrlFromHostname(hostname: string, protocol: string | undefined): string | undefined {
  const match = hostname.match(CODESPACES_DOMAIN_REGEX);
  if (!match) {
    return undefined;
  }
  const [, port, domain] = match;
  if (port === DEFAULT_API_PORT) {
    const normalizedProtocol = normalizeProtocol(protocol);
    return `${normalizedProtocol}://${hostname}`;
  }
  const targetHostname = hostname.replace(
    CODESPACES_DOMAIN_REGEX,
    `-${DEFAULT_API_PORT}.${domain}`,
  );
  const normalizedProtocol = normalizeProtocol(protocol);
  return `${normalizedProtocol}://${targetHostname}`;
}

function detectCodespacesUrlFromWindow(): string | undefined {
  if (typeof window === "undefined" || !window.location) {
    return undefined;
  }
  const { hostname, protocol } = window.location;
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return undefined;
  }
  return buildCodespacesUrlFromHostname(hostname, protocol);
}

type ProcessEnv = { [key: string]: string | undefined };

function getProcessEnv(): ProcessEnv | undefined {
  if (typeof globalThis === "undefined") {
    return undefined;
  }
  const globalProcess = (globalThis as { process?: { env?: ProcessEnv } }).process;
  return globalProcess?.env;
}

function detectCodespacesUrlFromProcess(): string | undefined {
  const env = getProcessEnv();
  if (!env) {
    return undefined;
  }
  const name = env.CODESPACE_NAME;
  if (!name) {
    return undefined;
  }
  const domain = env.GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN ?? "app.github.dev";
  return `${DEFAULT_PROTOCOL}://${name}-${DEFAULT_API_PORT}.${domain}`;
}

export function getStoredApiBaseUrlOverride(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const stored = window.localStorage.getItem(API_OVERRIDE_STORAGE_KEY);
    return normalizeBaseUrl(stored);
  } catch (error) {
    if (import.meta.env.DEV) {
      console.warn("No fue posible leer la URL de API almacenada", error);
    }
    return null;
  }
}

export function setApiBaseUrlOverride(baseUrl: string | null): string | null {
  const normalized = normalizeBaseUrl(baseUrl);
  if (typeof window === "undefined") {
    return normalized;
  }
  try {
    if (normalized) {
      window.localStorage.setItem(API_OVERRIDE_STORAGE_KEY, normalized);
    } else {
      window.localStorage.removeItem(API_OVERRIDE_STORAGE_KEY);
    }
  } catch (error) {
    if (import.meta.env.DEV) {
      console.warn("No fue posible persistir la URL base de la API", error);
    }
  }
  return normalized;
}

export function clearApiBaseUrlOverride(): void {
  setApiBaseUrlOverride(null);
}

export function detectRuntimeEnvironment(): RuntimeEnvironment {
  const configuredUrl = getStoredApiBaseUrlOverride() ?? ENV_API_URL;
  if (configuredUrl) {
    if (configuredUrl.includes("github.dev") || configuredUrl.includes("githubpreview.dev")) {
      return "codespaces";
    }
    if (configuredUrl.includes("127.0.0.1") || configuredUrl.includes("localhost")) {
      return "local";
    }
    return "custom";
  }

  const codespacesUrl = detectCodespacesUrlFromWindow() ?? detectCodespacesUrlFromProcess();
  if (codespacesUrl) {
    return "codespaces";
  }

  if (typeof window !== "undefined" && window.location) {
    const hostname = window.location.hostname;
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return "local";
    }
  }

  return "local";
}

function buildLocalFallbackUrl(): string | undefined {
  if (typeof window === "undefined" || !window.location) {
    return undefined;
  }

  const { protocol, hostname } = window.location;
  const normalizedProtocol = normalizeProtocol(protocol);
  return `${normalizedProtocol}://${hostname}:${DEFAULT_API_PORT}`;
}

export function getApiBaseUrl(): string {
  const storedOverride = getStoredApiBaseUrlOverride();
  if (storedOverride) {
    return storedOverride;
  }

  if (ENV_API_URL) {
    return ENV_API_URL;
  }

  const codespacesUrl = detectCodespacesUrlFromWindow() ?? detectCodespacesUrlFromProcess();
  if (codespacesUrl) {
    return codespacesUrl;
  }

  if (typeof window !== "undefined" && window.location) {
    const { hostname, port, protocol } = window.location;
    if (!hostname) {
      return RELATIVE_API_BASE;
    }
    const normalizedProtocol = normalizeProtocol(protocol);
    const isLocalHost =
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname === "0.0.0.0" ||
      hostname === "::1";
    const isLanHost = PRIVATE_IPV4_REGEX.test(hostname);

    // Fuerza el uso de base relativa `/api` cuando se ejecuta en Vite dev (4173/5173)
    if (isLocalHost && (port === "5173" || port === "4173")) {
      return RELATIVE_API_BASE;
    }
    if (isLocalHost && (!port || port === DEFAULT_API_PORT)) {
      return RELATIVE_API_BASE;
    }

    if (isLanHost) {
      const targetPort = !port || port === "5173" || port === "4173" ? DEFAULT_API_PORT : port;
      return `${normalizedProtocol}://${hostname}:${targetPort}`;
    }

    if (port === "5173" || port === "4173") {
      // Preferir el proxy relativo en dev para evitar CORS
      return RELATIVE_API_BASE;
    }

    if (port === DEFAULT_API_PORT && !isLocalHost) {
      return `${normalizedProtocol}://${hostname}:${DEFAULT_API_PORT}`;
    }
    if (!hostname) {
      return RELATIVE_API_BASE;
    }
  }

  const localFallback = buildLocalFallbackUrl();
  if (localFallback) {
    return localFallback;
  }

  return RELATIVE_API_BASE;
}

export const apiConfig = {
  get baseUrl(): string {
    return getApiBaseUrl();
  },
  detectRuntimeEnvironment,
};

export default apiConfig;
