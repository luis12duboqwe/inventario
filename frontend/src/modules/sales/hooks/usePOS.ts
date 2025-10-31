// [PACK22-POS-HOOK-START]
import { useCallback, useRef, useState } from "react";
import type { CartLineInput, Product, PaymentInput, Totals } from "../../../services/sales";
import { calcTotalsLocal, asCheckoutRequest } from "../utils/totals";
import { SalesPOS } from "../../../services/sales";

export type PosBanner = { type: "info"|"warn"|"error"|"success"; msg: string };

export function usePOS() {
  const [lines, setLines] = useState<CartLineInput[]>([]);
  const [customerId, setCustomerId] = useState<string | null>(null);
  const [payments, setPayments] = useState<PaymentInput[]>([]);
  const [totals, setTotals] = useState<Totals>(() => calcTotalsLocal([]));
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<PosBanner | null>(null);
  type OfflineItem = { ts: number; dto: any };
  const [pendingOffline, setPendingOffline] = useState<OfflineItem[]>(() => {
    try { return JSON.parse(localStorage.getItem("sm_offline_sales") || "[]") as OfflineItem[]; }
    catch { return []; }
  });

  const taxRateRef = useRef(0); // TODO(map): si backend devuelve impuesto, sincronizar

  const refreshTotalsLocal = useCallback(() => {
    setTotals(calcTotalsLocal(lines, taxRateRef.current));
  }, [lines]);

  const addProduct = useCallback((p: Product, qty = 1) => {
    setLines(curr => {
      const i = curr.findIndex(l => l.productId === p.id && !l.imei);
      if (i >= 0) {
        const copy = curr.slice();
        copy[i] = { ...copy[i], qty: copy[i].qty + qty };
        return copy;
      }
      return [...curr, { productId: p.id, name: p.name, sku: p.sku, qty, price: p.price, discount: null }];
    });
  }, []);

  const updateQty = useCallback((productId: string, qty: number) => {
    setLines(curr => curr.map(l => l.productId === productId ? { ...l, qty } : l));
  }, []);

  const removeLine = useCallback((productId: string) => {
    setLines(curr => curr.filter(l => l.productId !== productId));
  }, []);

  const setDiscount = useCallback((productId: string, type: "PERCENT"|"AMOUNT", value: number) => {
    setLines(curr => curr.map(l => l.productId === productId ? { ...l, discount: { type, value } } : l));
  }, []);

  const overridePrice = useCallback((productId: string, price: number) => {
    setLines(curr => curr.map(l => l.productId === productId ? { ...l, price } : l));
  }, []);

  const clearCart = useCallback(() => setLines([]), []);

  const priceDraft = useCallback(async () => {
    // Cálculo local inmediato para UX responsiva
    refreshTotalsLocal();

    // Ajuste con backend (si está disponible)
    try {
      setLoading(true);
      const dto = asCheckoutRequest(lines, payments, customerId ?? undefined);
      const t = await SalesPOS.priceDraft(dto);
      setTotals(t);
    } catch (e: any) {
      // Silencioso: el cálculo local mantiene la UI operativa
      // eslint-disable-next-line no-console
      console.warn("priceDraft fallback local", e);
      setBanner({ type: "warn", msg: "No fue posible sincronizar totales con el servidor (usando cálculo local)." });
    } finally {
      setLoading(false);
    }
  }, [lines, payments, customerId, refreshTotalsLocal]);

  const holdSale = useCallback(async () => {
    const dto = asCheckoutRequest(lines, payments, customerId ?? undefined);
    setLoading(true);
    try {
      const r = await SalesPOS.holdSale(dto);
      setBanner({ type: "success", msg: `Venta en espera guardada (#${r.holdId}).` });
      return r.holdId;
    } catch (e: any) {
      setBanner({ type: "error", msg: "No se pudo guardar venta en espera." });
      throw e;
    } finally {
      setLoading(false);
    }
  }, [lines, payments, customerId]);

  const resumeHold = useCallback(async (holdId: string) => {
    setLoading(true);
    try {
      const dto = await SalesPOS.resumeHold(holdId);
      setLines(dto.lines || []);
      setPayments(dto.payments || []);
      setCustomerId(dto.customerId || null);
      await priceDraft();
    } catch (e: any) {
      setBanner({ type: "error", msg: "No se pudo recuperar venta en espera." });
      throw e;
    } finally {
      setLoading(false);
    }
  }, [priceDraft]);

  const checkout = useCallback(async () => {
    const dto = asCheckoutRequest(lines, payments, customerId ?? undefined);
    setLoading(true);
    try {
      const r = await SalesPOS.checkout(dto);
      clearCart();
      setPayments([]);
      setBanner({ type: "success", msg: `Venta #${r.number} realizada.` });
      return r;
    } catch (e: any) {
      // Offline mínimo: guardar intento en localStorage para reintentar
      try {
        const q = JSON.parse(localStorage.getItem("sm_offline_sales") || "[]") as OfflineItem[];
        q.push({ ts: Date.now(), dto });
        localStorage.setItem("sm_offline_sales", JSON.stringify(q));
        setPendingOffline(q);
        setBanner({ type: "warn", msg: "Sin conexión. Venta en cola offline para reintento." });
      } catch {}
      throw e;
    } finally {
      setLoading(false);
    }
  }, [lines, payments, customerId, clearCart]);

  const retryOffline = useCallback(async () => {
    const raw = localStorage.getItem("sm_offline_sales");
    if (!raw) return 0;
    const queue = JSON.parse(raw) as OfflineItem[];
    let ok = 0, left: OfflineItem[] = [];
    for (const item of queue) {
      try { await SalesPOS.checkout(item.dto); ok++; }
      catch { left.push(item); }
    }
    localStorage.setItem("sm_offline_sales", JSON.stringify(left));
    setPendingOffline(left);
    setBanner({ type: "info", msg: `Reintentos OK: ${ok}. Pendientes: ${left.length}.` });
    return ok;
  }, []);

  const purgeOffline = useCallback((id?: string | number) => {
    const raw = localStorage.getItem("sm_offline_sales");
    if (!raw) {
      setPendingOffline([]);
      return [] as OfflineItem[];
    }
    const queue = JSON.parse(raw) as OfflineItem[];
    const filtered = typeof id === "undefined"
      ? []
      : queue.filter(item => String(item.ts) !== String(id));
    localStorage.setItem("sm_offline_sales", JSON.stringify(filtered));
    setPendingOffline(filtered);
    return filtered;
  }, []);

  return {
    lines, payments, totals, loading, banner, customerId, pendingOffline,
    setCustomerId, setPayments,
    addProduct, updateQty, removeLine, setDiscount, overridePrice, clearCart,
    priceDraft, checkout, holdSale, resumeHold, retryOffline, purgeOffline,
  };
}
// [PACK22-POS-HOOK-END]
