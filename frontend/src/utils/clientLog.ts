export const CLIENT_LOG_EVENT = "softmobile:client-log" as const;

export type ClientLogLevel = "warning" | "error";

export type ClientLogDetail = {
  level: ClientLogLevel;
  message: string;
  error?: {
    name?: string;
    message?: string;
    stack?: string;
    raw?: string;
  };
};

function normalizeError(error: unknown): ClientLogDetail["error"] {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      ...(error.stack ? { stack: error.stack } : {}),
    };
  }

  if (typeof error === "string") {
    return { message: error };
  }

  if (typeof error === "number" || typeof error === "boolean") {
    return { message: String(error) };
  }

  if (error && typeof error === "object") {
    try {
      return { raw: JSON.stringify(error) };
    } catch {
      return { raw: Object.prototype.toString.call(error) };
    }
  }

  if (error === null || typeof error === "undefined") {
    return undefined;
  }

  return { message: String(error) };
}

function emitClientLog(level: ClientLogLevel, message: string, error?: unknown): void {
  if (typeof window === "undefined") {
    return;
  }

  const detail: ClientLogDetail = { level, message };
  const normalized = normalizeError(error);
  if (normalized) {
    detail.error = normalized;
  }

  window.dispatchEvent(new CustomEvent<ClientLogDetail>(CLIENT_LOG_EVENT, { detail }));
}

export function emitClientWarning(message: string, error?: unknown): void {
  emitClientLog("warning", message, error);
}

export function emitClientError(message: string, error?: unknown): void {
  emitClientLog("error", message, error);
}
