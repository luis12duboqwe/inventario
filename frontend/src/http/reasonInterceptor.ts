import { getStoredReason, rememberReason } from "../utils/reasonStorage";

const READ_ONLY_METHOD = "GET";
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

const SENSITIVE_RULES: { prefix: string; defaultReason: string }[] = [
  { prefix: "/pos", defaultReason: "Consulta POS corporativa" },
  { prefix: "/reports", defaultReason: "Consulta reportes corporativa" },
  { prefix: "/customers", defaultReason: "Consulta clientes corporativa" },
  { prefix: "/price-lists", defaultReason: "Consulta listas de precios" },
];

function normalizePath(path: string): string {
  const [rawPath = ""] = path.split("?");
  if (!rawPath) {
    return "/";
  }

  if (rawPath === "/") {
    return rawPath;
  }

  return rawPath.endsWith("/") ? rawPath.slice(0, -1) : rawPath;
}

function findRule(path: string): { prefix: string; defaultReason: string } | undefined {
  return SENSITIVE_RULES.find((rule) => path === rule.prefix || path.startsWith(`${rule.prefix}/`));
}

function resolveDefaultReason(path: string): string | null {
  const rule = findRule(path);
  return rule ? rule.defaultReason : null;
}

function sanitizeReason(value: string | null): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length >= 5 ? trimmed : null;
}

export function applyReasonHeader(path: string, method: string, headers: Headers): void {
  const normalizedMethod = method.toUpperCase();
  const normalizedPath = normalizePath(path);
  const rule = findRule(normalizedPath);

  if (!rule) {
    return;
  }

  const provided = sanitizeReason(headers.get("X-Reason"));
  if (provided) {
    headers.set("X-Reason", provided);
    rememberReason(provided);
    return;
  }

  const stored = getStoredReason();
  if (stored) {
    headers.set("X-Reason", stored);
    return;
  }

  if (normalizedMethod === READ_ONLY_METHOD) {
    const fallback = resolveDefaultReason(normalizedPath);
    if (fallback) {
      headers.set("X-Reason", fallback);
      rememberReason(fallback);
      return;
    }
  }

  if (MUTATING_METHODS.has(normalizedMethod)) {
    throw new Error(
      "Debes registrar un motivo corporativo valido (X-Reason) antes de continuar.",
    );
  }

  throw new Error("No fue posible determinar un motivo corporativo para la operación.");
}

export function __testables() {
  return {
    normalizePath,
    resolveDefaultReason,
  };
}
