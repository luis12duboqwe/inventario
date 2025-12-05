import React from "react";
import Button from "./Button";
import { monitoring } from "../../services/monitoring";

// [PACK36-error-boundary]
type AppErrorBoundaryProps = {
  children: React.ReactNode;
  title?: string;
  description?: string;
  onRetry?: () => void;
  variant?: "full" | "inline";
  forceFallback?: boolean; // [PACK36-error-boundary]
  details?: string;
};

// [PACK36-error-boundary]
type AppErrorBoundaryState = {
  hasError: boolean;
  errorMessage: string | null;
  stack: string | null;
};

class AppErrorBoundary extends React.Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  // [PACK36-error-boundary]
  constructor(props: AppErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, errorMessage: null, stack: null };
  }

  static getDerivedStateFromError(error: unknown): AppErrorBoundaryState {
    return {
      hasError: true,
      errorMessage: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack ?? null : null,
    };
  }

  override componentDidCatch(error: unknown, info: React.ErrorInfo): void {
    monitoring.captureException(error, {
      componentStack: info.componentStack ?? "",
      tags: {
        boundary: "AppErrorBoundary",
        variant: this.props.variant ?? "full",
      },
    });
  }

  private handleRetry = () => {
    this.setState({ hasError: false, errorMessage: null, stack: null });
    this.props.onRetry?.();
  };

  override render(): React.ReactNode {
    const shouldShowFallback = this.state.hasError || this.props.forceFallback;

    if (!shouldShowFallback) {
      return this.props.children;
    }

    const { variant = "full", title, description, details } = this.props;
    const isInline = variant === "inline";
    const errorDetails = this.state.errorMessage ?? details ?? null;

    return (
      <div
        role="alert"
        aria-live="assertive"
        className={`error-boundary ${isInline ? "error-boundary--inline" : "error-boundary--full"}`}
      >
        <div className="error-boundary__card">
          <h1 className="error-boundary__title">{title ?? "Algo salió mal"}</h1>
          <p className="error-boundary__description">
            {description ?? "Se produjo un error inesperado al mostrar esta sección."}
          </p>
          {errorDetails ? (
            <details className="error-boundary__details">
              <summary className="error-boundary__summary">Detalles técnicos</summary>
              <pre className="error-boundary__pre">{errorDetails}</pre>
            </details>
          ) : null}
          <div className="error-boundary__actions">
            <Button type="button" variant="primary" onClick={this.handleRetry}>
              Reintentar
            </Button>
            {!isInline ? (
              <Button type="button" variant="ghost" onClick={() => window.location.assign("/")}>
                Ir al inicio
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    );
  }
}

export default AppErrorBoundary;
