// src/services/sales/types.ts
import { ID, ListParams } from "../types/common";

export interface Money { currency?: string; amount: number; }

export interface Product {
  id: ID;
  sku?: string;
  name: string;
  price: number;
  stock?: number;
  imageUrl?: string;
  imeiManaged?: boolean; // teléfonos con IMEI
  attributes?: Record<string, string>; // color, GB, etc.
}

export interface ProductSearchParams extends ListParams {
  sku?: string;
  imei?: string;
  minPrice?: number;
  maxPrice?: number;
  onlyInStock?: boolean;
  category?: string;
}

export interface CartLineInput {
  productId: ID;
  name?: string;
  sku?: string;
  imei?: string;
  qty: number;
  price: number;
  discount?: { type: "PERCENT" | "AMOUNT"; value: number } | null;
}

export interface Totals {
  sub: number;    // suma de (qty*price)
  disc: number;   // total de descuentos
  tax: number;    // impuestos calculados
  grand: number;  // total final
}

export type PaymentType = "CASH" | "CARD" | "TRANSFER" | "OTHER";
export interface PaymentInput { type: PaymentType; amount: number; ref?: string; }

export interface CheckoutRequest {
  customerId?: ID | null;
  lines: CartLineInput[];
  payments: PaymentInput[];
  docType?: "TICKET" | "INVOICE";
  note?: string;
}

// [PACK27-PRINT-TYPES-START]
export interface PrintableResource {
  pdfUrl?: string;
  html?: string;
  plain?: string;
}
// [PACK27-PRINT-TYPES-END]

export interface CheckoutResponse {
  saleId: ID;
  number: string; // folio
  date: string;
  totals: Totals;
  // para impresión rápida
  printable?: PrintableResource | null;
}

export interface ReceiptDeliveryPayload {
  channel: "email" | "whatsapp";
  recipient: string;
  message?: string;
  subject?: string;
}

export interface ReceiptDeliveryResponse {
  channel: "email" | "whatsapp";
  status: string;
}

export interface Quote {
  id: ID;
  number: string;
  date: string;
  customerId?: ID | null;
  customerName?: string;
  lines: CartLineInput[];
  totals: Totals;
  note?: string;
  status: "OPEN" | "APPROVED" | "EXPIRED" | "CONVERTED";
  printable?: PrintableResource | null;
}
export interface QuoteListParams extends ListParams { dateFrom?: string; dateTo?: string; status?: Quote["status"]; }
export type QuoteCreate = Omit<Quote, "id" | "number" | "date" | "status" | "totals"> & { note?: string };

export interface ReturnLine { productId: ID; name: string; qty: number; price: number; imei?: string; restock?: boolean; }
export interface ReturnDoc {
  id: ID;
  number: string;
  date: string;
  reason: "DEFECT" | "BUYER_REMORSE" | "WARRANTY" | "OTHER";
  lines: ReturnLine[];
  totalCredit: number;
  customerName?: string;
  printable?: PrintableResource | null;
}
export interface ReturnListParams extends ListParams { dateFrom?: string; dateTo?: string; reason?: ReturnDoc["reason"]; }
export interface ReturnCreate { reason: ReturnDoc["reason"]; note?: string; lines: ReturnLine[]; ticketNumber?: string; }

export interface Customer {
  id: ID;
  name: string;
  phone?: string;
  email?: string;
  tier?: string;     // STANDARD/VIP, etc.
  tags?: string[];
  notes?: string;
  lastSaleAt?: string;
  createdAt?: string;
}
export interface CustomerListParams extends ListParams { tag?: string; tier?: string; }

export interface CashSummary {
  date: string;
  theoretical: { cash: number; card: number; transfer: number; other: number; total: number };
  counted?:    { cash: number; card: number; transfer: number; other: number; total: number };
  differences?:{ cash: number; card: number; transfer: number; other: number; total: number };
}
export interface CashClosePayload {
  date: string;
  counted: { cash: number; card: number; transfer: number; other: number; total: number };
  note?: string;
}
