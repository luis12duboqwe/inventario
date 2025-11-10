import type { CustomerLedgerEntry } from "../api";

export type CustomerFormState = {
  name: string;
  contactName: string;
  email: string;
  phone: string;
  address: string;
  customerType: string;
  status: string;
  taxId: string;
  segmentCategory: string;
  tags: string;
  creditLimit: number;
  outstandingDebt: number;
  notes: string;
  historyNote: string;
};

export type PortfolioFilters = {
  category: "delinquent" | "frequent";
  limit: number;
  dateFrom: string;
  dateTo: string;
};

export type DashboardFilters = {
  months: number;
  topLimit: number;
};

export type CustomerFilters = {
  search: string;
  status: string;
  customerType: string;
  debt: string;
  segmentCategory: string;
  tags: string;
};

export type LedgerEntryWithDetails = CustomerLedgerEntry & {
  detailsLabel?: string;
  detailsValue?: string;
};
