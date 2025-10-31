// [PACK25-ERRORBOUNDARY-START]
import React from "react";
type State = { hasError: boolean; error?: any };

export class ErrorBoundary extends React.Component<{fallback?: (e:any)=>React.ReactNode}, State> {
  state: State = { hasError: false };
  static getDerivedStateFromError(error: any){ return { hasError: true, error }; }
  componentDidCatch(error:any, info:any){ /* opcional: log */ }
  render(){
    if (this.state.hasError) return this.props.fallback?.(this.state.error) ?? <div>Ocurrió un error.</div>;
    return this.props.children as any;
  }
}
// [PACK25-ERRORBOUNDARY-END]
