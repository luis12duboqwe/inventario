import React from "react";
import {
  CartPanel,
  CustomerBar,
  DiscountModal,
  FastCustomerModal,
  HoldResumeDrawer,
  OfflineQueueDrawer,
  POSActionsBar,
  POSLayout,
  PaymentsModal,
  PriceOverrideModal,
  ProductGrid,
  ProductSearchBar,
} from "../components/pos";
// [PACK22-POS-PAGE-IMPORTS-START]
import { useEffect, useMemo, useState } from "react";
import type { Product, ProductSearchParams, PaymentInput } from "../../../services/sales";
import { SalesProducts } from "../../../services/sales";
import { usePOS } from "../hooks/usePOS";
// [PACK22-POS-PAGE-IMPORTS-END]
import { calcTotalsLocal } from "../utils/totals";

type HoldSale = {
  id: string;
  number: string;
  date: string;
  customer?: string;
  total: number;
};

type OfflineSale = {
  id: string;
  when: string;
  total: number;
  status: "QUEUED" | "RETRYING" | "FAILED";
};

type Customer = {
  id: string;
  name: string;
  phone?: string;
};

export default function POSPage() {
  type PaymentDraft = PaymentInput & { id: string };
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [discountTarget, setDiscountTarget] = useState<string | null>(null);
  const [priceTarget, setPriceTarget] = useState<string | null>(null);
  const [paymentsOpen, setPaymentsOpen] = useState<boolean>(false);
  const [holdDrawerOpen, setHoldDrawerOpen] = useState<boolean>(false);
  const [fastCustomerOpen, setFastCustomerOpen] = useState<boolean>(false);
  const [offlineDrawerOpen, setOfflineDrawerOpen] = useState<boolean>(false);
  const [holdItems, setHoldItems] = useState<HoldSale[]>([]);
  // [PACK22-POS-SEARCH-STATE-START]
  const [q, setQ] = useState("");
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [page, setPage] = useState(1);
  const pageSize = 24; // ajusta a tu grid
  // [PACK22-POS-SEARCH-STATE-END]
  // [PACK22-POS-HOOK-USE-START]
  const pos = usePOS();

  const {
    lines,
    totals,
    payments,
    banner,
    pendingOffline,
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
    setCustomerId,
    setPayments,
    purgeOffline,
  } = pos;

  useEffect(() => {
    priceDraft();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lines, payments]);
  // [PACK22-POS-HOOK-USE-END]

  useEffect(() => {
    setCustomerId(customer?.id ?? null);
  }, [customer, setCustomerId]);

  const productCards = useMemo(
    () =>
      products.map((product) => ({
        id: String(product.id),
        sku: product.sku,
        name: product.name,
        price: product.price,
        stock: product.stock,
        image: product.imageUrl,
      })),
    [products],
  );

  const offlineQueue = useMemo<OfflineSale[]>(() => {
    return (pendingOffline as Array<{ ts: number; dto: any }>).map((item) => {
      const totalsDraft = calcTotalsLocal(item.dto?.lines ?? []);
      return {
        id: String(item.ts),
        when: new Date(item.ts).toISOString(),
        total: totalsDraft.grand,
        status: "QUEUED" as const,
      };
    });
  }, [pendingOffline]);

  const cartLines = useMemo(
    () =>
      lines.map((line) => ({
        id: String(line.productId),
        sku: line.sku,
        name: line.name ?? "Producto",
        qty: line.qty,
        price: line.price,
        discount: line.discount ?? null,
        imei: line.imei,
      })),
    [lines],
  );

  const currentPrice = priceTarget
    ? lines.find((line) => String(line.productId) === priceTarget)?.price ?? 0
    : 0;

  async function doSearch(extra?: Partial<ProductSearchParams>) {
    setLoadingSearch(true);
    try {
      const params: ProductSearchParams = {
        q,
        page,
        pageSize,
        onlyInStock: true,
        ...extra,
      } as ProductSearchParams;
      if (extra?.q !== undefined) {
        params.q = extra.q;
      }
      if (extra?.page !== undefined) {
        params.page = extra.page;
      }
      const res = await SalesProducts.searchProducts(params);
      setProducts(res.items ?? []);
    } catch (error) {
      // TODO(wire): manejar error de búsqueda
    } finally {
      setLoadingSearch(false);
    }
  }

  function handleSearch(value: string) {
    setQ(value);
    setPage(1);
    doSearch({ q: value, page: 1 });
  }

  function onAddToCart(product: Product) {
    addProduct(product, 1);
  }

  function handleQty(id: string, qty: number) {
    updateQty(id, Math.max(1, qty));
  }

  function handleRemove(id: string) {
    removeLine(id);
  }

  const handleDiscountSubmit = (payload: { type: "PERCENT" | "AMOUNT"; value: number }) => {
    if (!discountTarget) return;
    const normalized = payload.type === "PERCENT"
      ? Math.min(Math.max(payload.value, 0), 100)
      : Math.max(payload.value, 0);
    setDiscount(discountTarget, payload.type, normalized);
    setDiscountTarget(null);
  };

  const handlePriceOverride = (newPrice: number) => {
    if (!priceTarget) return;
    overridePrice(priceTarget, Math.max(newPrice, 0));
    setPriceTarget(null);
  };

  function onOpenPayments() {
    setPaymentsOpen(true);
  }

  const handlePaymentsSubmit = async (paymentDrafts: PaymentDraft[]) => {
    const payload: PaymentInput[] = paymentDrafts.map(({ type, amount, ref }) => ({ type, amount, ref }));
    setPayments(payload);
    try {
      const result = await checkout();
      // [PACK22-POS-PRINT-START]
      if (result?.printable?.pdfUrl) window.open(result.printable.pdfUrl, "_blank");
      else if (result?.printable?.html) {
        // TODO: implementar vista previa HTML
      }
      // [PACK22-POS-PRINT-END]
      setCustomer(null);
    } finally {
      setPaymentsOpen(false);
    }
  };

  async function onHold() {
    try {
      const holdId = await holdSale();
      if (holdId) {
        setHoldItems((prev) => [
          ...prev,
          {
            id: holdId,
            number: holdId,
            date: new Date().toISOString(),
            customer: customer?.name,
            total: totals.grand,
          },
        ]);
        clearCart();
        setCustomer(null);
        setHoldDrawerOpen(false);
      }
    } catch (error) {
      // errores manejados por banner POS
    }
  }

  async function onResumeHold(holdId: string) {
    try {
      await resumeHold(holdId);
      setHoldItems((prev) => prev.filter((item) => item.id !== holdId));
      setHoldDrawerOpen(false);
    } catch (error) {
      // errores manejados por banner POS
    }
  }

  const handleOfflineRetry = async () => {
    await retryOffline();
  };

  const handleOfflinePurge = (id?: string) => {
    purgeOffline(id);
  };

  function handleCancelSale() {
    clearCart();
    setPayments([]);
    setCustomer(null);
  }

  // [PACK22-POS-SEARCH-INIT-START]
  useEffect(() => { doSearch(); /* carga inicial */ }, []);
  // [PACK22-POS-SEARCH-INIT-END]

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {/* [PACK22-POS-BANNER-START] */}
      {banner && (
        <div
          style={{
            borderRadius: 12,
            padding: 12,
            border: "1px solid rgba(255,255,255,0.08)",
            background:
              banner.type === "error"
                ? "rgba(248,113,113,0.12)"
                : banner.type === "warn"
                ? "rgba(250,204,21,0.12)"
                : banner.type === "success"
                ? "rgba(34,197,94,0.12)"
                : "rgba(59,130,246,0.12)",
          }}
        >
          <div>{banner.msg}</div>
          {pendingOffline.length > 0 && (
            <button onClick={handleOfflineRetry} style={{ marginTop: 8, padding: "6px 10px", borderRadius: 8 }}>
              Reintentar ventas offline ({pendingOffline.length})
            </button>
          )}
        </div>
      )}
      {/* [PACK22-POS-BANNER-END] */}
      <CustomerBar
        customer={customer}
        onPick={() => {
          // TODO(wire)
        }}
        onQuickNew={() => setFastCustomerOpen(true)}
      />
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={() => setHoldDrawerOpen(true)} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Ventas en espera
        </button>
      </div>
      <POSLayout
        left={
          <>
            <ProductSearchBar value={q} onChange={setQ} onSearch={handleSearch} />
            {loadingSearch && (
              <div style={{ marginTop: 8, fontSize: 12, color: "#94a3b8" }}>Buscando productos…</div>
            )}
            <div style={{ marginTop: 10 }}>
              <ProductGrid
                items={productCards}
                onPick={(card) => {
                  const original = products.find((item) => String(item.id) === card.id);
                  if (original) {
                    onAddToCart(original);
                  }
                }}
              />
            </div>
          </>
        }
        right={
          <>
            <CartPanel
              lines={cartLines}
              totals={totals}
              onQty={handleQty}
              onRemove={handleRemove}
              onDiscount={(id) => setDiscountTarget(id)}
              onOverridePrice={(id) => setPriceTarget(id)}
            />
            <div style={{ marginTop: 10 }}>
              <POSActionsBar
                onHold={() => {
                  void onHold();
                }}
                onPay={onOpenPayments}
                onPrint={() => {
                  // TODO(wire): impresión directa
                }}
                onOffline={() => setOfflineDrawerOpen(true)}
                onCancel={handleCancelSale}
              />
            </div>
          </>
        }
      />
      <DiscountModal
        open={!!discountTarget}
        onClose={() => setDiscountTarget(null)}
        onSubmit={handleDiscountSubmit}
      />
      <PriceOverrideModal
        open={!!priceTarget}
        price={currentPrice}
        onClose={() => setPriceTarget(null)}
        onSubmit={handlePriceOverride}
      />
      <PaymentsModal
        open={paymentsOpen}
        total={totals.grand}
        onClose={() => setPaymentsOpen(false)}
        onSubmit={(paymentsDraft) => {
          void handlePaymentsSubmit(paymentsDraft as PaymentDraft[]);
        }}
      />
      <HoldResumeDrawer
        open={holdDrawerOpen}
        items={holdItems}
        onClose={() => setHoldDrawerOpen(false)}
        onResume={(id) => {
          void onResumeHold(id);
        }}
        onDelete={(id) => setHoldItems((prev) => prev.filter((item) => item.id !== id))}
      />
      <FastCustomerModal
        open={fastCustomerOpen}
        onClose={() => setFastCustomerOpen(false)}
        onSubmit={(payload) => {
          setCustomer({ id: `fast-${Date.now()}`, name: payload.name, phone: payload.phone });
          setFastCustomerOpen(false);
          // TODO(wire): creación inmediata de cliente
        }}
      />
      <OfflineQueueDrawer
        open={offlineDrawerOpen}
        items={offlineQueue}
        onClose={() => setOfflineDrawerOpen(false)}
        onRetry={() => {
          void handleOfflineRetry();
        }}
        onPurge={(id) => handleOfflinePurge(id)}
      />
    </div>
  );
}
