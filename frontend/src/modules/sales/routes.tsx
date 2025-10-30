import React, { lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

const SalesDashboardPage = lazy(() => import("./pages/SalesDashboardPage"));
const POSPage = lazy(() => import("./pages/POSPage"));
const QuotesListPage = lazy(() => import("./pages/QuotesListPage"));
const QuoteDetailPage = lazy(() => import("./pages/QuoteDetailPage"));
const ReturnsListPage = lazy(() => import("./pages/ReturnsListPage"));
const ReturnDetailPage = lazy(() => import("./pages/ReturnDetailPage"));
const CashClosePage = lazy(() => import("./pages/CashClosePage"));
const CustomersListPage = lazy(() => import("./pages/CustomersListPage"));
const CustomerDetailPage = lazy(() => import("./pages/CustomerDetailPage"));

export default function SalesRoutes() {
  return (
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
  );
}
