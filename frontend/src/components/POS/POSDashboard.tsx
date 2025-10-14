import { useCallback, useEffect, useMemo, useState } from "react";
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
} from "../../api";
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
} from "../../api";
import POSCart, { CartLine } from "./POSCart";
import POSPayment from "./POSPayment";
import POSReceipt from "./POSReceipt";
import POSSettings from "./POSSettings";

type Props = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

const PAYMENT_METHODS: PaymentMethod[] = [
  "EFECTIVO",
  "TARJETA",
  "TRANSFERENCIA",
  "CREDITO",
  "OTRO",
];

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

function POSDashboard({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(defaultStoreId ?? null);
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
  const [submittingMode, setSubmittingMode] = useState<"draft" | "sale" | null>(null);
  const [saleWarnings, setSaleWarnings] = useState<string[]>([]);
  const [customerOptions, setCustomerOptions] = useState<Customer[]>([]);
  const [customerSearch, setCustomerSearch] = useState("");
  const [customerLoading, setCustomerLoading] = useState(false);
  const [cashSessions, setCashSessions] = useState<CashSession[]>([]);
  const [cashLoading, setCashLoading] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

  const refreshCustomers = useCallback(
    async (query?: string) => {
      try {
        setCustomerLoading(true);
        const normalized = query?.trim();
        const data = await listCustomers(
          token,
          normalized && normalized.length > 0 ? normalized : undefined,
          100
        );
        setCustomerOptions(data);
      } catch (err) {
        setError((current) =>
          current ?? "No fue posible cargar los clientes corporativos."
        );
      } finally {
        setCustomerLoading(false);
      }
    },
    [token]
  );

  const refreshCashSessions = useCallback(
    async (storeId: number) => {
      try {
        setCashLoading(true);
        const history = await listCashSessions(token, storeId, 20);
        setCashSessions(history);
      } catch (err) {
        setError((current) => current ?? "No fue posible cargar las sesiones de caja.");
      } finally {
        setCashLoading(false);
      }
    },
    [token]
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
      const found = customerOptions.find((candidate) => candidate.id === payment.customerId);
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
        setError(err instanceof Error ? err.message : "No fue posible cargar la información POS.");
      } finally {
        setConfigLoading(false);
      }
    };
    loadStoreContext();
    void refreshCustomers();
  }, [selectedStoreId, token, refreshCashSessions, refreshCustomers]);

  const filteredDevices = useMemo(() => {
    const query = search.trim().toLowerCase();
    const collection = devices;
    if (!query) {
      return collection.slice(0, 6);
    }
    return collection
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
    [cashSessions]
  );

  const cartWarnings = useMemo(() =>
    cart
      .filter((line) => line.quantity > line.device.quantity)
      .map(
        (line) =>
          `No hay suficiente stock de ${line.device.sku}. Disponible: ${line.device.quantity}, solicitado: ${line.quantity}.`
      ),
  [cart]);

  const totals = useMemo(() => {
    if (cart.length === 0) {
      return { subtotal: 0, tax: 0, total: 0 };
    }
    const globalDiscount = payment.discountPercent;
    let subtotal = 0;
    cart.forEach((line) => {
      const price = line.device.unit_price ?? 0;
      const base = price * line.quantity;
      const lineDiscountPercent = line.discountPercent > 0 ? line.discountPercent : globalDiscount;
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
  const formatCurrency = (value: number) =>
    value.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const formatDateTime = (value?: string | null) =>
    value ? new Date(value).toLocaleString("es-MX") : "—";

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
          line.device.id === device.id ? { ...line, quantity: line.quantity + 1 } : line
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
          : line
      )
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
      const sanitizedBreakdown = PAYMENT_METHODS.reduce<Record<string, number>>((acc, method) => {
        const value = Number(payment.paymentBreakdown[method] ?? 0);
        if (!Number.isFinite(value)) {
          return acc;
        }
        const normalized = Number(value.toFixed(2));
        if (normalized > 0) {
          acc[method] = normalized;
        }
        return acc;
      }, {});
      if (mode === "sale") {
        const breakdownTotal = Object.values(sanitizedBreakdown).reduce(
          (acc, value) => acc + value,
          0
        );
        if (breakdownTotal === 0 && totals.total > 0) {
          sanitizedBreakdown[payment.paymentMethod] = Number(totals.total.toFixed(2));
        } else if (Math.abs(breakdownTotal - totals.total) > 0.5) {
          setError("El desglose de pago debe coincidir con el total a cobrar.");
          return;
        }
      }
      const resolvedCustomerName = payment.customerName.trim() || selectedCustomer?.name || undefined;
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
      setError(err instanceof Error ? err.message : "No fue posible registrar la venta POS.");
    } finally {
      setSubmittingMode(null);
    }
  };

  const handleSettingsSave = async (payload: PosConfigUpdateInput) => {
    try {
      setSettingsSaving(true);
      const reason = window.prompt(
        "Motivo corporativo para actualizar la configuración POS",
        "Ajuste configuración POS"
      );
      if (!reason || reason.trim().length < 5) {
        throw new Error("Debes indicar un motivo válido para registrar la configuración.");
      }
      const updated = await updatePosConfig(token, payload, reason.trim());
      setConfig(updated);
      setMessage("Configuración POS actualizada.");
    } finally {
      setSettingsSaving(false);
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
      "Alta cliente POS"
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
        reason.trim()
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
          : "No fue posible registrar al cliente desde el POS."
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
      "Apertura turno POS"
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
        reason.trim()
      );
      setMessage("Caja abierta correctamente.");
      setCashSessions((current) => [session, ...current]);
      setPayment((current) => ({ ...current, cashSessionId: session.id }));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible abrir la sesión de caja."
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
      String(Number(activeCashSession.expected_amount ?? 0).toFixed(2))
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
        String(Number(previousValue).toFixed(2))
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
      "Cierre de caja POS"
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
        reason.trim()
      );
      setMessage("Caja cerrada exitosamente.");
      setCashSessions((current) =>
        current.map((session) => (session.id === closed.id ? closed : session))
      );
      setPayment((current) => ({ ...current, cashSessionId: null }));
      await refreshCashSessions(selectedStoreId);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible cerrar la sesión de caja."
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

  const totalsForCart = useMemo(() => totals, [totals]);

  return (
    <div className="section-grid pos-touch-area">
      <section className="card wide">
        <h2>Venta directa POS</h2>
        <p className="card-subtitle">
          Busca dispositivos por IMEI, modelo o nombre y controla stock, impuestos y recibos en un solo flujo.
        </p>
        {message ? <div className="alert success">{message}</div> : null}
        {error ? <div className="alert error">{error}</div> : null}
        <div className="form-grid">
          <label>
            Sucursal
            <select
              value={selectedStoreId ?? ""}
              onChange={(event) => setSelectedStoreId(event.target.value ? Number(event.target.value) : null)}
            >
              <option value="">Selecciona una sucursal</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Buscar producto
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="IMEI, nombre o modelo"
              disabled={!selectedStoreId || configLoading}
            />
          </label>
        </div>
        {quickDevices.length > 0 ? (
          <div className="quick-actions">
            <span className="muted-text">Venta rápida:</span>
            {quickDevices.map((device) => (
              <button
                type="button"
                key={device.id}
                className="button ghost"
                onClick={() => handleAddDevice(device)}
                disabled={!selectedStoreId}
              >
                {device.sku}
              </button>
            ))}
          </div>
        ) : null}
        <div className="quick-actions">
          {filteredDevices.map((device) => (
            <button
              type="button"
              key={device.id}
              className="button secondary"
              onClick={() => handleAddDevice(device)}
              disabled={!selectedStoreId}
            >
              {device.sku} · {device.name}
            </button>
          ))}
        </div>
      </section>
      <POSCart
        items={cart}
        onUpdate={handleUpdateCart}
        onRemove={handleRemoveCart}
        totals={totalsForCart}
        hasTaxes={payment.applyTaxes}
        globalDiscount={payment.discountPercent}
      />
      <POSPayment
        paymentMethod={payment.paymentMethod}
        onPaymentMethodChange={(method) => setPayment((current) => ({ ...current, paymentMethod: method }))}
        customerId={payment.customerId}
        customerName={payment.customerName}
        onCustomerNameChange={(value) => setPayment((current) => ({ ...current, customerName: value }))}
        customerOptions={customerOptions}
        customerSearch={customerSearch}
        onCustomerSearchChange={setCustomerSearch}
        onCustomerSelect={(value) =>
          setPayment((current) => ({
            ...current,
            customerId: value,
            customerName:
              value !== null
                ? customerOptions.find((candidate) => candidate.id === value)?.name ?? ""
                : "",
          }))
        }
        onQuickCreateCustomer={handleQuickCustomerCreate}
        selectedCustomer={selectedCustomer}
        customerLoading={customerLoading}
        notes={payment.notes}
        onNotesChange={(value) => setPayment((current) => ({ ...current, notes: value }))}
        globalDiscount={payment.discountPercent}
        onGlobalDiscountChange={(value) => setPayment((current) => ({ ...current, discountPercent: value }))}
        applyTaxes={payment.applyTaxes}
        onToggleTaxes={(value) => setPayment((current) => ({ ...current, applyTaxes: value }))}
        reason={payment.reason}
        onReasonChange={(value) => setPayment((current) => ({ ...current, reason: value }))}
        confirmChecked={payment.confirm}
        onConfirmChange={(value) => setPayment((current) => ({ ...current, confirm: value }))}
        cashSessionId={payment.cashSessionId}
        cashSessions={cashSessions}
        onCashSessionChange={(sessionId) =>
          setPayment((current) => ({
            ...current,
            cashSessionId: sessionId,
          }))
        }
        onOpenCashSession={handleOpenCashSession}
        onCloseCashSession={handleCloseCashSession}
        cashLoading={cashLoading}
        paymentBreakdown={payment.paymentBreakdown}
        onPaymentBreakdownChange={handleBreakdownChange}
        onAutoDistributeBreakdown={handleAutoDistributeBreakdown}
        onResetBreakdown={() =>
          setPayment((current) => ({
            ...current,
            paymentBreakdown: buildEmptyBreakdown(),
          }))
        }
        activeCashSessionId={activeCashSession?.id ?? null}
        totals={totalsForCart}
        disabled={cartIsEmpty || !selectedStoreId}
        loading={isSubmitting}
        onSubmit={handleSubmitSale}
        warnings={combinedWarnings}
      />
      <section className="card">
        <h3>Arqueos de caja POS</h3>
        <p className="card-subtitle">
          Controla aperturas, cierres y diferencias por sucursal para cuadrar el efectivo cada turno.
        </p>
        <div className="actions-row">
          <button
            type="button"
            className="button ghost"
            onClick={handleRefreshCashHistory}
            disabled={!selectedStoreId || cashLoading}
          >
            Actualizar historial
          </button>
        </div>
        {cashSessions.length === 0 ? (
          <p className="muted-text">
            Registra una apertura de caja para iniciar el historial de arqueos de esta sucursal.
          </p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Sesión</th>
                  <th>Estado</th>
                  <th>Apertura</th>
                  <th>Cierre</th>
                  <th>Esperado</th>
                  <th>Diferencia</th>
                  <th>Pagos registrados</th>
                  <th>Abierta</th>
                  <th>Cerrada</th>
                </tr>
              </thead>
              <tbody>
                {cashSessions.slice(0, 8).map((session) => {
                  const breakdownEntries = Object.entries(session.payment_breakdown ?? {})
                    .filter(([, value]) => Number(value) > 0)
                    .map(
                      ([method, value]) => `${method}: $${formatCurrency(Number(value))}`
                    );
                  const breakdownText = breakdownEntries.length > 0 ? breakdownEntries.join(" · ") : "—";
                  const differenceFlag = Math.abs(Number(session.difference_amount ?? 0)) > 0.01;
                  return (
                    <tr key={session.id}>
                      <td>#{session.id}</td>
                      <td>{session.status === "ABIERTO" ? "Abierta" : "Cerrada"}</td>
                      <td>${formatCurrency(Number(session.opening_amount ?? 0))}</td>
                      <td>
                        {session.status === "ABIERTO"
                          ? "—"
                          : `$${formatCurrency(Number(session.closing_amount ?? 0))}`}
                      </td>
                      <td>${formatCurrency(Number(session.expected_amount ?? 0))}</td>
                      <td>
                        ${formatCurrency(Number(session.difference_amount ?? 0))}
                        {differenceFlag ? " ⚠️" : ""}
                      </td>
                      <td>{breakdownText}</td>
                      <td>{formatDateTime(session.opened_at)}</td>
                      <td>{formatDateTime(session.closed_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <POSReceipt token={token} sale={lastSale} receiptUrl={receiptUrl} />
      <POSSettings
        config={config}
        devices={devices}
        onSave={async (payload) => {
          setSaleWarnings([]);
          await handleSettingsSave(payload);
        }}
        loading={settingsSaving}
      />
    </div>
  );
}

export default POSDashboard;
