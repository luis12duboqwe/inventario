import { useEffect } from "react";
import {
  isRouteErrorResponse,
  useNavigate,
  useRouteError,
} from "react-router-dom";
import AppErrorBoundary from "../shared/components/AppErrorBoundary";
import Button from "../shared/components/ui/Button";
import { logUI } from "../services/audit";
import { safeString } from "../utils/safeValues";

// [PACK36-route-error]
type RouteErrorElementProps = {
  scope: string;
};

function normalizeErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  if (isRouteErrorResponse(error)) {
    return `${error.status} ${error.statusText}`;
  }
  return "Ocurrió un error inesperado";
}

const RouteErrorElement = ({ scope }: RouteErrorElementProps) => {
  const error = useRouteError();
  const navigate = useNavigate();
  const message = normalizeErrorMessage(error);

  useEffect(() => {
    const details = error instanceof Error ? error.stack : safeString((error as any)?.stack, "");
    void logUI({
      ts: Date.now(),
      module: "OTHER",
      action: "router.error", // [PACK36-route-error]
      meta: {
        scope,
        message,
        details,
      },
    }).catch(() => {
      console.error("[RouteErrorElement]", scope, message);
    });
  }, [error, message, scope]);

  return (
    <AppErrorBoundary
      forceFallback
      variant="inline"
      title="No se pudo cargar la sección"
      description={`Se produjo un error al renderizar ${scope}. Intenta recargar o vuelve más tarde.`}
      details={message}
      onRetry={() => navigate(0)}
    >
      <div style={{ padding: 24, textAlign: "center" }}>
        <Button type="button" variant="primary" onClick={() => navigate(0)}>
          Reintentar
        </Button>
      </div>
    </AppErrorBoundary>
  );
};

export default RouteErrorElement;
