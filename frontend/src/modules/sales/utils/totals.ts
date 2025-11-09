// [PACK22-POS-UTILS-START]
import type { CartLineInput, Totals, CheckoutRequest, PaymentInput } from "../../../services/sales";

export function calcTotalsLocal(lines: CartLineInput[], taxRate = 0): Totals {
  const sub = lines.reduce((s, l) => s + l.qty * l.price, 0);
  const disc = lines.reduce((s, l) => {
    if (!l.discount) return s;
    if (l.discount.type === "PERCENT") return s + (l.qty * l.price) * (l.discount.value / 100);
    return s + l.discount.value * l.qty;
  }, 0);
  const base = Math.max(sub - disc, 0);
  const tax = +(base * taxRate).toFixed(2);
  const grand = +(base + tax).toFixed(2);
  return { sub: +sub.toFixed(2), disc: +disc.toFixed(2), tax, grand };
}

export function paidAmount(payments: PaymentInput[], includeTips = false): number {
  const total = payments.reduce((s, p) => {
    const base = p.amount || 0;
    const tip = includeTips ? p.tipAmount || 0 : 0;
    return s + base + tip;
  }, 0);
  return +total.toFixed(2);
}

export function calcChange(grand: number, payments: PaymentInput[]): number {
  return +(paidAmount(payments) - grand).toFixed(2);
}

export function asCheckoutRequest(
  lines: CartLineInput[],
  payments: PaymentInput[],
  customerId?: string | null,
  coupons: string[] = [],
): CheckoutRequest {
  const payload: CheckoutRequest = {
type CheckoutOptions = {
  customerId?: string | null;
  docType?: "TICKET" | "INVOICE";
  note?: string | null;
};

export function asCheckoutRequest(
  lines: CartLineInput[],
  payments: PaymentInput[],
  options?: CheckoutOptions,
): CheckoutRequest {
  const payload: CheckoutRequest = {
    customerId: options?.customerId ?? null,
export function tipsTotal(payments: PaymentInput[]): number {
  return +payments.reduce((s, p) => s + (p.tipAmount || 0), 0).toFixed(2);
}

export function asCheckoutRequest(lines: CartLineInput[], payments: PaymentInput[], customerId?: string | null): CheckoutRequest {
  return {
    customerId: customerId ?? null,
    lines,
    payments,
    docType: options?.docType ?? "TICKET",
  };
  if (coupons.length) {
    payload.coupons = coupons;
  if (options?.note) {
    payload.note = options.note;
  }
  return payload;
}
// [PACK22-POS-UTILS-END]
