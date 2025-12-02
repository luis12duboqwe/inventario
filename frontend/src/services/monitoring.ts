/**
 * Enterprise Monitoring Service
 * Abstraction layer for error tracking and performance monitoring.
 * Currently logs to console and internal audit, but designed to be
 * easily swapped with Sentry, Datadog, or LogRocket.
 */

import { logUI } from "./audit";

export interface ErrorContext {
  componentStack?: string;
  user?: {
    id: string;
    role: string;
  };
  tags?: Record<string, string>;
}

class MonitoringService {
  private static instance: MonitoringService;
  private isInitialized = false;

  private constructor() {}

  public static getInstance(): MonitoringService {
    if (!MonitoringService.instance) {
      MonitoringService.instance = new MonitoringService();
    }
    return MonitoringService.instance;
  }

  public init() {
    if (this.isInitialized) return;
    // Here we would initialize Sentry.init()
    console.log("[Monitoring] Service initialized");
    this.isInitialized = true;
  }

  public captureException(error: unknown, context?: ErrorContext) {
    const message = error instanceof Error ? error.message : String(error);
    const stack = error instanceof Error ? error.stack : undefined;

    // 1. Log to Console (Dev)
    console.error("[Monitoring] Exception captured:", message, context);

    // 2. Log to Internal Audit (Compliance)
    void logUI({
      ts: Date.now(),
      module: "MONITORING",
      action: "exception",
      meta: {
        message,
        stack,
        componentStack: context?.componentStack,
        tags: context?.tags,
      },
    }).catch((err) => console.error("[Monitoring] Failed to log to audit:", err));

    // 3. Send to External Service (Sentry/Datadog)
    // if (window.Sentry) Sentry.captureException(error, { extra: context });
  }

  public captureMessage(message: string, level: "info" | "warning" | "error" = "info") {
    console.log(`[Monitoring] [${level.toUpperCase()}] ${message}`);
    // if (window.Sentry) Sentry.captureMessage(message, level);
  }
}

export const monitoring = MonitoringService.getInstance();
