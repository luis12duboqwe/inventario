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

export function paidAmount(payments: PaymentInput[]): number {
  return +payments.reduce((s, p) => s + (p.amount || 0), 0).toFixed(2);
}

export function calcChange(grand: number, payments: PaymentInput[]): number {
  return +(paidAmount(payments) - grand).toFixed(2);
}

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
    lines,
    payments,
    docType: options?.docType ?? "TICKET",
  };
  if (options?.note) {
    payload.note = options.note;
  }
  return payload;
}
// [PACK22-POS-UTILS-END]
