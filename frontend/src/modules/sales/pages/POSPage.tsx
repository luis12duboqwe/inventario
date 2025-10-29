import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  POSCartTable,
  POSCustomerPicker,
  POSDiscountModal,
  POSFiltersPanel,
  POSHoldOrdersDrawer,
  POSPaymentsModal,
  POSProductGrid,
  POSQuickActions,
  POSSearchBar,
  POSTotals,
  type CartItem,
  type Customer,
  type HoldOrder,
  type POSFilters,
  type ProductCard,
} from "../components/pos";

type HoldOrderRecord = HoldOrder & {
  items: CartItem[];
  customer?: Customer | null;
};

type ProductRecord = ProductCard & {
  category: string;
  brand: string;
  storeId: string;
  availability: "IN_STOCK" | "OUT_OF_STOCK";
};

const PRODUCT_CATALOG: ProductRecord[] = [
  {
    id: "p-1001",
    name: "iPhone 13 Pro",
    sku: "APL-IP13P-128",
    price: 27999,
    stock: 6,
    category: "Smartphone",
    brand: "Apple",
    storeId: "MX-001",
    availability: "IN_STOCK",
  },
  {
    id: "p-1002",
    name: "Samsung Galaxy S23",
    sku: "SMS-S23-256",
    price: 21499,
    stock: 4,
    category: "Smartphone",
    brand: "Samsung",
    storeId: "MX-001",
    availability: "IN_STOCK",
  },
  {
    id: "p-1003",
    name: "Xiaomi Redmi Note 12",
    sku: "XMI-RN12-128",
    price: 7299,
    stock: 15,
    category: "Smartphone",
    brand: "Xiaomi",
    storeId: "MX-002",
    availability: "IN_STOCK",
  },
  {
    id: "p-1004",
    name: "MacBook Air M2",
    sku: "APL-MBA-M2-13",
    price: 32999,
    stock: 2,
    category: "Laptop",
    brand: "Apple",
    storeId: "MX-001",
    availability: "IN_STOCK",
  },
  {
    id: "p-1005",
    name: "Lenovo ThinkPad X1",
    sku: "LNV-X1-14",
    price: 28999,
    stock: 0,
    category: "Laptop",
    brand: "Lenovo",
    storeId: "MX-003",
    availability: "OUT_OF_STOCK",
  },
  {
    id: "p-1006",
    name: "Apple Watch Series 9",
    sku: "APL-WATCH9-45",
    price: 11999,
    stock: 8,
    category: "Wearables",
    brand: "Apple",
    storeId: "MX-002",
    availability: "IN_STOCK",
  },
  {
    id: "p-1007",
    name: "Samsung Galaxy Watch 6",
    sku: "SMS-GW6-44",
    price: 8999,
    stock: 5,
    category: "Wearables",
    brand: "Samsung",
    storeId: "MX-003",
    availability: "IN_STOCK",
  },
  {
    id: "p-1008",
    name: "iPad Air 5",
    sku: "APL-IPAD-64",
    price: 18999,
    stock: 3,
    category: "Tablet",
    brand: "Apple",
    storeId: "MX-001",
    availability: "IN_STOCK",
  },
];

const SAMPLE_CUSTOMERS: Customer[] = [
  { id: "c-100", name: "Andrea Solís", phone: "+52 55 1000 1000", email: "andrea@empresa.mx" },
  { id: "c-200", name: "Corporativo Atlan", phone: "+52 55 2000 2000", email: "compras@atlan.mx" },
  { id: "c-300", name: "Luis Hernández", phone: "+52 55 3000 3000" },
];

const TAX_RATE = 0.16;

const filterCatalog = (query: string, filters: POSFilters): ProductCard[] => {
  const normalizedQuery = query.trim().toLowerCase();
  return PRODUCT_CATALOG.filter((product) => {
    if (filters.storeId && product.storeId !== filters.storeId) return false;
    if (filters.category && !product.category.toLowerCase().includes(filters.category.toLowerCase())) return false;
    if (filters.brand && !product.brand.toLowerCase().includes(filters.brand.toLowerCase())) return false;
    if (filters.availability && filters.availability !== "ALL" && product.availability !== filters.availability) return false;
    if (!normalizedQuery) return true;
    return (
      product.name.toLowerCase().includes(normalizedQuery) ||
      product.sku.toLowerCase().includes(normalizedQuery)
    );
  }).map(({ category: _category, brand: _brand, storeId: _store, availability: _availability, ...card }) => card);
};

function POSPage() {
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const [pendingQuery, setPendingQuery] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<POSFilters>({ availability: "ALL" });
  const [products, setProducts] = useState<ProductCard[]>(() => filterCatalog("", { availability: "ALL" }));
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [paymentsOpen, setPaymentsOpen] = useState(false);
  const [discountOpen, setDiscountOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [holdDrawerOpen, setHoldDrawerOpen] = useState(false);
  const [holdOrders, setHoldOrders] = useState<HoldOrderRecord[]>([]);
  const [customerCursor, setCustomerCursor] = useState(0);

  useEffect(() => {
    setLoadingProducts(true);
    const timer = window.setTimeout(() => {
      setProducts(filterCatalog(query, filters));
      setLoadingProducts(false);
    }, 120);
    return () => window.clearTimeout(timer);
  }, [query, filters]);

  const totals = useMemo(() => {
    const subtotal = cart.reduce((acc, item) => acc + item.price * item.qty, 0);
    const discountTotal = cart.reduce((acc, item) => acc + (item.discount ?? 0), 0);
    const taxableBase = Math.max(subtotal - discountTotal, 0);
    const taxTotal = taxableBase * TAX_RATE;
    const grandTotal = taxableBase + taxTotal;
    return { subtotal, discountTotal, taxTotal, grandTotal };
  }, [cart]);

  const focusSearch = useCallback(() => {
    if (searchInputRef.current) {
      searchInputRef.current.focus();
      searchInputRef.current.select();
    }
  }, []);

  const handleSearch = useCallback(() => {
    setQuery(pendingQuery);
  }, [pendingQuery]);

  const handleFiltersChange = useCallback((next: POSFilters) => {
    setFilters(next);
  }, []);

  const handlePickProduct = useCallback((id: string) => {
    const product = PRODUCT_CATALOG.find((item) => item.id === id);
    if (!product) return;
    setCart((prev) => {
      const exists = prev.find((item) => item.id === id);
      const maxStock = product.stock ?? Number.POSITIVE_INFINITY;
      if (exists) {
        if (exists.qty >= maxStock) {
          return prev;
        }
        return prev.map((item) =>
          item.id === id ? { ...item, qty: item.qty + 1 } : item
        );
      }
      if (maxStock <= 0) {
        return prev;
      }
      return [
        ...prev,
        {
          id: product.id,
          sku: product.sku,
          name: product.name,
          price: product.price,
          qty: 1,
        },
      ];
    });
  }, []);

  const handleInc = useCallback((id: string) => {
    const product = PRODUCT_CATALOG.find((item) => item.id === id);
    const maxStock = product?.stock ?? Number.POSITIVE_INFINITY;
    setCart((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        if (item.qty >= maxStock) return item;
        return { ...item, qty: item.qty + 1 };
      })
    );
  }, []);

  const handleDec = useCallback((id: string) => {
    setCart((prev) =>
      prev
        .map((item) => {
          if (item.id !== id) return item;
          const nextQty = Math.max(1, item.qty - 1);
          return { ...item, qty: nextQty };
        })
        .filter((item) => item.qty > 0)
    );
  }, []);

  const handleRemove = useCallback((id: string) => {
    setCart((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const handleClearCart = useCallback(() => {
    setCart([]);
    setCustomer(null);
    setEditingId(null);
  }, []);

  const handleEditDiscount = useCallback((id: string) => {
    setEditingId(id);
    setDiscountOpen(true);
  }, []);

  const editingDiscount = useMemo(() => {
    if (!editingId) return 0;
    return cart.find((item) => item.id === editingId)?.discount ?? 0;
  }, [cart, editingId]);

  const handleApplyDiscount = useCallback(
    (amount: number) => {
      setCart((prev) =>
        prev.map((item) => {
          if (item.id !== editingId) return item;
          const maxDiscount = item.price * item.qty;
          const sanitized = Math.max(0, Math.min(amount, maxDiscount));
          return { ...item, discount: sanitized };
        })
      );
      setDiscountOpen(false);
    },
    [editingId]
  );

  const handleOpenPayments = useCallback(() => {
    setPaymentsOpen(true);
  }, []);

  const handlePaymentSubmit = useCallback(() => {
    setPaymentsOpen(false);
    setCart([]);
    setCustomer(null);
  }, []);

  const handleToggleHold = useCallback(() => {
    setHoldDrawerOpen((prev) => !prev);
  }, []);

  const handleHold = useCallback(() => {
    if (!cart.length) return;
    const snapshot: HoldOrderRecord = {
      id: `H-${Date.now()}`,
      createdAt: new Date().toISOString(),
      customerName: customer?.name,
      total: totals.grandTotal,
      items: cart.map((item) => ({ ...item })),
      customer,
    };
    setHoldOrders((prev) => [...prev, snapshot]);
    setCart([]);
    setCustomer(null);
    setHoldDrawerOpen(true);
  }, [cart, customer, totals.grandTotal]);

  const handleResumeHold = useCallback(
    (id: string) => {
      const order = holdOrders.find((item) => item.id === id);
      if (!order) return;
      setCart(order.items.map((item) => ({ ...item })));
      setCustomer(order.customer ?? null);
      setHoldOrders((prev) => prev.filter((item) => item.id !== id));
      setHoldDrawerOpen(false);
    },
    [holdOrders]
  );

  const handleDeleteHold = useCallback((id: string) => {
    setHoldOrders((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const handlePickCustomer = useCallback(() => {
    const next = SAMPLE_CUSTOMERS[customerCursor % SAMPLE_CUSTOMERS.length];
    setCustomer(next);
    setCustomerCursor((prev) => prev + 1);
  }, [customerCursor]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "F1") {
        event.preventDefault();
        focusSearch();
      }
      if (event.key === "F2") {
        event.preventDefault();
        setPaymentsOpen(true);
      }
      if (event.key === "F3") {
        event.preventDefault();
        setHoldDrawerOpen((prev) => !prev);
      }
      if (event.key === "F4") {
        event.preventDefault();
        handleClearCart();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [focusSearch, handleClearCart]);

  const holdDrawerItems = useMemo<HoldOrder[]>(
    () => holdOrders.map(({ id, createdAt, customerName, total }) => ({ id, createdAt, customerName, total })),
    [holdOrders]
  );

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <POSSearchBar
        query={pendingQuery}
        onQueryChange={setPendingQuery}
        onSubmit={handleSearch}
        inputRef={searchInputRef}
      />
      <POSFiltersPanel value={filters} onChange={handleFiltersChange} />
      <POSQuickActions
        onFocusSearch={focusSearch}
        onOpenPayments={handleOpenPayments}
        onToggleHold={handleToggleHold}
        onClearCart={handleClearCart}
      />
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
        <POSProductGrid items={products} loading={loadingProducts} onPick={handlePickProduct} />
        <div style={{ display: "grid", gap: 12 }}>
          <POSCustomerPicker customer={customer} onPick={handlePickCustomer} onClear={() => setCustomer(null)} />
          <POSCartTable
            items={cart}
            onInc={handleInc}
            onDec={handleDec}
            onRemove={handleRemove}
            onEditDiscount={handleEditDiscount}
          />
          <POSTotals
            subtotal={totals.subtotal}
            discountTotal={totals.discountTotal}
            taxTotal={totals.taxTotal}
            grandTotal={totals.grandTotal}
            onCharge={handleOpenPayments}
            onHold={handleHold}
            onClear={handleClearCart}
          />
        </div>
      </div>

      <POSPaymentsModal
        open={paymentsOpen}
        amount={totals.grandTotal}
        onClose={() => setPaymentsOpen(false)}
        onSubmit={handlePaymentSubmit}
      />
      <POSDiscountModal
        open={discountOpen}
        current={editingDiscount}
        onClose={() => setDiscountOpen(false)}
        onApply={handleApplyDiscount}
      />
      <POSHoldOrdersDrawer
        open={holdDrawerOpen}
        items={holdDrawerItems}
        onClose={() => setHoldDrawerOpen(false)}
        onResume={handleResumeHold}
        onDelete={handleDeleteHold}
      />
    </div>
  );
}

export default POSPage;
