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

export interface PosPromotionFeatureFlags {
  volume: boolean;
  combos: boolean;
  coupons: boolean;
}

export interface PosVolumePromotion {
  id: string;
  deviceId: number;
  minQuantity: number;
  discountPercent: number;
}

export interface PosComboPromotionItem {
  deviceId: number;
  quantity: number;
}

export interface PosComboPromotion {
  id: string;
  items: PosComboPromotionItem[];
  discountPercent: number;
}

export interface PosCouponPromotion {
  code: string;
  discountPercent: number;
  description?: string | null;
}

export interface PosPromotionsConfig {
  storeId: number;
  featureFlags: PosPromotionFeatureFlags;
  volumePromotions: PosVolumePromotion[];
  comboPromotions: PosComboPromotion[];
  coupons: PosCouponPromotion[];
  updatedAt?: string | null;
}

export type PosPromotionsUpdate = Omit<PosPromotionsConfig, "updatedAt">;

export interface PosPromotionsUpdateRequest {
  store_id: number;
  feature_flags: PosPromotionFeatureFlags;
  volume_promotions: Array<{
    id: string;
    device_id: number;
    min_quantity: number;
    discount_percent: number;
  }>;
  combo_promotions: Array<{
    id: string;
    discount_percent: number;
    items: Array<{
      device_id: number;
      quantity: number;
    }>;
  }>;
  coupons: Array<{
    code: string;
    discount_percent: number;
    description: string | null;
  }>;
}

export interface PosAppliedPromotion {
  id: string;
  promotionType: "volume" | "combo" | "coupon";
  description: string;
  discountPercent?: number | null;
  discountAmount?: number | null;
  affectedItems?: number[];
  couponCode?: string | null;
}

export type PaymentType = "CASH" | "CARD" | "TRANSFER" | "OTHER";
export interface PaymentInput {
  type: PaymentType;
  amount: number;
  reference?: string;
  tipAmount?: number;
  terminalId?: string;
  token?: string;
  metadata?: Record<string, string>;
}

export interface CheckoutRequest {
  customerId?: ID | null;
  lines: CartLineInput[];
  payments: PaymentInput[];
  docType?: "TICKET" | "INVOICE";
  note?: string;
  coupons?: string[];
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
  appliedPromotions?: PosAppliedPromotion[];
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
