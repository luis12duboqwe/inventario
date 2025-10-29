import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type {
  CashSession,
  Customer,
  Device,
  PaymentMethod,
  PosConfig,
  PosConfigUpdateInput,
  PosSalePayload,
  Sale,
  Store,
} from "../../../../api";
import {
  closeCashSession,
  createCustomer,
  getDevices,
  getPosConfig,
  listCashSessions,
  listCustomers,
  submitPosSale,
  updatePosConfig,
  openCashSession,
} from "../../../../api";
import type { CartLine } from "../../../../pages/pos/components/CartPanel";
import type { PaymentModalProps } from "../../../../pages/pos/components/PaymentModal";

const PAYMENT_METHODS: PaymentMethod[] = [
  "EFECTIVO",
  "TARJETA",
  "TRANSFERENCIA",
  "CREDITO",
  "OTRO",
];

type Totals = {
  subtotal: number;
  tax: number;
  total: number;
};

const buildEmptyBreakdown = (): Record<PaymentMethod, number> => ({
  EFECTIVO: 0,
  TARJETA: 0,
  TRANSFERENCIA: 0,
  CREDITO: 0,
  OTRO: 0,
});

type PaymentState = {
  paymentMethod: PaymentMethod;
  customerId: number | null;
  customerName: string;
  notes: string;
  discountPercent: number;
  applyTaxes: boolean;
  reason: string;
  confirm: boolean;
  cashSessionId: number | null;
  paymentBreakdown: Record<PaymentMethod, number>;
};

const createInitialPayment = (): PaymentState => ({
  paymentMethod: "EFECTIVO",
  customerId: null,
  customerName: "",
  notes: "",
  discountPercent: 0,
  applyTaxes: true,
  reason: "Venta mostrador",
  confirm: false,
  cashSessionId: null,
  paymentBreakdown: buildEmptyBreakdown(),
});

type AlertsState = {
  message: string | null;
  error: string | null;
};

type QuickSaleState = {
  stores: Store[];
  selectedStoreId: number | null;
  onStoreChange: (storeId: number | null) => void;
  search: string;
  onSearchChange: (value: string) => void;
  searchDisabled: boolean;
};

type ProductGridState = {
  quickDevices: Device[];
  filteredDevices: Device[];
  disabled: boolean;
  onDeviceSelect: (device: Device) => void;
};

type CartState = {
  items: CartLine[];
  totals: Totals;
  hasTaxes: boolean;
  globalDiscount: number;
  onUpdate: (deviceId: number, updates: Partial<CartLine>) => void;
  onRemove: (deviceId: number) => void;
};

type CashHistoryState = {
  sessions: CashSession[];
  loading: boolean;
  onRefresh: () => void;
  formatCurrency: (value: number) => string;
  formatDateTime: (value?: string | null) => string;
  activeSessionId: number | null;
};

type ReceiptState = {
  sale: Sale | null;
  receiptUrl: string | null;
};

type SettingsState = {
  config: PosConfig | null;
  devices: Device[];
  onSave: (payload: PosConfigUpdateInput) => Promise<void>;
  loading: boolean;
};

type ConfigReasonModalState = {
  open: boolean;
  reason: string;
  onReasonChange: (value: string) => void;
  error: string | null;
  submitting: boolean;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>;
  onClose: () => void;
  pendingPayload: PosConfigUpdateInput | null;
};

export type UsePosDashboardControllerParams = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

export type UsePosDashboardControllerReturn = {
  alerts: AlertsState;
  quickSale: QuickSaleState;
  productGrid: ProductGridState;
  cart: CartState;
  paymentModal: PaymentModalProps;
  cashHistory: CashHistoryState;
  receipt: ReceiptState;
  settings: SettingsState;
  configReasonModal: ConfigReasonModalState;
};

export function usePosDashboardController({
  token,
  stores,
  defaultStoreId = null,
  onInventoryRefresh,
}: UsePosDashboardControllerParams): UsePosDashboardControllerReturn {
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(
    defaultStoreId ?? null,
  );
  const [devices, setDevices] = useState<Device[]>([]);
  const [config, setConfig] = useState<PosConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [payment, setPayment] = useState<PaymentState>(() => createInitialPayment());
  const [lastSale, setLastSale] = useState<Sale | null>(null);
  const [receiptUrl, setReceiptUrl] = useState<string | null>(null);
  const [draftId, setDraftId] = useState<number | null>(null);
  const [submittingMode, setSubmittingMode] = useState<"draft" | "sale" | null>(
    null,
  );
  const [saleWarnings, setSaleWarnings] = useState<string[]>([]);
  const [customerOptions, setCustomerOptions] = useState<Customer[]>([]);
  const [customerSearch, setCustomerSearch] = useState("");
  const [customerLoading, setCustomerLoading] = useState(false);
  const [cashSessions, setCashSessions] = useState<CashSession[]>([]);
  const [cashLoading, setCashLoading] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [configReasonOpen, setConfigReasonOpen] = useState(false);
  const [configReason, setConfigReason] = useState("Ajuste configuración POS");
  const [configReasonError, setConfigReasonError] = useState<string | null>(null);
  const [configReasonSubmitting, setConfigReasonSubmitting] = useState(false);
  const [pendingConfigPayload, setPendingConfigPayload] =
    useState<PosConfigUpdateInput | null>(null);
  const configRequestRef = useRef<
    { resolve: () => void; reject: (error: Error) => void } | null
  >(null);

  const refreshCustomers = useCallback(
    async (query?: string) => {
      try {
        setCustomerLoading(true);
        const normalized = query?.trim();
        const data = await listCustomers(token, {
          query: normalized && normalized.length > 0 ? normalized : undefined,
          limit: 100,
        });
        setCustomerOptions(data);
      } catch (err) {
        setError((current) =>
          current ?? "No fue posible cargar los clientes corporativos.",
        );
      } finally {
        setCustomerLoading(false);
      }
    },
    [token],
  );

  const refreshCashSessions = useCallback(
    async (storeId: number) => {
      try {
        setCashLoading(true);
        const history = await listCashSessions(token, storeId, 20);
        setCashSessions(history);
      } catch (err) {
        setError((current) =>
          current ?? "No fue posible cargar las sesiones de caja.",
        );
      } finally {
        setCashLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    setSelectedStoreId(defaultStoreId ?? null);
  }, [defaultStoreId]);

  useEffect(() => {
    const query = customerSearch.trim();
    const handler = window.setTimeout(() => {
      if (query.length === 0) {
        void refreshCustomers();
      } else if (query.length >= 2) {
        void refreshCustomers(query);
      }
    }, 350);
    return () => window.clearTimeout(handler);
  }, [customerSearch, refreshCustomers]);

  useEffect(() => {
    if (!payment.customerId) {
      setSelectedCustomer(null);
      return;
    }
    setSelectedCustomer((current) => {
      if (current && current.id === payment.customerId) {
        return current;
      }
      const found = customerOptions.find(
        (candidate) => candidate.id === payment.customerId,
      );
      return found ?? current;
    });
  }, [payment.customerId, customerOptions]);

  useEffect(() => {
    setPayment((current) => {
      if (
        current.cashSessionId &&
        cashSessions.some((session) => session.id === current.cashSessionId)
      ) {
        return current;
      }
      const opened = cashSessions.find((session) => session.status === "ABIERTO");
      return {
        ...current,
        cashSessionId: opened ? opened.id : null,
      };
    });
  }, [cashSessions]);

  useEffect(() => {
    if (!selectedStoreId) {
      setDevices([]);
      setConfig(null);
      setCart([]);
      setDraftId(null);
      setCashSessions([]);
      setPayment(createInitialPayment());
      setSelectedCustomer(null);
      return;
    }
    const loadStoreContext = async () => {
      try {
        setConfigLoading(true);
        const [storeDevices, storeConfig] = await Promise.all([
          getDevices(token, selectedStoreId),
          getPosConfig(token, selectedStoreId),
        ]);
        setDevices(storeDevices);
        setConfig(storeConfig);
        setPayment((current) => {
          const next = createInitialPayment();
          next.applyTaxes = storeConfig.tax_rate > 0;
          next.reason = current.reason || next.reason;
          return next;
        });
        setDraftId(null);
        setCart([]);
        setMessage(null);
        setError(null);
        setSelectedCustomer(null);
        setCustomerSearch("");
        await refreshCashSessions(selectedStoreId);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "No fue posible cargar la información POS.",
        );
      } finally {
        setConfigLoading(false);
      }
    };
    loadStoreContext();
    void refreshCustomers();
  }, [selectedStoreId, token, refreshCashSessions, refreshCustomers]);

  const filteredDevices = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) {
      return devices.slice(0, 6);
    }
    return devices
      .filter((device) => {
        const haystack = [
          device.sku,
          device.name,
          device.imei ?? "",
          device.modelo ?? "",
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(query);
      })
      .slice(0, 10);
  }, [devices, search]);

  const quickDevices = useMemo(() => {
    if (!config) {
      return [];
    }
    return config.quick_product_ids
      .map((id) => devices.find((device) => device.id === id))
      .filter((device): device is Device => Boolean(device));
  }, [config, devices]);

  const activeCashSession = useMemo(
    () => cashSessions.find((session) => session.status === "ABIERTO") ?? null,
    [cashSessions],
  );

  const cartWarnings = useMemo(
    () =>
      cart
        .filter((line) => line.quantity > line.device.quantity)
        .map(
          (line) =>
            `No hay suficiente stock de ${line.device.sku}. Disponible: ${line.device.quantity}, solicitado: ${line.quantity}.`,
        ),
    [cart],
  );

  const totals = useMemo<Totals>(() => {
    if (cart.length === 0) {
      return { subtotal: 0, tax: 0, total: 0 };
    }
    const globalDiscount = payment.discountPercent;
    let subtotal = 0;
    cart.forEach((line) => {
      const price = line.device.unit_price ?? 0;
      const base = price * line.quantity;
      const lineDiscountPercent =
        line.discountPercent > 0 ? line.discountPercent : globalDiscount;
      const discountAmount = base * (lineDiscountPercent / 100);
      subtotal += base - discountAmount;
    });
    const taxRate = config && payment.applyTaxes ? config.tax_rate : 0;
    const taxAmount = subtotal * (taxRate / 100);
    const total = subtotal + taxAmount;
    return {
      subtotal: Number(subtotal.toFixed(2)),
      tax: Number(taxAmount.toFixed(2)),
      total: Number(total.toFixed(2)),
    };
  }, [cart, config, payment.discountPercent, payment.applyTaxes]);

  const combinedWarnings = [...cartWarnings, ...saleWarnings];
  const isSubmitting = submittingMode !== null;
  const cartIsEmpty = cart.length === 0;

  const formatCurrency = useCallback(
    (value: number) =>
      value.toLocaleString("es-MX", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    [],
  );

  const formatDateTime = useCallback(
    (value?: string | null) => (value ? new Date(value).toLocaleString("es-MX") : "—"),
    [],
  );

  const handleAddDevice = (device: Device) => {
    if (!selectedStoreId) {
      setError("Selecciona una sucursal para comenzar a vender.");
      return;
    }
    setError(null);
    setSaleWarnings([]);
    setCart((current) => {
      const existing = current.find((line) => line.device.id === device.id);
      if (existing) {
        return current.map((line) =>
          line.device.id === device.id
            ? { ...line, quantity: line.quantity + 1 }
            : line,
        );
      }
      return [...current, { device, quantity: 1, discountPercent: 0 }];
    });
  };

  const handleUpdateCart = (deviceId: number, updates: Partial<CartLine>) => {
    setSaleWarnings([]);
    setCart((current) =>
      current.map((line) =>
        line.device.id === deviceId
          ? {
              ...line,
              ...updates,
            }
          : line,
      ),
    );
  };

  const handleRemoveCart = (deviceId: number) => {
    setSaleWarnings([]);
    setCart((current) => current.filter((line) => line.device.id !== deviceId));
  };

  const resetSaleContext = (sale?: Sale | null, receipt?: string | null) => {
    if (sale) {
      setLastSale(sale);
      setReceiptUrl(receipt ?? null);
    }
    setCart([]);
    setDraftId(null);
    setPayment((current) => {
      const next = createInitialPayment();
      next.applyTaxes = current.applyTaxes;
      next.reason = current.reason;
      next.customerId = current.customerId;
      next.customerName = current.customerName;
      next.cashSessionId = current.cashSessionId;
      return next;
    });
    if (selectedStoreId) {
      void refreshCashSessions(selectedStoreId);
    }
    const trimmedSearch = customerSearch.trim();
    void refreshCustomers(trimmedSearch.length >= 2 ? trimmedSearch : undefined);
    onInventoryRefresh?.();
  };

  const handleSubmitSale = async (mode: "draft" | "sale") => {
    if (!selectedStoreId) {
      setError("Selecciona una sucursal para operar ventas POS.");
      return;
    }
    if (mode === "sale" && payment.reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo de al menos 5 caracteres.");
      return;
    }
    if (mode === "sale" && cartWarnings.length > 0) {
      setError("Ajusta las cantidades para coincidir con el inventario disponible.");
      return;
    }
    if (mode === "sale" && payment.paymentMethod === "CREDITO" && !payment.customerId) {
      setError("Selecciona un cliente registrado para ventas a crédito.");
      return;
    }
    try {
      setSubmittingMode(mode);
      setMessage(null);
      setError(null);
      const sanitizedBreakdown = PAYMENT_METHODS.reduce<Record<string, number>>(
        (acc, method) => {
          const value = Number(payment.paymentBreakdown[method] ?? 0);
          if (!Number.isFinite(value)) {
            return acc;
          }
          const normalized = Number(value.toFixed(2));
          if (normalized > 0) {
            acc[method] = normalized;
          }
          return acc;
        },
        {},
      );
      if (mode === "sale") {
        const breakdownTotal = Object.values(sanitizedBreakdown).reduce(
          (acc, value) => acc + value,
          0,
        );
        if (breakdownTotal === 0 && totals.total > 0) {
          sanitizedBreakdown[payment.paymentMethod] = Number(
            totals.total.toFixed(2),
          );
        } else if (Math.abs(breakdownTotal - totals.total) > 0.5) {
          setError("El desglose de pago debe coincidir con el total a cobrar.");
          return;
        }
      }
      const resolvedCustomerName =
        payment.customerName.trim() || selectedCustomer?.name || undefined;
      const payload: PosSalePayload = {
        store_id: selectedStoreId,
        payment_method: payment.paymentMethod,
        items: cart.map((line) => ({
          device_id: line.device.id,
          quantity: line.quantity,
          discount_percent: line.discountPercent,
        })),
        discount_percent: payment.discountPercent,
        customer_id: payment.customerId ?? undefined,
        customer_name: resolvedCustomerName,
        notes: payment.notes || undefined,
        confirm: mode === "sale",
        save_as_draft: mode === "draft",
        draft_id: draftId ?? undefined,
        apply_taxes: payment.applyTaxes,
      };
      if (payment.cashSessionId) {
        payload.cash_session_id = payment.cashSessionId;
      }
      if (Object.keys(sanitizedBreakdown).length > 0) {
        payload.payment_breakdown = sanitizedBreakdown;
      }
      const response = await submitPosSale(token, payload, payment.reason.trim());
      setSaleWarnings(response.warnings ?? []);
      if (response.status === "draft" && response.draft) {
        setDraftId(response.draft.id);
        setMessage("Borrador guardado. Puedes retomar la venta más tarde.");
      }
      if (response.status === "registered" && response.sale) {
        setMessage("Venta registrada con éxito.");
        resetSaleContext(response.sale, response.receipt_url ?? null);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible registrar la venta POS.",
      );
    } finally {
      setSubmittingMode(null);
    }
  };

  const handleSettingsSave = (payload: PosConfigUpdateInput) => {
    return new Promise<void>((resolve, reject) => {
      configRequestRef.current = { resolve, reject };
      setPendingConfigPayload(payload);
      setConfigReason("Ajuste configuración POS");
      setConfigReasonError(null);
      setConfigReasonOpen(true);
    });
  };

  const closeConfigReasonDialog = () => {
    if (configReasonSubmitting) {
      return;
    }
    setConfigReasonOpen(false);
    setConfigReason("Ajuste configuración POS");
    setConfigReasonError(null);
    setPendingConfigPayload(null);
    const pendingRequest = configRequestRef.current;
    if (pendingRequest) {
      pendingRequest.reject(new Error("Actualización cancelada por el usuario."));
      configRequestRef.current = null;
    }
  };

  const submitConfigReason = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();
    if (!pendingConfigPayload) {
      return;
    }
    const normalizedReason = configReason.trim();
    if (normalizedReason.length < 5) {
      setConfigReasonError("Ingresa un motivo corporativo de al menos 5 caracteres.");
      return;
    }

    try {
      setConfigReasonSubmitting(true);
      setConfigReasonError(null);
      setSettingsSaving(true);
      setError(null);
      const updated = await updatePosConfig(
        token,
        pendingConfigPayload,
        normalizedReason,
      );
      setConfig(updated);
      setMessage("Configuración POS actualizada.");
      if (configRequestRef.current) {
        configRequestRef.current.resolve();
        configRequestRef.current = null;
      }
      setConfigReasonOpen(false);
      setPendingConfigPayload(null);
      setConfigReason("Ajuste configuración POS");
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "No fue posible actualizar la configuración POS.";
      setConfigReasonError(message);
    } finally {
      setSettingsSaving(false);
      setConfigReasonSubmitting(false);
    }
  };

  const handleQuickCustomerCreate = async () => {
    const name = window.prompt("Nombre del cliente", "");
    if (!name || !name.trim()) {
      return;
    }
    const email = window.prompt("Correo del cliente (opcional)", "");
    const reason = window.prompt(
      "Motivo corporativo para registrar al cliente",
      "Alta cliente POS",
    );
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo válido para crear clientes.");
      return;
    }
    try {
      setError(null);
      const customer = await createCustomer(
        token,
        {
          name: name.trim(),
          email: email?.trim() || undefined,
        },
        reason.trim(),
      );
      setMessage("Cliente creado correctamente.");
      setPayment((current) => ({
        ...current,
        customerId: customer.id,
        customerName: customer.name,
      }));
      setSelectedCustomer(customer);
      setCustomerSearch("");
      const trimmedSearch = customerSearch.trim();
      await refreshCustomers(trimmedSearch.length >= 2 ? trimmedSearch : undefined);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible registrar al cliente desde el POS.",
      );
    }
  };

  const handleOpenCashSession = async () => {
    if (!selectedStoreId) {
      setError("Selecciona una sucursal para gestionar la caja.");
      return;
    }
    if (activeCashSession) {
      setMessage("Ya existe una sesión de caja abierta para esta sucursal.");
      return;
    }
    const openingRaw = window.prompt("Monto de apertura", "0");
    if (openingRaw === null) {
      return;
    }
    const openingAmount = Number(openingRaw);
    if (!Number.isFinite(openingAmount) || openingAmount < 0) {
      setError("Indica un monto de apertura válido.");
      return;
    }
    const notes = window.prompt("Notas de apertura (opcional)", "Apertura de caja");
    const reason = window.prompt(
      "Motivo corporativo para abrir caja",
      "Apertura turno POS",
    );
    if (!reason || reason.trim().length < 5) {
      setError("Debes capturar un motivo corporativo válido para abrir caja.");
      return;
    }
    try {
      const session = await openCashSession(
        token,
        {
          store_id: selectedStoreId,
          opening_amount: Number(openingAmount.toFixed(2)),
          notes: notes?.trim() || undefined,
        },
        reason.trim(),
      );
      setMessage("Caja abierta correctamente.");
      setCashSessions((current) => [session, ...current]);
      setPayment((current) => ({ ...current, cashSessionId: session.id }));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible abrir la sesión de caja.",
      );
    }
  };

  const handleCloseCashSession = async () => {
    if (!selectedStoreId) {
      setError("Selecciona una sucursal para gestionar la caja.");
      return;
    }
    if (!activeCashSession) {
      setMessage("No hay una sesión abierta por cerrar.");
      return;
    }
    const closingRaw = window.prompt(
      "Monto contado al cierre",
      String(Number(activeCashSession.expected_amount ?? 0).toFixed(2)),
    );
    if (closingRaw === null) {
      return;
    }
    const closingAmount = Number(closingRaw);
    if (!Number.isFinite(closingAmount) || closingAmount < 0) {
      setError("Indica un monto de cierre válido.");
      return;
    }
    const breakdown: Record<string, number> = {};
    for (const method of PAYMENT_METHODS) {
      const previousValue =
        activeCashSession.payment_breakdown?.[method] ??
        payment.paymentBreakdown[method] ??
        0;
      const response = window.prompt(
        `Total reportado para ${method.toLowerCase()}`,
        String(Number(previousValue).toFixed(2)),
      );
      if (response === null) {
        return;
      }
      const parsed = Number(response);
      if (!Number.isFinite(parsed) || parsed < 0) {
        setError(`Monto inválido para ${method}.`);
        return;
      }
      if (parsed > 0) {
        breakdown[method] = Number(parsed.toFixed(2));
      }
    }
    const notes = window.prompt("Notas de cierre (opcional)", "Cierre turno POS");
    const reason = window.prompt(
      "Motivo corporativo para cerrar caja",
      "Cierre de caja POS",
    );
    if (!reason || reason.trim().length < 5) {
      setError("Debes capturar un motivo corporativo válido para cerrar la caja.");
      return;
    }
    try {
      const closed = await closeCashSession(
        token,
        {
          session_id: activeCashSession.id,
          closing_amount: Number(closingAmount.toFixed(2)),
          payment_breakdown: breakdown,
          notes: notes?.trim() || undefined,
        },
        reason.trim(),
      );
      setMessage("Caja cerrada exitosamente.");
      setCashSessions((current) =>
        current.map((session) => (session.id === closed.id ? closed : session)),
      );
      setPayment((current) => ({ ...current, cashSessionId: null }));
      await refreshCashSessions(selectedStoreId);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible cerrar la sesión de caja.",
      );
    }
  };

  const handleBreakdownChange = (method: PaymentMethod, value: number) => {
    setPayment((current) => ({
      ...current,
      paymentBreakdown: {
        ...current.paymentBreakdown,
        [method]: value < 0 || Number.isNaN(value) ? 0 : Number(value),
      },
    }));
  };

  const resetPaymentBreakdown = () => {
    setPayment((current) => ({
      ...current,
      paymentBreakdown: buildEmptyBreakdown(),
    }));
  };

  const handleAutoDistributeBreakdown = () => {
    setPayment((current) => {
      const next = buildEmptyBreakdown();
      if (totals.total > 0) {
        next[current.paymentMethod] = Number(totals.total.toFixed(2));
      }
      return {
        ...current,
        paymentBreakdown: next,
      };
    });
  };

  const handleRefreshCashHistory = () => {
    if (selectedStoreId) {
      void refreshCashSessions(selectedStoreId);
    }
  };

  const updatePayment = (updates: Partial<PaymentState>) => {
    setPayment((current) => ({ ...current, ...updates }));
  };

  const paymentModalProps: PaymentModalProps = {
    paymentMethod: payment.paymentMethod,
    onPaymentMethodChange: (method) => updatePayment({ paymentMethod: method }),
    customerId: payment.customerId,
    customerName: payment.customerName,
    onCustomerNameChange: (value) => updatePayment({ customerName: value }),
    customerOptions,
    customerSearch,
    onCustomerSearchChange: setCustomerSearch,
    onCustomerSelect: (value) =>
      updatePayment({
        customerId: value,
        customerName:
          value !== null
            ? customerOptions.find((candidate) => candidate.id === value)?.name ?? ""
            : "",
      }),
    onQuickCreateCustomer: handleQuickCustomerCreate,
    selectedCustomer,
    customerLoading,
    notes: payment.notes,
    onNotesChange: (value) => updatePayment({ notes: value }),
    globalDiscount: payment.discountPercent,
    onGlobalDiscountChange: (value) =>
      updatePayment({ discountPercent: Number(value) }),
    applyTaxes: payment.applyTaxes,
    onToggleTaxes: (value) => updatePayment({ applyTaxes: value }),
    reason: payment.reason,
    onReasonChange: (value) => updatePayment({ reason: value }),
    confirmChecked: payment.confirm,
    onConfirmChange: (value) => updatePayment({ confirm: value }),
    cashSessionId: payment.cashSessionId,
    cashSessions,
    onCashSessionChange: (sessionId) => updatePayment({ cashSessionId: sessionId }),
    onOpenCashSession: handleOpenCashSession,
    onCloseCashSession: handleCloseCashSession,
    cashLoading,
    paymentBreakdown: payment.paymentBreakdown,
    onPaymentBreakdownChange: handleBreakdownChange,
    onAutoDistributeBreakdown: handleAutoDistributeBreakdown,
    onResetBreakdown: resetPaymentBreakdown,
    activeCashSessionId: activeCashSession?.id ?? null,
    totals,
    disabled: cartIsEmpty || !selectedStoreId,
    loading: isSubmitting,
    onSubmit: handleSubmitSale,
    warnings: combinedWarnings,
  };

  const quickSaleState: QuickSaleState = {
    stores,
    selectedStoreId,
    onStoreChange: setSelectedStoreId,
    search,
    onSearchChange: setSearch,
    searchDisabled: !selectedStoreId || configLoading,
  };

  const productGridState: ProductGridState = {
    quickDevices,
    filteredDevices,
    disabled: !selectedStoreId,
    onDeviceSelect: handleAddDevice,
  };

  const cartState: CartState = {
    items: cart,
    onUpdate: handleUpdateCart,
    onRemove: handleRemoveCart,
    totals,
    hasTaxes: payment.applyTaxes,
    globalDiscount: payment.discountPercent,
  };

  const cashHistoryState: CashHistoryState = {
    sessions: cashSessions,
    loading: cashLoading,
    onRefresh: handleRefreshCashHistory,
    formatCurrency,
    formatDateTime,
    activeSessionId: activeCashSession?.id ?? null,
  };

  const receiptState: ReceiptState = {
    sale: lastSale,
    receiptUrl,
  };

  const settingsState: SettingsState = {
    config,
    devices,
    onSave: async (payload) => {
      setSaleWarnings([]);
      await handleSettingsSave(payload);
    },
    loading: settingsSaving,
  };

  const configReasonModalState: ConfigReasonModalState = {
    open: configReasonOpen,
    reason: configReason,
    onReasonChange: setConfigReason,
    error: configReasonError,
    submitting: configReasonSubmitting,
    onSubmit: submitConfigReason,
    onClose: closeConfigReasonDialog,
    pendingPayload: pendingConfigPayload,
  };

  return {
    alerts: { message, error },
    quickSale: quickSaleState,
    productGrid: productGridState,
    cart: cartState,
    paymentModal: paymentModalProps,
    cashHistory: cashHistoryState,
    receipt: receiptState,
    settings: settingsState,
    configReasonModal: configReasonModalState,
  };
}

