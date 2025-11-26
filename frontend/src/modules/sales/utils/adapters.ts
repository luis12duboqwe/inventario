// [PACK23-UTILS-ADAPTERS-START]
import type { CartLineInput, Customer } from "../../../services/sales";

export function linesToTable(lines: CartLineInput[]) {
  return (lines || []).map((l) => ({
    id: `${l.productId}${l.imei ? ":"+l.imei : ""}`,
    name: l.name ?? l.productId,
    qty: l.qty,
    price: l.price,
    discount: l.discount ? (l.discount.type === "PERCENT" ? `${l.discount.value}%` : `-${l.discount.value}`) : "-",
    total: +(l.qty * l.price - (l.discount ? (l.discount.type === "PERCENT" ? (l.qty*l.price*l.discount.value/100) : (l.discount.value*l.qty)) : 0)).toFixed(2)
  }));
}

export function customerDisplay(c?: Customer | null) {
  if (!c) return "-";
  return `${c.name}${c.phone ? " · " + c.phone : ""}`;
}
// [PACK23-UTILS-ADAPTERS-END]
