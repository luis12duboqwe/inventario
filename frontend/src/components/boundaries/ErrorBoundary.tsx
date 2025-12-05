import React from "react";
import { API_URL } from "@api/client";

type Props = { children: React.ReactNode };
type State = { hasError: boolean; info: string | null; errMsg: string | null };

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, info: null, errMsg: null };
  }
  static getDerivedStateFromError(error: unknown): State {
    return { hasError: true, info: null, errMsg: String(error) };
  }
  override componentDidCatch(error: unknown, info: React.ErrorInfo): void {
    try {
      const payload = {
        type: "react_error",
        message: String(error),
        stack: error instanceof Error ? error.stack || "" : "",
        componentStack: info.componentStack || "",
        ts: Date.now(),
      };
      if (navigator?.sendBeacon) {
        const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
        navigator.sendBeacon(`${API_URL}/metrics`, blob);
      } else {
        // fallback
        console.error("[ErrorBoundary]", payload);
      }
    } catch {}
  }
  handleRetry = () => {
    this.setState({ hasError: false, info: null, errMsg: null });
    // window.location.reload(); // opcional
  };
  override render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div className="simple-error-boundary">
          <div className="simple-error-boundary__card">
            <h1 className="simple-error-boundary__title">Algo salió mal</h1>
            <p className="simple-error-boundary__description">
              Se produjo un error al renderizar la interfaz.
            </p>
            {this.state.errMsg ? (
              <pre className="simple-error-boundary__pre">{this.state.errMsg}</pre>
            ) : null}
            <div className="simple-error-boundary__actions">
              <button onClick={this.handleRetry} className="simple-error-boundary__btn-primary">
                Reintentar
              </button>
              <button
                onClick={() => (window.location.href = "/")}
                className="simple-error-boundary__btn-secondary"
              >
                Ir al inicio
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
