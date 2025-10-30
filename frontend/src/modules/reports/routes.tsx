// [PACK29-*] Definición de rutas para reportes de ventas
import { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { SuspenseGate } from "@/ui/SuspenseGate";
import { ErrorBoundary } from "@/ui/ErrorBoundary";

const SalesReportsPage = lazy(() => import("./pages/SalesReportsPage"));

export default function ReportsRoutes() {
  // [PACK29-*] Enrutamiento interno del módulo de reportes
  return (
    <ErrorBoundary>
      <SuspenseGate
        fallback={
          <div style={{ padding: 16 }}>
            <h3>Cargando reportes de ventas…</h3>
          </div>
        }
      >
        <Routes>
          <Route index element={<SalesReportsPage />} />
          <Route path="*" element={<Navigate to="." replace />} />
        </Routes>
      </SuspenseGate>
    </ErrorBoundary>
  );
}
