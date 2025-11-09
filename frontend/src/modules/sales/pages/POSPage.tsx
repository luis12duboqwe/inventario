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
import type {
  Product,
  ProductSearchParams,
  PaymentInput,
  PosPromotionsConfig,
  PosPromotionsUpdateRequest,
} from "../../../services/sales";
import { SalesProducts, SalesPOS } from "../../../services/sales";
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
  email?: string;
  docId?: string;
};

type TerminalOption = {
  id: string;
  label: string;
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
  const [selectedStoreId, setSelectedStoreId] = useState<string>("1");
  const [promotionsConfig, setPromotionsConfig] = useState<PosPromotionsConfig | null>(null);
  const [promotionsDraft, setPromotionsDraft] = useState<PosPromotionsConfig | null>(null);
  const [promotionsLoading, setPromotionsLoading] = useState(false);
  const [promotionsError, setPromotionsError] = useState<string | null>(null);
  const [promotionsEditorOpen, setPromotionsEditorOpen] = useState(false);
  const [volumeForm, setVolumeForm] = useState({ id: "", deviceId: "", minQuantity: "", discountPercent: "" });
  const [comboForm, setComboForm] = useState({ id: "", deviceIds: "", discountPercent: "" });
  const [couponForm, setCouponForm] = useState({ code: "", discountPercent: "", description: "" });
  const [couponInput, setCouponInput] = useState("");

  const editorInputStyle: React.CSSProperties = {
    padding: "6px 10px",
    borderRadius: 8,
    background: "rgba(15,23,42,0.85)",
    border: "1px solid rgba(148,163,184,0.25)",
    color: "#e2e8f0",
    minWidth: 110,
  };
  const secondaryButtonStyle: React.CSSProperties = {
    padding: "6px 12px",
    borderRadius: 8,
    border: "1px solid rgba(59,130,246,0.35)",
    background: "rgba(30,41,59,0.8)",
    color: "#e2e8f0",
  };
  const primaryButtonStyle: React.CSSProperties = {
    padding: "6px 16px",
    borderRadius: 8,
    border: "none",
    background: "linear-gradient(90deg, rgba(56,189,248,0.8), rgba(14,165,233,0.85))",
    color: "#0f172a",
    fontWeight: 600,
  };
  const [lastSale, setLastSale] = useState<{ id: string; number: string; receiptUrl?: string | null } | null>(null);
  const [lastSaleContact, setLastSaleContact] = useState<{ email?: string; phone?: string; docId?: string; name?: string } | null>(null);
  const [sendingChannel, setSendingChannel] = useState<"email" | "whatsapp" | null>(null);
  const terminalOptions = useMemo<TerminalOption[]>(
    () => [
      { id: "atl-01", label: "Terminal Atlántida" },
      { id: "fic-01", label: "Terminal Ficohsa" },
    ],
    [],
  );
  const [selectedTerminal, setSelectedTerminal] = useState<string | undefined>(
    () => terminalOptions[0]?.id,
  );
  const [tipSuggestions, setTipSuggestions] = useState<number[]>(() => {
    if (typeof window === "undefined") {
      return [0, 5, 10];
    }
    try {
      const stored = localStorage.getItem("sm_pos_tip_suggestions");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          const values = parsed
            .map((value) => Number(value))
            .filter((value) => Number.isFinite(value) && value >= 0);
          if (values.length > 0) {
            return values;
          }
        }
      }
    } catch (error) {
      console.warn("No se pudieron cargar propinas configuradas", error);
    }
    return [0, 5, 10];
  });
  const [tipPresetInput, setTipPresetInput] = useState<string>(() => tipSuggestions.join(", "));
  useEffect(() => {
    setTipPresetInput(tipSuggestions.join(", "));
    if (typeof window !== "undefined") {
      localStorage.setItem("sm_pos_tip_suggestions", JSON.stringify(tipSuggestions));
    }
  }, [tipSuggestions]);
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
    docType,
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
    coupons: appliedCoupons,
    setCoupons: setAppliedCoupons,
    setDocType,
    pushBanner,
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

  useEffect(() => {
    void priceDraft();
  }, [appliedCoupons, priceDraft]);
    setDocType(customer?.docId ? "INVOICE" : "TICKET");
  }, [customer, setDocType]);

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

  const fetchPromotions = useCallback(async (storeNumeric: number) => {
    try {
      setPromotionsLoading(true);
      const data = await SalesPOS.getPromotions(storeNumeric);
      const featureFlagsSource: any = (data as any).featureFlags ?? (data as any).feature_flags ?? {};
      const volumeSource: any[] = (data as any).volumePromotions ?? (data as any).volume_promotions ?? [];
      const comboSource: any[] = (data as any).comboPromotions ?? (data as any).combo_promotions ?? [];
      const couponSource: any[] = (data as any).coupons ?? [];
      const normalized: PosPromotionsConfig = {
        storeId: (data as any).storeId ?? (data as any).store_id ?? storeNumeric,
        featureFlags: {
          volume: Boolean(featureFlagsSource.volume),
          combos: Boolean(featureFlagsSource.combos),
          coupons: Boolean(featureFlagsSource.coupons),
        },
        volumePromotions: volumeSource.map((rule) => ({
          id: String(rule.id ?? ""),
          deviceId: Number(rule.deviceId ?? rule.device_id ?? 0),
          minQuantity: Number(rule.minQuantity ?? rule.min_quantity ?? 0),
          discountPercent: Number(rule.discountPercent ?? rule.discount_percent ?? 0),
        })).filter((rule) => rule.deviceId > 0),
        comboPromotions: comboSource.map((rule) => ({
          id: String(rule.id ?? ""),
          items: Array.isArray(rule.items)
            ? rule.items.map((item: any) => ({
                deviceId: Number(item.deviceId ?? item.device_id ?? 0),
                quantity: Number(item.quantity ?? 1) || 1,
              })).filter((item: any) => item.deviceId > 0)
            : [],
          discountPercent: Number(rule.discountPercent ?? rule.discount_percent ?? 0),
        })).filter((rule) => rule.items.length > 0),
        coupons: couponSource.map((coupon) => ({
          code: String(coupon.code ?? ""),
          discountPercent: Number(coupon.discountPercent ?? coupon.discount_percent ?? 0),
          description: coupon.description ?? null,
        })).filter((coupon) => coupon.code.length > 0),
        updatedAt: (data as any).updatedAt ?? (data as any).updated_at ?? null,
      };
      setPromotionsConfig(normalized);
      setPromotionsDraft(normalized);
      setPromotionsError(null);
    } catch (error) {
      console.warn("No se pudo cargar promociones", error);
      setPromotionsError("No se pudo cargar promociones.");
    } finally {
      setPromotionsLoading(false);
    }
  }, []);

  useEffect(() => {
    const numericStore = Number(selectedStoreId);
    if (!Number.isFinite(numericStore) || numericStore <= 0) {
      setPromotionsConfig(null);
      setPromotionsDraft(null);
      return;
    }
    void fetchPromotions(numericStore);
  }, [selectedStoreId, fetchPromotions]);

  const handleReloadPromotions = useCallback(() => {
    const numericStore = Number(selectedStoreId);
    if (!Number.isFinite(numericStore) || numericStore <= 0) {
      setPromotionsError("Selecciona una sucursal válida.");
      return;
    }
    void fetchPromotions(numericStore);
  }, [selectedStoreId, fetchPromotions]);

  const handleFlagToggle = useCallback((flag: "volume" | "combos" | "coupons") => {
    setPromotionsDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        featureFlags: { ...prev.featureFlags, [flag]: !prev.featureFlags[flag] },
      };
    });
  }, []);

  const handleAddVolumeRule = useCallback(() => {
    if (!promotionsDraft) return;
    const deviceId = Number(volumeForm.deviceId);
    const minQuantity = Number(volumeForm.minQuantity);
    const discountPercent = Number(volumeForm.discountPercent);
    if (!volumeForm.id.trim() || !Number.isFinite(deviceId) || deviceId <= 0 || !Number.isFinite(minQuantity) || minQuantity <= 0 || !Number.isFinite(discountPercent) || discountPercent <= 0) {
      return;
    }
    const rule = {
      id: volumeForm.id.trim(),
      deviceId,
      minQuantity,
      discountPercent,
    };
    setPromotionsDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        volumePromotions: [...prev.volumePromotions.filter((item) => item.id !== rule.id), rule],
      };
    });
    setVolumeForm({ id: "", deviceId: "", minQuantity: "", discountPercent: "" });
  }, [promotionsDraft, volumeForm]);

  const handleRemoveVolumeRule = useCallback((id: string) => {
    setPromotionsDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        volumePromotions: prev.volumePromotions.filter((rule) => rule.id !== id),
      };
    });
  }, []);

  const handleAddComboRule = useCallback(() => {
    if (!promotionsDraft) return;
    const discountPercent = Number(comboForm.discountPercent);
    const deviceIds = comboForm.deviceIds
      .split(",")
      .map((value) => Number(value.trim()))
      .filter((value) => Number.isFinite(value) && value > 0);
    if (!comboForm.id.trim() || !deviceIds.length || !Number.isFinite(discountPercent) || discountPercent <= 0) {
      return;
    }
    const items = deviceIds.map((deviceId) => ({ deviceId, quantity: 1 }));
    const rule = {
      id: comboForm.id.trim(),
      items,
      discountPercent,
    };
    setPromotionsDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        comboPromotions: [...prev.comboPromotions.filter((item) => item.id !== rule.id), rule],
      };
    });
    setComboForm({ id: "", deviceIds: "", discountPercent: "" });
  }, [promotionsDraft, comboForm]);

  const handleRemoveComboRule = useCallback((id: string) => {
    setPromotionsDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        comboPromotions: prev.comboPromotions.filter((rule) => rule.id !== id),
      };
    });
  }, []);

  const handleAddCouponRule = useCallback(() => {
    if (!promotionsDraft) return;
    const discountPercent = Number(couponForm.discountPercent);
    const code = couponForm.code.trim().toUpperCase();
    if (!code || !Number.isFinite(discountPercent) || discountPercent <= 0) {
      return;
    }
    const coupon = {
      code,
      discountPercent,
      description: couponForm.description.trim() ? couponForm.description.trim() : null,
    };
    setPromotionsDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        coupons: [...prev.coupons.filter((item) => item.code !== coupon.code), coupon],
      };
    });
    setCouponForm({ code: "", discountPercent: "", description: "" });
  }, [promotionsDraft, couponForm]);

  const handleRemoveCouponRule = useCallback((code: string) => {
    setPromotionsDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        coupons: prev.coupons.filter((coupon) => coupon.code !== code),
      };
    });
  }, []);

  const handleSavePromotions = useCallback(async () => {
    if (!promotionsDraft) return;
    const storeNumeric = promotionsDraft.storeId || Number(selectedStoreId);
    if (!Number.isFinite(storeNumeric) || storeNumeric <= 0) {
      setPromotionsError("Selecciona una sucursal válida.");
      return;
    }
    const requestPayload: PosPromotionsUpdateRequest = {
      store_id: storeNumeric,
      feature_flags: { ...promotionsDraft.featureFlags },
      volume_promotions: promotionsDraft.volumePromotions.map((rule) => ({
        id: rule.id,
        device_id: Number(rule.deviceId),
        min_quantity: Number(rule.minQuantity),
        discount_percent: Number(rule.discountPercent),
      })),
      combo_promotions: promotionsDraft.comboPromotions.map((rule) => ({
        id: rule.id,
        discount_percent: Number(rule.discountPercent),
        items: rule.items.map((item) => ({
          device_id: Number(item.deviceId),
          quantity: Number(item.quantity) || 1,
        })),
      })),
      coupons: promotionsDraft.coupons.map((coupon) => ({
        code: coupon.code,
        discount_percent: Number(coupon.discountPercent),
        description: coupon.description ?? null,
      })),
    };
    setPromotionsLoading(true);
    try {
      await SalesPOS.updatePromotions(requestPayload);
      await fetchPromotions(storeNumeric);
      setPromotionsEditorOpen(false);
      setPromotionsError(null);
    } catch (error) {
      console.warn("No se pudo guardar promociones", error);
      setPromotionsError("No se pudo guardar promociones.");
    } finally {
      setPromotionsLoading(false);
    }
  }, [promotionsDraft, selectedStoreId, fetchPromotions]);

  const promotionBadges = useMemo<Record<string, string[]>>(() => {
    if (!promotionsConfig) {
      return {};
    }
    const badges: Record<string, string[]> = {};
    const lineByDevice = new Map<number, (typeof lines)[number]>();
    lines.forEach((line) => {
      const numericId = Number(line.productId);
      if (Number.isFinite(numericId)) {
        lineByDevice.set(numericId, line);
      }
    });
    if (promotionsConfig.featureFlags.volume) {
      promotionsConfig.volumePromotions.forEach((rule) => {
        const target = lineByDevice.get(rule.deviceId);
        if (!target) return;
        if (target.qty >= rule.minQuantity) {
          const key = String(target.productId);
          const badge = `Volumen ${rule.discountPercent}% (≥${rule.minQuantity})`;
          badges[key] = [...(badges[key] ?? []), badge];
        }
      });
    }
    if (promotionsConfig.featureFlags.combos) {
      promotionsConfig.comboPromotions.forEach((rule) => {
        if (!rule.items.length) return;
        const qualifies = rule.items.every((item) => {
          const target = lineByDevice.get(item.deviceId);
          return target && target.qty >= item.quantity;
        });
        if (!qualifies) return;
        rule.items.forEach((item) => {
          const target = lineByDevice.get(item.deviceId);
          if (!target) return;
          const key = String(target.productId);
          const badge = `Combo ${rule.id} ${rule.discountPercent}%`;
          badges[key] = [...(badges[key] ?? []), badge];
        });
      });
    }
    return badges;
  }, [lines, promotionsConfig]);

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

        const badgeKey = String(line.productId);
        if (promotionBadges[badgeKey]?.length) {
          cartLine.badges = promotionBadges[badgeKey];
        }

        return cartLine;
      }),
    [lines, promotionBadges],
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
        tips: payments.reduce((sum, payment) => sum + (payment.tipAmount ?? 0), 0),
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

  const handleApplyCouponCode = useCallback(() => {
    const normalized = couponInput.trim().toUpperCase();
    if (!normalized || normalized.length < 3) {
      return;
    }
    if (appliedCoupons.includes(normalized)) {
      setCouponInput("");
      return;
    }
    setAppliedCoupons([...appliedCoupons, normalized]);
    setCouponInput("");
  }, [couponInput, appliedCoupons, setAppliedCoupons]);

  const handleRemoveAppliedCoupon = useCallback(
    (code: string) => {
      setAppliedCoupons(appliedCoupons.filter((item) => item !== code));
    },
    [appliedCoupons, setAppliedCoupons],
  );

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
    const payload: PaymentInput[] = paymentDrafts.map(
      ({ type, amount, reference, tipAmount, terminalId }) => {
        const payment: PaymentInput = { type, amount };
        if (reference) {
          payment.reference = reference;
        }
        if (typeof tipAmount === "number" && tipAmount > 0) {
          payment.tipAmount = tipAmount;
        }
        if (terminalId) {
          payment.terminalId = terminalId;
        }
        return payment;
      },
    );
    setPayments(payload);
    try {
      const result = await checkout();
      await onAfterCheckout(result);
      if (result?.saleId) {
        const saleIdStr = String(result.saleId);
        setLastSale({
          id: saleIdStr,
          number: result.number,
          receiptUrl: result.printable?.pdfUrl ?? null,
        });
        setLastSaleContact((prev) => ({
          email: customer?.email ?? prev?.email,
          phone: customer?.phone ?? prev?.phone,
          docId: customer?.docId ?? prev?.docId,
          name: customer?.name ?? prev?.name,
        }));
      } else {
        setLastSale(null);
      }
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
      setDocType("TICKET");
    } finally {
      setPaymentsOpen(false);
    }
  };

  const handleSend = useCallback(
    async (channel: "email" | "whatsapp") => {
      if (!lastSale) {
        pushBanner({ type: "warn", msg: "Registra una venta antes de enviar el recibo." });
        return;
      }
      const contact = channel === "email"
        ? lastSaleContact?.email ?? customer?.email
        : lastSaleContact?.phone ?? customer?.phone;
      if (!contact) {
        pushBanner({ type: "error", msg: "No hay datos de contacto para enviar el recibo." });
        return;
      }
      setSendingChannel(channel);
      try {
        const reason = "Envio recibo inmediato";
        const message = channel === "email"
          ? `Adjuntamos el comprobante ${lastSale.number}.`
          : `Recibo ${lastSale.number}. Descarga: ${lastSale.receiptUrl ?? `/pos/receipt/${lastSale.id}`}`;
        await SalesPOS.sendReceipt(
          lastSale.id,
          {
            channel,
            recipient: contact,
            message,
            subject: channel === "email" ? `Recibo ${lastSale.number}` : undefined,
          },
          reason,
        );
        await logUI({
          ts: Date.now(),
          userId: user?.id ?? null,
          module: "POS",
          action: `receipt.send.${channel}`,
          entityId: lastSale.id,
          meta: { contact },
        });
        pushBanner({
          type: "success",
          msg: channel === "email" ? "Recibo enviado por correo." : "Recibo enviado por WhatsApp.",
        });
      } catch (error) {
        pushBanner({ type: "error", msg: "No se pudo enviar el recibo." });
      } finally {
        setSendingChannel(null);
      }
    },
    [customer, lastSale, lastSaleContact, pushBanner, user],
  );

  const handleSendEmail = useCallback(() => {
    void handleSend("email");
  }, [handleSend]);

  const handleSendWhatsApp = useCallback(() => {
    void handleSend("whatsapp");
  }, [handleSend]);

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

  const handleTipPresetBlur = () => {
    const values = tipPresetInput
      .split(",")
      .map((entry) => Number(entry.trim()))
      .filter((value) => Number.isFinite(value) && value >= 0);
    if (values.length > 0) {
      setTipSuggestions(values);
    }
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
      <div
        style={{
          border: "1px solid rgba(56,189,248,0.25)",
          borderRadius: 12,
          padding: 12,
          background: "rgba(15,23,42,0.65)",
          display: "grid",
          gap: 10,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div style={{ fontWeight: 600 }}>Promociones activas</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
              Sucursal
              <input
                value={selectedStoreId}
                onChange={(event) => setSelectedStoreId(event.target.value)}
                style={{ ...editorInputStyle, minWidth: 80 }}
              />
            </label>
            <button onClick={handleReloadPromotions} style={secondaryButtonStyle}>
              Recargar
            </button>
            <button
              onClick={() => setPromotionsEditorOpen((prev) => !prev)}
              style={{
                ...secondaryButtonStyle,
                background: promotionsEditorOpen ? "rgba(56,189,248,0.28)" : secondaryButtonStyle.background,
                color: promotionsEditorOpen ? "#0f172a" : secondaryButtonStyle.color,
              }}
            >
              {promotionsEditorOpen ? "Cerrar editor" : "Editar reglas"}
            </button>
          </div>
        </div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>
          {promotionsLoading
            ? "Sincronizando promociones…"
            : promotionsConfig
            ? `Volumen ${promotionsConfig.featureFlags.volume ? "activo" : "apagado"} · Combos ${promotionsConfig.featureFlags.combos ? "activos" : "apagados"} · Cupones ${promotionsConfig.featureFlags.coupons ? "activos" : "apagados"}`
            : "Selecciona una sucursal para cargar promociones."}
        </div>
        {promotionsError && (
          <div style={{ fontSize: 12, color: "#f87171" }}>{promotionsError}</div>
        )}
        {promotionsConfig && !promotionsLoading && (
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 12, color: "#cbd5f5" }}>
            <span>{promotionsConfig.volumePromotions.length} reglas de volumen</span>
            <span>{promotionsConfig.comboPromotions.length} combos</span>
            <span>{promotionsConfig.coupons.length} cupones</span>
          </div>
        )}
        {promotionsEditorOpen && promotionsDraft && (
          <div
            style={{
              display: "grid",
              gap: 12,
              background: "rgba(15,23,42,0.75)",
              borderRadius: 12,
              padding: 12,
              border: "1px solid rgba(56,189,248,0.25)",
            }}
          >
            <div>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Banderas</div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 12 }}>
                {(["volume", "combos", "coupons"] as const).map((flag) => (
                  <label key={flag} style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <input
                      type="checkbox"
                      checked={Boolean(promotionsDraft.featureFlags[flag])}
                      onChange={() => handleFlagToggle(flag)}
                    />
                    {flag === "volume" ? "Volumen" : flag === "combos" ? "Combos" : "Cupones"}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Promociones por volumen</div>
              {promotionsDraft.volumePromotions.length ? (
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#cbd5f5" }}>
                  {promotionsDraft.volumePromotions.map((rule) => (
                    <li key={rule.id} style={{ marginBottom: 4 }}>
                      ID {rule.id} · dispositivo #{rule.deviceId} · min {rule.minQuantity} · {rule.discountPercent}%
                      <button
                        onClick={() => handleRemoveVolumeRule(rule.id)}
                        style={{ ...secondaryButtonStyle, marginLeft: 8, padding: "2px 8px", fontSize: 11 }}
                      >
                        Quitar
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ fontSize: 12, color: "#94a3b8" }}>Sin reglas de volumen.</div>
              )}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
                <input
                  value={volumeForm.id}
                  onChange={(event) => setVolumeForm((prev) => ({ ...prev, id: event.target.value }))}
                  placeholder="ID"
                  style={editorInputStyle}
                />
                <input
                  value={volumeForm.deviceId}
                  onChange={(event) => setVolumeForm((prev) => ({ ...prev, deviceId: event.target.value }))}
                  placeholder="Dispositivo"
                  style={editorInputStyle}
                />
                <input
                  value={volumeForm.minQuantity}
                  onChange={(event) => setVolumeForm((prev) => ({ ...prev, minQuantity: event.target.value }))}
                  placeholder="Cantidad"
                  style={editorInputStyle}
                />
                <input
                  value={volumeForm.discountPercent}
                  onChange={(event) => setVolumeForm((prev) => ({ ...prev, discountPercent: event.target.value }))}
                  placeholder="% desc"
                  style={editorInputStyle}
                />
                <button onClick={handleAddVolumeRule} style={secondaryButtonStyle}>
                  Agregar
                </button>
              </div>
            </div>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Combos</div>
              {promotionsDraft.comboPromotions.length ? (
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#cbd5f5" }}>
                  {promotionsDraft.comboPromotions.map((rule) => (
                    <li key={rule.id} style={{ marginBottom: 4 }}>
                      {rule.id} · dispositivos {rule.items.map((item) => `#${item.deviceId}`).join(", ")} · {rule.discountPercent}%
                      <button
                        onClick={() => handleRemoveComboRule(rule.id)}
                        style={{ ...secondaryButtonStyle, marginLeft: 8, padding: "2px 8px", fontSize: 11 }}
                      >
                        Quitar
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ fontSize: 12, color: "#94a3b8" }}>Sin combos registrados.</div>
              )}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
                <input
                  value={comboForm.id}
                  onChange={(event) => setComboForm((prev) => ({ ...prev, id: event.target.value }))}
                  placeholder="ID"
                  style={editorInputStyle}
                />
                <input
                  value={comboForm.deviceIds}
                  onChange={(event) => setComboForm((prev) => ({ ...prev, deviceIds: event.target.value }))}
                  placeholder="Dispositivos (1,2)"
                  style={{ ...editorInputStyle, minWidth: 160 }}
                />
                <input
                  value={comboForm.discountPercent}
                  onChange={(event) => setComboForm((prev) => ({ ...prev, discountPercent: event.target.value }))}
                  placeholder="% desc"
                  style={editorInputStyle}
                />
                <button onClick={handleAddComboRule} style={secondaryButtonStyle}>
                  Agregar
                </button>
              </div>
            </div>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>Cupones</div>
              {promotionsDraft.coupons.length ? (
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#cbd5f5" }}>
                  {promotionsDraft.coupons.map((coupon) => (
                    <li key={coupon.code} style={{ marginBottom: 4 }}>
                      {coupon.code} · {coupon.discountPercent}% {coupon.description ? `· ${coupon.description}` : ""}
                      <button
                        onClick={() => handleRemoveCouponRule(coupon.code)}
                        style={{ ...secondaryButtonStyle, marginLeft: 8, padding: "2px 8px", fontSize: 11 }}
                      >
                        Quitar
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ fontSize: 12, color: "#94a3b8" }}>Sin cupones configurados.</div>
              )}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
                <input
                  value={couponForm.code}
                  onChange={(event) => setCouponForm((prev) => ({ ...prev, code: event.target.value }))}
                  placeholder="Código"
                  style={editorInputStyle}
                />
                <input
                  value={couponForm.discountPercent}
                  onChange={(event) => setCouponForm((prev) => ({ ...prev, discountPercent: event.target.value }))}
                  placeholder="% desc"
                  style={editorInputStyle}
                />
                <input
                  value={couponForm.description}
                  onChange={(event) => setCouponForm((prev) => ({ ...prev, description: event.target.value }))}
                  placeholder="Descripción"
                  style={{ ...editorInputStyle, minWidth: 180 }}
                />
                <button onClick={handleAddCouponRule} style={secondaryButtonStyle}>
                  Agregar
                </button>
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button onClick={handleSavePromotions} style={primaryButtonStyle}>
                Guardar promociones
              </button>
            </div>
          </div>
        )}
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <input
          value={couponInput}
          onChange={(event) => setCouponInput(event.target.value)}
          placeholder="Cupón promocional"
          style={editorInputStyle}
        />
        <button onClick={handleApplyCouponCode} style={secondaryButtonStyle}>
          Aplicar cupón
        </button>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {appliedCoupons.map((code) => (
            <span
              key={code}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "4px 10px",
                borderRadius: 9999,
                background: "rgba(56,189,248,0.2)",
                color: "#38bdf8",
                fontSize: 12,
              }}
            >
              {code}
              <button
                onClick={() => handleRemoveAppliedCoupon(code)}
                style={{
                  border: "none",
                  background: "transparent",
                  color: "#0f172a",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
                aria-label={`Quitar cupón ${code}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
          display: "flex",
          gap: 12,
          flexWrap: "wrap",
          alignItems: "center",
          background: "rgba(30,41,59,0.6)",
          borderRadius: 12,
          padding: "8px 12px",
          border: "1px solid rgba(148,163,184,0.15)",
        }}
      >
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
          Terminal predeterminado
          <select
            value={selectedTerminal ?? ""}
            onChange={(event) => setSelectedTerminal(event.target.value || undefined)}
            style={{ padding: 8, borderRadius: 8 }}
          >
            {terminalOptions.map((terminal) => (
              <option key={terminal.id} value={terminal.id}>
                {terminal.label}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
          Propinas sugeridas (%)
          <input
            value={tipPresetInput}
            onChange={(event) => setTipPresetInput(event.target.value)}
            onBlur={handleTipPresetBlur}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                handleTipPresetBlur();
              }
            }}
            style={{ padding: 8, borderRadius: 8 }}
            placeholder="0, 5, 10"
          />
        </label>
      </div>
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
                onSendEmail={handleSendEmail}
                onSendWhatsapp={handleSendWhatsApp}
                canSend={!!lastSale}
                sendingChannel={sendingChannel}
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
        terminals={terminalOptions}
        defaultTerminalId={selectedTerminal}
        tipSuggestions={tipSuggestions}
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
            if (payload.email) {
              nextCustomer.email = payload.email;
            }
            if (payload.docId) {
              nextCustomer.docId = payload.docId;
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
