// [PACK25-LAZY-IMPORTS-START]
import React, { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { SuspenseGate } from "@/ui/SuspenseGate"; // [PACK37-frontend]
import { ErrorBoundary } from "@/ui/ErrorBoundary"; // [PACK37-frontend]

const SalesDashboardPage = lazy(() => import("./pages/SalesDashboardPage"));
const POSPage = lazy(() => import("./pages/POSPage"));
const QuotesListPage = lazy(() => import("./pages/QuotesListPage"));
const QuoteDetailPage = lazy(() => import("./pages/QuoteDetailPage"));
const ReturnsListPage = lazy(() => import("./pages/ReturnsListPage"));
const ReturnDetailPage = lazy(() => import("./pages/ReturnDetailPage"));
const CustomersListPage = lazy(() => import("./pages/CustomersListPage"));
const CustomerDetailPage = lazy(() => import("./pages/CustomerDetailPage"));
const CashClosePage = lazy(() => import("./pages/CashClosePage"));
// [PACK25-LAZY-IMPORTS-END]

export default function SalesRoutes() {
  // [PACK25-LAZY-ROUTES-START]
  return (
    <ErrorBoundary>
      <SuspenseGate fallback={<div style={{ padding: 16 }}><h3>Cargando Ventas…</h3></div>}>
        <Routes>
          <Route index element={<SalesDashboardPage />} />
          <Route path="pos" element={<POSPage />} />
          <Route path="quotes" element={<QuotesListPage />} />
          <Route path="quotes/:id" element={<QuoteDetailPage />} />
          <Route path="returns" element={<ReturnsListPage />} />
          <Route path="returns/:id" element={<ReturnDetailPage />} />
          <Route path="customers" element={<CustomersListPage />} />
          <Route path="customers/:id" element={<CustomerDetailPage />} />
          <Route path="cash-close" element={<CashClosePage />} />
          <Route path="*" element={<Navigate to="." replace />} />
        </Routes>
      </SuspenseGate>
    </ErrorBoundary>
  );
  // [PACK25-LAZY-ROUTES-END]
}
