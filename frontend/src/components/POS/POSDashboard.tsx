import { useEffect, useMemo, useState } from "react";
import type {
  Device,
  PosConfig,
  PosConfigUpdateInput,
  PosSalePayload,
  Sale,
  Store,
} from "../../api";
import {
  getDevices,
  getPosConfig,
  submitPosSale,
  updatePosConfig,
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

type PaymentState = {
  paymentMethod: "EFECTIVO" | "TARJETA" | "TRANSFERENCIA" | "OTRO" | "CREDITO";
  customerName: string;
  notes: string;
  discountPercent: number;
  applyTaxes: boolean;
  reason: string;
  confirm: boolean;
};

const initialPayment: PaymentState = {
  paymentMethod: "EFECTIVO",
  customerName: "",
  notes: "",
  discountPercent: 0,
  applyTaxes: true,
  reason: "Venta mostrador",
  confirm: false,
};

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
  const [payment, setPayment] = useState<PaymentState>({ ...initialPayment });
  const [lastSale, setLastSale] = useState<Sale | null>(null);
  const [receiptUrl, setReceiptUrl] = useState<string | null>(null);
  const [draftId, setDraftId] = useState<number | null>(null);
  const [submittingMode, setSubmittingMode] = useState<"draft" | "sale" | null>(null);
  const [saleWarnings, setSaleWarnings] = useState<string[]>([]);

  useEffect(() => {
    setSelectedStoreId(defaultStoreId ?? null);
  }, [defaultStoreId]);

  useEffect(() => {
    if (!selectedStoreId) {
      setDevices([]);
      setConfig(null);
      setCart([]);
      setDraftId(null);
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
        setPayment((current) => ({ ...current, applyTaxes: storeConfig.tax_rate > 0 }));
        setDraftId(null);
        setCart([]);
        setMessage(null);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar la información POS.");
      } finally {
        setConfigLoading(false);
      }
    };
    loadStoreContext();
  }, [selectedStoreId, token]);

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
    setPayment({ ...initialPayment, applyTaxes: payment.applyTaxes, reason: payment.reason });
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
    try {
      setSubmittingMode(mode);
      setMessage(null);
      setError(null);
      const payload: PosSalePayload = {
        store_id: selectedStoreId,
        payment_method: payment.paymentMethod,
        items: cart.map((line) => ({
          device_id: line.device.id,
          quantity: line.quantity,
          discount_percent: line.discountPercent,
        })),
        discount_percent: payment.discountPercent,
        customer_name: payment.customerName || undefined,
        notes: payment.notes || undefined,
        confirm: mode === "sale",
        save_as_draft: mode === "draft",
        draft_id: draftId ?? undefined,
        apply_taxes: payment.applyTaxes,
      };
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

  const totalsForCart = useMemo(() => totals, [totals]);

  return (
    <div className="section-grid">
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
        customerName={payment.customerName}
        onCustomerNameChange={(value) => setPayment((current) => ({ ...current, customerName: value }))}
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
        totals={totalsForCart}
        disabled={cartIsEmpty || !selectedStoreId}
        loading={isSubmitting}
        onSubmit={handleSubmitSale}
        warnings={combinedWarnings}
      />
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
