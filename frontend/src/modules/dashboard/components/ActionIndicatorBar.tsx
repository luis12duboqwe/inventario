import { useMemo } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  CloudCog,
  Loader2,
  WifiOff,
} from "lucide-react";

export type ActionIndicatorBarProps = {
  loading: boolean;
  hasSuccessMessage: boolean;
  hasError: boolean;
  errorMessage: string | null;
  syncStatus: string | null;
  networkAlert: string | null;
  lastInventoryRefresh: Date | null;
};

type Indicator = {
  id: "save" | "sync" | "alerts";
  label: string;
  description: string;
  icon: JSX.Element;
  status: "ok" | "warning" | "error";
};

function formatRelative(date: Date | null) {
  if (!date) {
    return "Sincronización pendiente";
  }
  return new Intl.RelativeTimeFormat("es", { numeric: "auto" }).format(
    Math.round((date.getTime() - Date.now()) / 60000),
    "minute",
  );
}

function ActionIndicatorBar({
  loading,
  hasSuccessMessage,
  hasError,
  errorMessage,
  syncStatus,
  networkAlert,
  lastInventoryRefresh,
}: ActionIndicatorBarProps) {
  const indicators = useMemo<Indicator[]>(() => {
    const saveIndicator: Indicator = loading
      ? {
          id: "save",
          label: "Guardado",
          description: "Procesando cambios en curso",
          icon: <Loader2 className="action-indicator__icon spinning" aria-hidden="true" />,
          status: "warning",
        }
      : {
          id: "save",
          label: "Guardado",
          description: hasSuccessMessage
            ? "Cambios confirmados recientemente"
            : "Sin cambios pendientes",
          icon: <CheckCircle2 className="action-indicator__icon" aria-hidden="true" />,
          status: "ok",
        };

    let syncDescription = syncStatus ?? formatRelative(lastInventoryRefresh);
    let syncStatusVariant: Indicator["status"] = "ok";
    let syncIcon: JSX.Element = <CloudCog className="action-indicator__icon" aria-hidden="true" />;

    if (networkAlert) {
      syncDescription = networkAlert;
      syncStatusVariant = "warning";
      syncIcon = <WifiOff className="action-indicator__icon" aria-hidden="true" />;
    } else if (syncStatus && syncStatus.toLowerCase().includes("error")) {
      syncStatusVariant = "error";
      syncIcon = <AlertTriangle className="action-indicator__icon" aria-hidden="true" />;
    }

    const syncIndicator: Indicator = {
      id: "sync",
      label: "Sincronización",
      description: syncDescription,
      icon: syncIcon,
      status: syncStatusVariant,
    };

    const alertsIndicator: Indicator = hasError
      ? {
          id: "alerts",
          label: "Alertas",
          description: errorMessage ?? "Se registró un error pendiente",
          icon: <AlertTriangle className="action-indicator__icon" aria-hidden="true" />,
          status: "error",
        }
      : {
          id: "alerts",
          label: "Alertas",
          description: "Sin alertas críticas registradas",
          icon: <CheckCircle2 className="action-indicator__icon" aria-hidden="true" />,
          status: "ok",
        };

    return [saveIndicator, syncIndicator, alertsIndicator];
  }, [
    errorMessage,
    hasError,
    hasSuccessMessage,
    lastInventoryRefresh,
    loading,
    networkAlert,
    syncStatus,
  ]);

  return (
    <section
      className="action-indicator-bar"
      aria-label="Indicadores clave de operación"
      aria-live="polite"
    >
      {indicators.map((indicator) => (
        <div
          key={indicator.id}
          className={`action-indicator action-indicator--${indicator.status}`}
          role="status"
          aria-live="polite"
        >
          {indicator.icon}
          <div className="action-indicator__content">
            <span className="action-indicator__label">{indicator.label}</span>
            <span className="action-indicator__description">{indicator.description}</span>
          </div>
        </div>
      ))}
    </section>
  );
}

export default ActionIndicatorBar;
