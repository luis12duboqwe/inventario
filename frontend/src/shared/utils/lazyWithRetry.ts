import { lazy, type ComponentType, type LazyExoticComponent } from "react";

type LazyFactory<T extends ComponentType<any>> = () => Promise<{ default: T }>;

type LazyWithRetryOptions = {
  retries?: number;
  delayMs?: number;
  shouldRetry?: (error: unknown, attempt: number) => boolean;
  onRetry?: (error: unknown, attempt: number) => void;
};

function isChunkLoadError(error: unknown): error is Error {
  if (!(error instanceof Error)) {
    return false;
  }
  const message = error.message ?? "";
  return (
    /Failed to fetch dynamically imported module/.test(message) ||
    /ChunkLoadError/.test(error.name) ||
    /Loading chunk \d+ failed/.test(message)
  );
}

function wait(delayMs: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, delayMs));
}

/**
 * Envuelve React.lazy con reintentos limitados para mitigar fallos intermitentes al cargar módulos.
 */
export function lazyWithRetry<T extends ComponentType<any>>(
  factory: LazyFactory<T>,
  options: LazyWithRetryOptions = {},
): LazyExoticComponent<T> {
  const {
    retries = 2,
    delayMs = 500,
    shouldRetry = isChunkLoadError,
    onRetry,
  } = options;

  const totalAttempts = retries + 1;

  async function load(attempt: number): Promise<{ default: T }> {
    try {
      return await factory();
    } catch (error) {
      const nextAttempt = attempt + 1;
      const canRetry = nextAttempt <= retries && shouldRetry(error, nextAttempt);
      if (!canRetry) {
        throw error;
      }
      if (import.meta.env.DEV) {
        console.warn(
          `[lazyWithRetry] Reintentando carga dinámica (intento ${nextAttempt + 1} de ${totalAttempts}):`,
          error,
        );
      }
      onRetry?.(error, nextAttempt);
      if (delayMs > 0) {
        await wait(delayMs);
      }
      return load(nextAttempt);
    }
  }

  return lazy(() => load(0));
}
