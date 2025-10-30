import React, { useMemo, useState } from "react";
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

type CartLine = {
  id: string;
  sku?: string;
  name: string;
  qty: number;
  price: number;
  discount?: { type: "PERCENT" | "AMOUNT"; value: number } | null;
  imei?: string;
};

type Totals = {
  sub: number;
  disc: number;
  tax: number;
  grand: number;
};

type ProductRecord = {
  id: string;
  sku?: string;
  name: string;
  price: number;
  stock?: number;
  image?: string;
  imei?: string;
};

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

const TAX_RATE = 0.16;

const computeTotals = (items: CartLine[]): Totals => {
  const subtotal = items.reduce((acc, line) => acc + line.price * line.qty, 0);
  const discountTotal = items.reduce((acc, line) => {
    if (!line.discount) return acc;
    if (line.discount.type === "PERCENT") {
      return acc + (line.price * line.qty * Math.min(Math.max(line.discount.value, 0), 100)) / 100;
    }
    return acc + Math.max(line.discount.value, 0);
  }, 0);
  const taxableBase = Math.max(subtotal - discountTotal, 0);
  const taxTotal = taxableBase * TAX_RATE;
  return {
    sub: subtotal,
    disc: discountTotal,
    tax: taxTotal,
    grand: taxableBase + taxTotal,
  };
};

export default function POSPage() {
  const [query, setQuery] = useState<string>("");
  const [products] = useState<ProductRecord[]>([]); // TODO(wire)
  const [lines, setLines] = useState<CartLine[]>([]);
  const totals = useMemo(() => computeTotals(lines), [lines]);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [discountTarget, setDiscountTarget] = useState<string | null>(null);
  const [priceTarget, setPriceTarget] = useState<string | null>(null);
  const [paymentsOpen, setPaymentsOpen] = useState<boolean>(false);
  const [holdDrawerOpen, setHoldDrawerOpen] = useState<boolean>(false);
  const [fastCustomerOpen, setFastCustomerOpen] = useState<boolean>(false);
  const [offlineDrawerOpen, setOfflineDrawerOpen] = useState<boolean>(false);
  const [holdItems] = useState<HoldSale[]>([]); // TODO(wire)
  const [offlineQueue] = useState<OfflineSale[]>([]); // TODO(wire)

  const pickProduct = (product: ProductRecord) => {
    if (product.stock !== undefined && product.stock <= 0) {
      return; // TODO(alerta stock)
    }
    if (product.imei && lines.some((line) => line.imei === product.imei)) {
      return; // TODO(notificar duplicado IMEI)
    }
    setLines((prev) => {
      const existing = prev.find((line) => line.id === product.id);
      if (existing) {
        return prev.map((line) =>
          line.id === product.id
            ? { ...line, qty: line.qty + 1 }
            : line,
        );
      }
      return [
        ...prev,
        {
          id: product.id,
          sku: product.sku,
          name: product.name,
          qty: 1,
          price: product.price,
          imei: product.imei,
        },
      ];
    });
  };

  const updateQty = (id: string, qty: number) => {
    const safeQty = Number.isFinite(qty) && qty > 0 ? Math.floor(qty) : 1;
    setLines((prev) => prev.map((line) => (line.id === id ? { ...line, qty: safeQty } : line)));
  };

  const removeLine = (id: string) => {
    setLines((prev) => prev.filter((line) => line.id !== id));
  };

  const applyDiscount = (payload: { type: "PERCENT" | "AMOUNT"; value: number }) => {
    if (!discountTarget) return;
    setLines((prev) =>
      prev.map((line) =>
        line.id === discountTarget
          ? {
              ...line,
              discount: {
                type: payload.type,
                value: payload.type === "PERCENT" ? Math.min(Math.max(payload.value, 0), 100) : Math.max(payload.value, 0),
              },
            }
          : line,
      ),
    );
    setDiscountTarget(null);
  };

  const applyPriceOverride = (newPrice: number) => {
    if (!priceTarget) return;
    const safePrice = Math.max(newPrice, 0);
    setLines((prev) => prev.map((line) => (line.id === priceTarget ? { ...line, price: safePrice } : line)));
    setPriceTarget(null);
  };

  const currentPrice = priceTarget ? lines.find((line) => line.id === priceTarget)?.price ?? 0 : 0;

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <CustomerBar
        customer={customer}
        onPick={() => {
          // TODO(wire)
        }}
        onQuickNew={() => setFastCustomerOpen(true)}
      />
      <POSLayout
        left={
          <>
            <ProductSearchBar
              value={query}
              onChange={setQuery}
              onSearch={() => {
                // TODO(wire)
              }}
            />
            <div style={{ marginTop: 10 }}>
              <ProductGrid items={products} onPick={pickProduct} />
            </div>
          </>
        }
        right={
          <>
            <CartPanel
              lines={lines}
              totals={totals}
              onQty={updateQty}
              onRemove={removeLine}
              onDiscount={(id) => setDiscountTarget(id)}
              onOverridePrice={(id) => setPriceTarget(id)}
            />
            <div style={{ marginTop: 10 }}>
              <POSActionsBar
                onHold={() => setHoldDrawerOpen(true)}
                onPay={() => setPaymentsOpen(true)}
                onPrint={() => {
                  // TODO(print)
                }}
                onOffline={() => setOfflineDrawerOpen(true)}
                onCancel={() => {
                  setLines([]);
                  setCustomer(null);
                  // TODO(reset adicional)
                }}
              />
            </div>
          </>
        }
      />
      <DiscountModal
        open={!!discountTarget}
        onClose={() => setDiscountTarget(null)}
        onSubmit={applyDiscount}
      />
      <PriceOverrideModal
        open={!!priceTarget}
        price={currentPrice}
        onClose={() => setPriceTarget(null)}
        onSubmit={applyPriceOverride}
      />
      <PaymentsModal
        open={paymentsOpen}
        total={totals.grand}
        onClose={() => setPaymentsOpen(false)}
        onSubmit={() => {
          // TODO(checkout)
          setPaymentsOpen(false);
        }}
      />
      <HoldResumeDrawer
        open={holdDrawerOpen}
        items={holdItems}
        onClose={() => setHoldDrawerOpen(false)}
        onResume={() => {
          // TODO(resume)
        }}
        onDelete={() => {
          // TODO(delete)
        }}
      />
      <FastCustomerModal
        open={fastCustomerOpen}
        onClose={() => setFastCustomerOpen(false)}
        onSubmit={(payload) => {
          setCustomer({ id: `fast-${Date.now()}`, name: payload.name, phone: payload.phone });
          setFastCustomerOpen(false);
          // TODO(create/pick)
        }}
      />
      <OfflineQueueDrawer
        open={offlineDrawerOpen}
        items={offlineQueue}
        onClose={() => setOfflineDrawerOpen(false)}
        onRetry={() => {
          // TODO(retry)
        }}
        onPurge={() => {
          // TODO(purge)
        }}
      />
    </div>
  );
}
