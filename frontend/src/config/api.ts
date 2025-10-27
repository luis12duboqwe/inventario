const DEFAULT_API_PORT = "8000";
const DEFAULT_HOSTNAME = "127.0.0.1";
const DEFAULT_PROTOCOL = "https";
const CODESPACES_DOMAIN_REGEX = /-(\d+)\.(app\.github\.dev|githubpreview\.dev)$/;

const ENVIRONMENT_VARIABLE_KEYS = ["VITE_API_URL", "VITE_API_BASE_URL"] as const;

type ProcessEnv = { [key: string]: string | undefined };

type EnvRecord = Record<string, string | undefined>;

function getProcessEnv(): ProcessEnv | undefined {
  if (typeof globalThis === "undefined") {
    return undefined;
  }
  const globalProcess = (globalThis as { process?: { env?: ProcessEnv } }).process;
  return globalProcess?.env;
}

function readConfiguredApiUrl(): string | undefined {
  const sources: Array<EnvRecord | undefined> = [
    import.meta.env as EnvRecord,
    getProcessEnv(),
  ];

  for (const source of sources) {
    if (!source) {
      continue;
    }
    for (const key of ENVIRONMENT_VARIABLE_KEYS) {
      const value = source[key];
      if (value && value.trim()) {
        return value.trim();
      }
    }
  }

  return undefined;
}

const API_URL = readConfiguredApiUrl();

type RuntimeEnvironment = "codespaces" | "local" | "custom";

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

export function detectRuntimeEnvironment(): RuntimeEnvironment {
  const configuredUrl = API_URL;
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
  if (API_URL) {
    return API_URL;
  }

  const codespacesUrl = detectCodespacesUrlFromWindow() ?? detectCodespacesUrlFromProcess();
  if (codespacesUrl) {
    return codespacesUrl;
  }

  const localFallback = buildLocalFallbackUrl();
  if (localFallback) {
    return localFallback;
  }

  return `${DEFAULT_PROTOCOL}://${DEFAULT_HOSTNAME}:${DEFAULT_API_PORT}`;
}

export const apiConfig = {
  get baseUrl(): string {
    return getApiBaseUrl();
  },
  detectRuntimeEnvironment,
};

export default apiConfig;
