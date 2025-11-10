import type { CustomerLedgerEntry } from "../api";

export type CustomerFormState = {
  name: string;
  contactName: string;
  email: string;
  phone: string;
  address: string;
  customerType: string;
  status: string;
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
};

export type LedgerEntryWithDetails = CustomerLedgerEntry & {
  detailsLabel?: string;
  detailsValue?: string;
};

export type SegmentExportChannel = "Mailchimp" | "SMS" | "Archivo";

export type CustomerSegmentDefinition = {
  key: string;
  label: string;
  description: string;
  channel: SegmentExportChannel;
};
