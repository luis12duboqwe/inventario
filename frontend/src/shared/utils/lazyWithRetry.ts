import {
  lazy,
  type ComponentType,
  type ExoticComponent,
  type LazyExoticComponent,
} from "react";

type RenderableComponent = ComponentType<never> | ExoticComponent<never>;

type ComponentProps<T> = T extends ComponentType<infer P>
  ? P
  : T extends ExoticComponent<infer P>
    ? P
    : never;

type LazyFactory<T extends RenderableComponent> = () => Promise<{ default: T }>;

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
 * Conserva las props del componente, incluso cuando el export default está memoizado.
 */
export function lazyWithRetry<T extends RenderableComponent>(
  factory: LazyFactory<T>,
  options: LazyWithRetryOptions = {},
): LazyExoticComponent<ComponentType<ComponentProps<T>>> {
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

  return lazy(async () => {
    const module = await load(0);
    return {
      default: module.default as ComponentType<ComponentProps<T>>,
    };
  });
}
