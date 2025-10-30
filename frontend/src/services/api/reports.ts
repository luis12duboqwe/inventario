// [PACK29-*] Cliente HTTP para los nuevos reportes de ventas
import httpClient from "./http";

export type SalesSummaryReport = {
  totalSales: number;
  totalOrders: number;
  avgTicket: number;
  returnsCount: number;
  net: number;
};

export type SalesByProductItem = {
  sku: string;
  name: string;
  qty: number;
  gross: number;
  net: number;
};

export type CashCloseReport = {
  opening: number;
  salesGross: number;
  refunds: number;
  expenses: number;
  closingSuggested: number;
};

export type SalesReportFilters = {
  from?: string;
  to?: string;
  branchId?: number;
  limit?: number;
};

export async function fetchSalesSummary(filters: SalesReportFilters): Promise<SalesSummaryReport> {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (typeof filters.branchId === "number") params.set("branchId", String(filters.branchId));
  const query = params.toString();
  const response = await httpClient.get<SalesSummaryReport>(
    query ? `/reports/sales/summary?${query}` : "/reports/sales/summary",
  );
  return response.data;
}

export async function fetchSalesByProduct(filters: SalesReportFilters): Promise<SalesByProductItem[]> {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (typeof filters.branchId === "number") params.set("branchId", String(filters.branchId));
  if (filters.limit) params.set("limit", String(filters.limit));
  const query = params.toString();
  const response = await httpClient.get<SalesByProductItem[]>(
    query ? `/reports/sales/by-product?${query}` : "/reports/sales/by-product",
  );
  return response.data;
}

export async function fetchCashCloseReport(filters: { date: string; branchId?: number }): Promise<CashCloseReport> {
  const params = new URLSearchParams();
  params.set("date", filters.date);
  if (typeof filters.branchId === "number") params.set("branchId", String(filters.branchId));
  const query = params.toString();
  const response = await httpClient.get<CashCloseReport>(
    query ? `/reports/cash-close?${query}` : "/reports/cash-close",
  );
  return response.data;
}
