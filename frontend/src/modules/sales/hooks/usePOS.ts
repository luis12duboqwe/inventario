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
  const [coupons, setCoupons] = useState<string[]>([]);
  const [totals, setTotals] = useState<Totals>(() => calcTotalsLocal([]));
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<PosBanner | null>(null);
  const [docType, setDocType] = useState<"TICKET" | "INVOICE">("TICKET");
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
    setLines((curr) => {
      const index = curr.findIndex((line) => line.productId === p.id && !line.imei);
      if (index >= 0) {
        const copy = curr.slice();
        const existing = copy[index];
        if (!existing) {
          return curr;
        }
        copy[index] = { ...existing, qty: existing.qty + qty };
        return copy;
      }
      const nextLine: CartLineInput = {
        productId: p.id,
        name: p.name,
        qty,
        price: p.price,
        discount: null,
      };
      if (p.sku) {
        nextLine.sku = p.sku;
      }
      return [...curr, nextLine];
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
      const dto = asCheckoutRequest(lines, payments, customerId ?? undefined, coupons);
      const dto = asCheckoutRequest(lines, payments, {
        customerId: customerId ?? undefined,
        docType,
      });
      const t = await SalesPOS.priceDraft(dto);
      setTotals(t);
    } catch (e: any) {
      // Silencioso: el cálculo local mantiene la UI operativa
  console.warn("priceDraft fallback local", e);
      setBanner({ type: "warn", msg: "No fue posible sincronizar totales con el servidor (usando cálculo local)." });
    } finally {
      setLoading(false);
    }
  }, [lines, payments, customerId, coupons, refreshTotalsLocal]);

  const holdSale = useCallback(async () => {
    const dto = asCheckoutRequest(lines, payments, customerId ?? undefined, coupons);
  }, [lines, payments, customerId, docType, refreshTotalsLocal]);

  const holdSale = useCallback(async () => {
    const dto = asCheckoutRequest(lines, payments, {
      customerId: customerId ?? undefined,
      docType,
    });
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
  }, [lines, payments, customerId, coupons]);
  }, [lines, payments, customerId, docType]);

  const resumeHold = useCallback(async (holdId: string) => {
    setLoading(true);
    try {
      const dto = await SalesPOS.resumeHold(holdId);
      setLines(dto.lines || []);
      setPayments(dto.payments || []);
      setCustomerId(dto.customerId || null);
      setCoupons(dto.coupons || []);
      if (dto.docType) {
        setDocType(dto.docType);
      }
      await priceDraft();
    } catch (e: any) {
      setBanner({ type: "error", msg: "No se pudo recuperar venta en espera." });
      throw e;
    } finally {
      setLoading(false);
    }
  }, [priceDraft]);

  const checkout = useCallback(async () => {
    const dto = asCheckoutRequest(lines, payments, customerId ?? undefined, coupons);
    const dto = asCheckoutRequest(lines, payments, {
      customerId: customerId ?? undefined,
      docType,
    });
    setLoading(true);
    try {
      const r = await SalesPOS.checkout(dto);
      clearCart();
      setPayments([]);
      setCoupons([]);
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
  }, [lines, payments, customerId, coupons, clearCart]);
  }, [lines, payments, customerId, docType, clearCart]);

  const retryOffline = useCallback(async () => {
    const raw = localStorage.getItem("sm_offline_sales");
    if (!raw) return 0;
  const queue = JSON.parse(raw) as OfflineItem[];
  let ok = 0; const left: OfflineItem[] = [];
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

  const pushBanner = useCallback((entry: PosBanner | null) => setBanner(entry), []);

  return {
    lines, payments, totals, loading, banner, customerId, pendingOffline, coupons,
    setCustomerId, setPayments, setCoupons,
    addProduct, updateQty, removeLine, setDiscount, overridePrice, clearCart,
    priceDraft, checkout, holdSale, resumeHold, retryOffline, purgeOffline,
    lines,
    payments,
    totals,
    loading,
    banner,
    customerId,
    pendingOffline,
    docType,
    setCustomerId,
    setPayments,
    setDocType,
    addProduct,
    updateQty,
    removeLine,
    setDiscount,
    overridePrice,
    clearCart,
    priceDraft,
    checkout,
    holdSale,
    resumeHold,
    retryOffline,
    purgeOffline,
    pushBanner,
  };
}
// [PACK22-POS-HOOK-END]
