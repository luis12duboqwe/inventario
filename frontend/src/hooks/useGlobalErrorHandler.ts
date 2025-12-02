import { useEffect } from "react";
import { logUI } from "../services/audit";

export function useGlobalErrorHandler() {
  useEffect(() => {
    const handleWindowError = (event: ErrorEvent) => {
      const meta = {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error ? String(event.error) : undefined,
      };
      void logUI({
        ts: Date.now(),
        module: "OTHER",
        action: "window.error",
        meta,
      }).catch(() => {
        console.error("[App] error global", meta);
      });
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason instanceof Error ? event.reason.message : String(event.reason);
      const meta = {
        reason,
        stack: event.reason?.stack,
      };
      void logUI({
        ts: Date.now(),
        module: "OTHER",
        action: "window.unhandledrejection",
        meta,
      }).catch(() => {
        console.error("[App] rechazo no controlado", meta);
      });
    };

    window.addEventListener("error", handleWindowError);
    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      window.removeEventListener("error", handleWindowError);
      window.removeEventListener("unhandledrejection", handleUnhandledRejection);
    };
  }, []);
}
