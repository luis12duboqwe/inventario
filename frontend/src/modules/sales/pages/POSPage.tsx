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
  POSQuickScan,
} from "../components/pos";
// [PACK22-POS-PAGE-IMPORTS-START]
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Product, ProductSearchParams, PaymentInput } from "../../../services/sales";
import { SalesProducts } from "../../../services/sales";
import {
  getInventoryAvailability,
  type InventoryAvailabilityRecord,
} from "../../../api";
import { usePOS } from "../hooks/usePOS";
// [PACK22-POS-PAGE-IMPORTS-END]
import { calcTotalsLocal } from "../utils/totals";
// [PACK26-POS-PERMS-START]
import { useAuthz, PERMS } from "../../../auth/useAuthz";
import { logUI } from "../../../services/audit";
// [PACK26-POS-PERMS-END]
// [PACK27-PRINT-POS-IMPORT-START]
import { openPrintable } from "@/lib/print";
// [PACK27-PRINT-POS-IMPORT-END]

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

const buildAvailabilityReference = (product: Product): string => {
  const normalizedSku = product.sku?.trim().toLowerCase();
  if (normalizedSku) {
    return normalizedSku;
  }
  const numericId = Number(product.id);
  if (Number.isFinite(numericId)) {
    return `device:${Math.trunc(numericId)}`;
  }
  return String(product.id);
};

export default function POSPage() {
  type PaymentDraft = PaymentInput & { id: string };
  // [PACK26-POS-AUTHZ-STATE-START]
  const { user, can, hasAny } = useAuthz();
  // [PACK26-POS-AUTHZ-STATE-END]
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
  const [availabilityMap, setAvailabilityMap] = useState<Record<string, InventoryAvailabilityRecord>>({});
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
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

  const updateAvailabilityForProducts = useCallback(
    async (items: Product[]) => {
      const pendingSkus = new Set<string>();
      const pendingDeviceIds = new Set<number>();
      items.forEach((item) => {
        const normalizedSku = item.sku?.trim();
        if (normalizedSku) {
          const reference = normalizedSku.toLowerCase();
          if (!availabilityMap[reference]) {
            pendingSkus.add(normalizedSku);
          }
          return;
        }
        const numericId = Number(item.id);
        if (Number.isFinite(numericId)) {
          const reference = buildAvailabilityReference(item);
          if (!availabilityMap[reference]) {
            pendingDeviceIds.add(Math.trunc(numericId));
          }
        }
      });
      if (pendingSkus.size === 0 && pendingDeviceIds.size === 0) {
        return;
      }
      setAvailabilityLoading(true);
      try {
        const response = await getInventoryAvailability({
          skus: pendingSkus.size ? Array.from(pendingSkus) : undefined,
          deviceIds: pendingDeviceIds.size ? Array.from(pendingDeviceIds) : undefined,
          limit: Math.max(items.length, pendingSkus.size + pendingDeviceIds.size, 1),
        });
        setAvailabilityMap((prev) => {
          const next = { ...prev };
          response.items.forEach((entry) => {
            next[entry.reference] = entry;
          });
          return next;
        });
      } catch (error) {
        console.warn("No se pudo consultar disponibilidad corporativa", error);
      } finally {
        setAvailabilityLoading(false);
      }
    },
    [availabilityMap],
  );

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
      products.map((product) => {
        const card: React.ComponentProps<typeof ProductGrid>["items"][number] = {
          id: String(product.id),
          name: product.name,
          price: product.price,
        };

        if (product.sku !== undefined) {
          card.sku = product.sku;
        }

        if (product.stock !== undefined) {
          card.stock = product.stock;
        }

        if (product.imageUrl) {
          card.image = product.imageUrl;
        }

        return card;
      }),
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

  const cartLines = useMemo<React.ComponentProps<typeof CartPanel>["lines"]>(
    () =>
      lines.map((line) => {
        const cartLine: React.ComponentProps<typeof CartPanel>["lines"][number] = {
          id: String(line.productId),
          name: line.name ?? "Producto",
          qty: line.qty,
          price: line.price,
          discount: line.discount ?? null,
        };

        if (line.sku !== undefined) {
          cartLine.sku = line.sku;
        }

        if (line.imei !== undefined) {
          cartLine.imei = line.imei;
        }

        return cartLine;
      }),
    [lines],
  );

  const currentPrice = priceTarget
    ? lines.find((line) => String(line.productId) === priceTarget)?.price ?? 0
    : 0;

  // [PACK26-POS-AUDIT-START]
  async function onAfterCheckout(result: any) {
    const auditEvent: Parameters<typeof logUI>[0] = {
      ts: Date.now(),
      userId: user?.id ?? null,
      module: "POS",
      action: "checkout",
      meta: {
        total: result?.totals?.grand ?? 0,
        lines: lines.length,
      },
    };

    if (result?.saleId) {
      auditEvent.entityId = String(result.saleId);
    }

    await logUI(auditEvent);
  }

  async function onApplyDiscount(lineId: string, value: number, type: "PERCENT" | "AMOUNT") {
    await logUI({
      ts: Date.now(),
      userId: user?.id ?? null,
      module: "POS",
      action: "discount.apply",
      entityId: lineId,
      meta: { value, type },
    });
  }

  async function onHeld(holdId: string) {
    await logUI({
      ts: Date.now(),
      userId: user?.id ?? null,
      module: "POS",
      action: "hold.create",
      entityId: holdId,
    });
  }

  async function onResumed(holdId: string) {
    await logUI({
      ts: Date.now(),
      userId: user?.id ?? null,
      module: "POS",
      action: "hold.resume",
      entityId: holdId,
    });
  }
  // [PACK26-POS-AUDIT-END]

  const doSearch = useCallback(async (extra?: Partial<ProductSearchParams>) => {
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
      const items = Array.isArray(res.items) ? res.items : [];
      setProducts(items);
      void updateAvailabilityForProducts(items);
    } catch {
      // TODO(wire): manejar error de búsqueda
    } finally {
      setLoadingSearch(false);
    }
  }, [page, pageSize, q, updateAvailabilityForProducts]);

  function handleSearch(value: string) {
    setQ(value);
    setPage(1);
    doSearch({ q: value, page: 1 });
  }

  function onAddToCart(product: Product) {
    addProduct(product, 1);
  }

  const handleQuickScan = useCallback(
    async (code: string) => {
      const normalized = code.trim();
      if (!normalized) {
        throw new Error("Ingresa un código válido.");
      }

      const params: ProductSearchParams = {
        q: normalized,
        page: 1,
        pageSize: 1,
        onlyInStock: true,
        sku: normalized,
        imei: normalized,
      };

      let response;
      try {
        response = await SalesProducts.searchProducts(params);
      } catch {
        throw new Error("No se pudo consultar el catálogo.");
      }

      const items = Array.isArray(response.items) ? response.items : [];
      const candidate =
        items.find((item) => item.sku && item.sku.toLowerCase() === normalized.toLowerCase()) ||
        items[0];

      if (!candidate) {
        throw new Error("No se encontró ningún producto con ese código.");
      }

      onAddToCart(candidate);
      setQ(normalized);
      setPage(1);
      setProducts((prev) => {
        if (prev.some((item) => item.id === candidate.id)) {
          return prev;
        }
        return [candidate, ...prev];
      });

      void updateAvailabilityForProducts([candidate]);

      return { label: candidate.name };
    },
    [onAddToCart, setPage, setProducts, setQ, updateAvailabilityForProducts],
  );

  function handleQty(id: string, qty: number) {
    updateQty(id, Math.max(1, qty));
  }

  function handleRemove(id: string) {
    removeLine(id);
  }

  const handleDiscountSubmit = (payload: { type: "PERCENT" | "AMOUNT"; value: number }) => {
    if (!discountTarget) return;
    if (!can(PERMS.POS_DISCOUNT)) return;
    const normalized = payload.type === "PERCENT"
      ? Math.min(Math.max(payload.value, 0), 100)
      : Math.max(payload.value, 0);
    setDiscount(discountTarget, payload.type, normalized);
    void onApplyDiscount(discountTarget, normalized, payload.type);
    setDiscountTarget(null);
  };

  const handlePriceOverride = (newPrice: number) => {
    if (!priceTarget) return;
    if (!can(PERMS.POS_PRICE_OVERRIDE)) return;
    overridePrice(priceTarget, Math.max(newPrice, 0));
    setPriceTarget(null);
  };

  function onOpenPayments() {
    setPaymentsOpen(true);
  }

  const handlePaymentsSubmit = async (paymentDrafts: PaymentDraft[]) => {
    if (!can(PERMS.POS_CHECKOUT)) return;
    const payload: PaymentInput[] = paymentDrafts.map(({ type, amount, ref }) => {
      const payment: PaymentInput = { type, amount };
      if (ref !== undefined) {
        payment.ref = ref;
      }
      return payment;
    });
    setPayments(payload);
    try {
      const result = await checkout();
      await onAfterCheckout(result);
      // [PACK22-POS-PRINT-START]
      if (result?.printable?.pdfUrl) window.open(result.printable.pdfUrl, "_blank");
      else if (result?.printable?.html) {
        // TODO: implementar vista previa HTML
      }
      // [PACK27-PRINT-POS-START]
      if (result?.printable) {
        openPrintable(result.printable, "ticket");
      }
      // [PACK27-PRINT-POS-END]
      setCustomer(null);
    } finally {
      setPaymentsOpen(false);
    }
  };

  async function onHold() {
    if (!can(PERMS.POS_HOLD)) return;
    try {
      const holdId = await holdSale();
      if (holdId) {
        setHoldItems((prev) => {
          const next: HoldSale = {
            id: holdId,
            number: holdId,
            date: new Date().toISOString(),
            total: totals.grand,
          };

          if (customer?.name) {
            next.customer = customer.name;
          }

          return [...prev, next];
        });
        clearCart();
        setCustomer(null);
        setHoldDrawerOpen(false);
        await onHeld(holdId);
      }
    } catch {
      // errores manejados por banner POS
    }
  }

  async function onResumeHold(holdId: string) {
    if (!can(PERMS.POS_RESUME)) return;
    try {
      await resumeHold(holdId);
      setHoldItems((prev) => prev.filter((item) => item.id !== holdId));
      setHoldDrawerOpen(false);
      await onResumed(holdId);
    } catch {
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
  const didInitRef = useRef(false);
  useEffect(() => {
    if (didInitRef.current) return;
    didInitRef.current = true;
    void doSearch(); /* carga inicial */
  }, [doSearch]);
  // [PACK22-POS-SEARCH-INIT-END]

  // [PACK26-POS-GUARD-START]
  if (!can(PERMS.POS_VIEW)) {
    return <div>No autorizado</div>;
  }
  // [PACK26-POS-GUARD-END]

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
      {/* [PACK26-POS-HOLD-BUTTON-START] */}
      {hasAny([PERMS.POS_HOLD, PERMS.POS_RESUME]) ? (
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => setHoldDrawerOpen(true)} style={{ padding: "6px 10px", borderRadius: 8 }}>
            Ventas en espera
          </button>
        </div>
      ) : null}
      {/* [PACK26-POS-HOLD-BUTTON-END] */}
      <POSLayout
        left={
          <>
            <div style={{ display: "grid", gap: 10 }}>
              <POSQuickScan onSubmit={handleQuickScan} />
              <ProductSearchBar value={q} onChange={setQ} onSearch={handleSearch} />
            </div>
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
                availabilityByReference={availabilityMap}
                availabilityLoading={availabilityLoading}
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
          setCustomer(() => {
            const nextCustomer: Customer = { id: `fast-${Date.now()}`, name: payload.name };
            if (payload.phone) {
              nextCustomer.phone = payload.phone;
            }
            return nextCustomer;
          });
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
