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
        style={{
          minHeight: isInline ? "auto" : "100vh",
          display: "grid",
          placeItems: "center",
          padding: isInline ? 16 : 32,
          background: isInline ? "transparent" : "linear-gradient(180deg,#0f172a,#111827)",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: 520,
            borderRadius: 16,
            border: "1px solid rgba(56,189,248,0.25)",
            background: "rgba(15,23,42,0.92)",
            boxShadow: "0 18px 38px rgba(8, 47, 73, 0.35)",
            padding: 28,
            color: "#e2e8f0",
            textAlign: "center",
          }}
        >
          <h1 style={{ fontSize: 24, marginBottom: 8 }}>{title ?? "Algo salió mal"}</h1>
          <p style={{ marginBottom: 18, color: "#94a3b8" }}>
            {description ?? "Se produjo un error inesperado al mostrar esta sección."}
          </p>
          {errorDetails ? (
            <details
              style={{
                textAlign: "left",
                marginBottom: 20,
                background: "rgba(148,163,184,0.08)",
                borderRadius: 12,
                padding: 16,
                border: "1px solid rgba(148,163,184,0.25)",
              }}
            >
              <summary style={{ cursor: "pointer", color: "#38bdf8" }}>Detalles técnicos</summary>
              <pre
                style={{
                  marginTop: 12,
                  whiteSpace: "pre-wrap",
                  fontFamily: "var(--font-mono, 'Fira Code', monospace)",
                  fontSize: 13,
                  lineHeight: 1.5,
                }}
              >
                {errorDetails}
              </pre>
            </details>
          ) : null}
          <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
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
