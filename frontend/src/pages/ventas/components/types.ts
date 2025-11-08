import type { Customer, Device, Sale, Store, UserAccount } from "../../../api";

export type SaleLine = {
  device: Device;
  quantity: number;
  batchCode: string;
};

export type SaleFormState = {
  storeId: number | null;
  paymentMethod: Sale["payment_method"];
  discountPercent: number;
  customerId: number | null;
  customerName: string;
  notes: string;
  reason: string;
};

export type SalesFilterState = {
  storeId: number | null;
  customerId: number | null;
  userId: number | null;
  dateFrom: string;
  dateTo: string;
  query: string;
};

export type SaleSummary = {
  gross: number;
  discount: number;
  subtotal: number;
  taxAmount: number;
  total: number;
  taxRate: number;
};

export type SalesDashboard = {
  total: number;
  subtotal: number;
  tax: number;
  count: number;
  average: number;
  dailyStats: Array<{
    day: string;
    total: number;
    count: number;
    average: number;
  }>;
};

export type SalesFiltersProps = {
  stores: Store[];
  customers: Customer[];
  users: UserAccount[];
  filters: SalesFilterState;
  exportReason: string;
  isExporting: boolean;
  onFiltersChange: (changes: Partial<SalesFilterState>) => void;
  onExportReasonChange: (value: string) => void;
  onExportPdf: () => void;
  onExportExcel: () => void;
  onClearFilters: () => void;
};
