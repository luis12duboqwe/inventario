import React from "react";

type Props = { children: React.ReactNode };
type State = { hasError: boolean; info?: string; errMsg?: string };

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(error: unknown): State {
    return { hasError: true, errMsg: String(error) };
  }
  componentDidCatch(error: unknown, info: React.ErrorInfo) {
    try {
      const payload = {
        type: "react_error",
        message: String(error),
        stack: (error as any)?.stack || "",
        componentStack: info?.componentStack || "",
        ts: Date.now(),
      };
      if (navigator?.sendBeacon) {
        const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
        navigator.sendBeacon("/api/metrics", blob);
      } else {
        // fallback
        console.error("[ErrorBoundary]", payload);
      }
    } catch {}
  }
  handleRetry = () => {
    this.setState({ hasError: false, info: undefined, errMsg: undefined });
    // window.location.reload(); // opcional
  };
  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "grid",
            placeItems: "center",
            background: "#0b1220",
            color: "#cbd5e1",
            padding: 24,
          }}
        >
          <div style={{ maxWidth: 560, textAlign: "center" }}>
            <h1 style={{ margin: "8px 0 4px" }}>Algo salió mal</h1>
            <p style={{ margin: 0, color: "#94a3b8" }}>
              Se produjo un error al renderizar la interfaz.
            </p>
            {this.state.errMsg ? (
              <pre
                style={{
                  textAlign: "left",
                  whiteSpace: "pre-wrap",
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 12,
                  padding: 12,
                  marginTop: 12,
                }}
              >
                {this.state.errMsg}
              </pre>
            ) : null}
            <div
              style={{
                display: "flex",
                gap: 8,
                justifyContent: "center",
                marginTop: 16,
              }}
            >
              <button
                onClick={this.handleRetry}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: "#2563eb",
                  color: "#fff",
                  border: 0,
                }}
              >
                Reintentar
              </button>
              <button
                onClick={() => (window.location.href = "/")}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.08)",
                  color: "#e5e7eb",
                  border: 0,
                }}
              >
                Ir al inicio
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children as React.ReactElement;
  }
}

export default ErrorBoundary;
