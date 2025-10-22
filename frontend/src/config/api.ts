const LOCAL_API_BASE_URL = "http://127.0.0.1:8000";
const CODESPACES_DOMAIN_REGEX = /-(\d+)\.(app\.github\.dev|githubpreview\.dev)$/;

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
  if (port === "8000") {
    const normalizedProtocol = normalizeProtocol(protocol);
    return `${normalizedProtocol}://${hostname}`;
  }
  const targetHostname = hostname.replace(CODESPACES_DOMAIN_REGEX, `-8000.${domain}`);
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
  return `https://${name}-8000.${domain}`;
}

export function detectRuntimeEnvironment(): RuntimeEnvironment {
  const configuredUrl = import.meta.env.VITE_API_BASE_URL;
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

export function getApiBaseUrl(): string {
  const configuredUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configuredUrl) {
    return configuredUrl;
  }

  const codespacesUrl = detectCodespacesUrlFromWindow() ?? detectCodespacesUrlFromProcess();
  if (codespacesUrl) {
    return codespacesUrl;
  }

  return LOCAL_API_BASE_URL;
}

export const apiConfig = {
  get baseUrl(): string {
    return getApiBaseUrl();
  },
  detectRuntimeEnvironment,
};

export default apiConfig;
