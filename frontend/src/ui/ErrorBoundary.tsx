// [PACK25-ERRORBOUNDARY-START]
import React from "react";

type ErrorBoundaryProps = React.PropsWithChildren<{ fallback?: (error: unknown) => React.ReactNode }>;
type State = { hasError: boolean; error: unknown };

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, State> {
  override state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: unknown): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: unknown): void {
    console.error("[UI ErrorBoundary]", error);
  }

  override render(): React.ReactNode {
    if (this.state.hasError) {
      return this.props.fallback?.(this.state.error) ?? <div>Ocurrió un error.</div>;
    }
    return this.props.children;
  }
}
// [PACK25-ERRORBOUNDARY-END]
