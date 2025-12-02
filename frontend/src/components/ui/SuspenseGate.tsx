// [PACK25-SUSPENSEGATE-START]
import React, { Suspense } from "react";

export function SuspenseGate({ fallback, children }: { fallback?: React.ReactNode; children: React.ReactNode }) {
  return <Suspense fallback={fallback ?? <div data-testid="skeleton">Cargando…</div>}>{children}</Suspense>;
}
// [PACK25-SUSPENSEGATE-END]
