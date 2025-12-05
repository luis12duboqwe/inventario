// [PACK29-*] Definición de rutas para reportes de ventas
import { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { SuspenseGate } from "@components/ui/SuspenseGate"; // [PACK37-frontend]
import AppErrorBoundary from "@components/ui/AppErrorBoundary"; // [PACK37-frontend]

const SalesReportsPage = lazy(() => import("./pages/SalesReportsPage"));

export default function ReportsRoutes() {
  // [PACK29-*] Enrutamiento interno del módulo de reportes
  return (
    <AppErrorBoundary variant="inline" title="Error en Reportes">
      <SuspenseGate
        fallback={
          <div className="p-4">
            <h3>Cargando reportes de ventas…</h3>
          </div>
        }
      >
        <Routes>
          <Route index element={<SalesReportsPage />} />
          <Route path="*" element={<Navigate to="." replace />} />
        </Routes>
      </SuspenseGate>
    </AppErrorBoundary>
  );
}
