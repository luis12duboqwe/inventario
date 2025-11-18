import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import type {
  PurchaseOrder,
  PurchaseOrderCreateInput,
  PurchaseReturn,
  PurchaseReturnInput,
  PurchaseSuggestionStore,
  PurchaseSuggestionsResponse,
  ReturnDisposition,
  ReturnReasonCategory,
  Store,
} from "../../api";
import {
  createPurchaseOrderFromSuggestion,
  getStores,
  getPurchaseSuggestions,
  listPurchaseOrders,
  registerPurchaseReturn,
} from "../../api";
import { useAuth } from "../../auth/useAuth";
import { promptCorporateReason } from "../../utils/corporateReason";

const reasonLabels: Record<PurchaseSuggestionStore["items"][number]["reason"], string> = {
  below_minimum: "Stock por debajo del mínimo",
  projected_consumption: "Cobertura insuficiente",
};

const dispositionOptions: { value: ReturnDisposition; label: string }[] = [
  { value: "vendible", label: "Vendible" },
  { value: "defectuoso", label: "Defectuoso" },
  { value: "no_vendible", label: "No vendible" },
  { value: "reparacion", label: "En revisión" },
];

const categoryOptions: { value: ReturnReasonCategory; label: string }[] = [
  { value: "defecto", label: "Falla de calidad" },
  { value: "logistica", label: "Logística / envío" },
  { value: "cliente", label: "Cambio del cliente" },
  { value: "precio", label: "Ajuste comercial" },
  { value: "otro", label: "Otro" },
];

type PurchaseReturnDraft = {
  storeId: number | null;
  orderId: number | null;
  deviceId: number | null;
  quantity: number;
  reason: string;
  disposition: ReturnDisposition;
  category: ReturnReasonCategory;
  warehouseId: number | null;
};

type SuggestionDraftItem = {
  deviceId: number;
  sku: string;
  name: string;
  quantity: number;
  unitCost: number;
};

type SuggestionDraft = {
  storeId: number;
  storeName: string;
  supplier: string;
  items: SuggestionDraftItem[];
};

const initialReturnDraft: PurchaseReturnDraft = {
  storeId: null,
  orderId: null,
  deviceId: null,
  quantity: 1,
  reason: "Proveedor defectuoso",
  disposition: "defectuoso",
  category: "defecto",
  warehouseId: null,
};

function buildDraft(store: PurchaseSuggestionStore): SuggestionDraft {
  const supplier = store.items.find((item) => item.supplier_name)?.supplier_name ?? "";
  return {
    storeId: store.store_id,
    storeName: store.store_name,
    supplier,
    items: store.items.map((item) => ({
      deviceId: item.device_id,
      sku: item.sku,
      name: item.name,
      quantity: item.suggested_quantity,
      unitCost: item.unit_cost,
    })),
  };
}

function Purchases() {
  const { accessToken } = useAuth();
  const [suggestions, setSuggestions] = useState<PurchaseSuggestionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [draft, setDraft] = useState<SuggestionDraft | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [stores, setStores] = useState<Store[]>([]);
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [returnForm, setReturnForm] = useState<PurchaseReturnDraft>(initialReturnDraft);
  const [returnSubmitting, setReturnSubmitting] = useState(false);
  const [returnError, setReturnError] = useState<string | null>(null);
  const [returnMessage, setReturnMessage] = useState<string | null>(null);
  const [returnDocument, setReturnDocument] = useState<{ url: string; filename: string } | null>(null);

  const currency = useMemo(
    () => new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" }),
    [],
  );

  const fetchSuggestions = useCallback(async () => {
    if (!accessToken) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await getPurchaseSuggestions(accessToken);
      setSuggestions(response);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "No fue posible cargar las sugerencias de compra.";
      setError(message);
      setSuggestions(null);
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  const resetReturnFeedback = useCallback(() => {
    setReturnError(null);
    setReturnMessage(null);
  }, []);

  useEffect(() => {
    if (!accessToken) {
      setStores([]);
      return;
    }
    let active = true;
    getStores(accessToken)
      .then((data) => {
        if (active) {
          setStores(data);
        }
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        const message =
          err instanceof Error
            ? err.message
            : "No fue posible cargar las sucursales.";
        setReturnError((current) => current ?? message);
      });
    return () => {
      active = false;
    };
  }, [accessToken]);

  const fetchOrders = useCallback(
    async (storeId: number) => {
      if (!accessToken) {
        return;
      }
      try {
        const data = await listPurchaseOrders(accessToken, storeId, 100);
        setOrders(data);
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "No fue posible cargar las órdenes de compra.";
        setReturnError(message);
        setOrders([]);
      }
    },
    [accessToken],
  );

  useEffect(() => {
    if (!returnForm.storeId || !accessToken) {
      setOrders([]);
      return;
    }
    resetReturnFeedback();
    void fetchOrders(returnForm.storeId);
  }, [returnForm.storeId, accessToken, fetchOrders, resetReturnFeedback]);

  useEffect(() => () => {
    if (returnDocument) {
      URL.revokeObjectURL(returnDocument.url);
    }
  }, [returnDocument]);

  const handleOpenDraft = (store: PurchaseSuggestionStore) => {
    setDraft(buildDraft(store));
    setError(null);
    setMessage(null);
  };

  const handleCloseDraft = () => {
    setDraft(null);
  };

  const handleSupplierChange = (value: string) => {
    setDraft((current) => (current ? { ...current, supplier: value } : current));
  };

  const handleUpdateItem = (deviceId: number, field: "quantity" | "unitCost", value: number) => {
    setDraft((current) => {
      if (!current) {
        return current;
      }
      const items = current.items.map((item) =>
        item.deviceId === deviceId
          ? {
              ...item,
              [field]: value,
            }
          : item,
      );
      return { ...current, items };
    });
  };

  const draftTotal = useMemo(() => {
    if (!draft) {
      return 0;
    }
    return draft.items.reduce((sum, item) => sum + item.quantity * item.unitCost, 0);
  }, [draft]);

  const resolveAvailableQuantity = useCallback(
    (orderId: number | null, deviceId: number | null) => {
      if (!orderId || !deviceId) {
        return 0;
      }
      const order = orders.find((item) => item.id === orderId);
      if (!order) {
        return 0;
      }
      const item = order.items.find((entry) => entry.device_id === deviceId);
      if (!item) {
        return 0;
      }
      const returned = order.returns
        .filter((entry) => entry.device_id === deviceId)
        .reduce((sum, entry) => sum + entry.quantity, 0);
      return Math.max(0, item.quantity_received - returned);
    },
    [orders],
  );

  const selectedStore = useMemo(() => {
    if (returnForm.storeId == null) {
      return null;
    }
    return stores.find((store) => store.id === returnForm.storeId) ?? null;
  }, [stores, returnForm.storeId]);

  const selectedOrder = useMemo(() => {
    if (returnForm.orderId == null) {
      return null;
    }
    return orders.find((order) => order.id === returnForm.orderId) ?? null;
  }, [orders, returnForm.orderId]);

  const selectedOrderItem = useMemo(() => {
    if (!selectedOrder || returnForm.deviceId == null) {
      return null;
    }
    return (
      selectedOrder.items.find((item) => item.device_id === returnForm.deviceId) ?? null
    );
  }, [selectedOrder, returnForm.deviceId]);

  const returnedQuantity = useMemo(() => {
    if (!selectedOrder || returnForm.deviceId == null) {
      return 0;
    }
    return selectedOrder.returns
      .filter((entry) => entry.device_id === returnForm.deviceId)
      .reduce((sum, entry) => sum + entry.quantity, 0);
  }, [selectedOrder, returnForm.deviceId]);

  const availableForReturn = useMemo(() => {
    if (!selectedOrderItem) {
      return 0;
    }
    return Math.max(0, selectedOrderItem.quantity_received - returnedQuantity);
  }, [selectedOrderItem, returnedQuantity]);

  const creditNotePreview = useMemo(() => {
    if (!selectedOrderItem || availableForReturn <= 0) {
      return 0;
    }
    const safeQuantity = Math.min(Math.max(0, returnForm.quantity), availableForReturn);
    return safeQuantity > 0 ? safeQuantity * selectedOrderItem.unit_cost : 0;
  }, [selectedOrderItem, availableForReturn, returnForm.quantity]);

  const handleReturnStoreChange = (value: string) => {
    const parsed = value ? Number(value) : NaN;
    const nextStoreId = Number.isNaN(parsed) ? null : parsed;
    resetReturnFeedback();
    setReturnForm({
      ...initialReturnDraft,
      storeId: nextStoreId,
    });
  };

  const handleReturnOrderChange = (value: string) => {
    const parsed = value ? Number(value) : NaN;
    const nextOrderId = Number.isNaN(parsed) ? null : parsed;
    resetReturnFeedback();
    setReturnForm((current) => ({
      ...current,
      orderId: nextOrderId,
      deviceId: null,
      quantity: 1,
    }));
  };

  const handleReturnDeviceChange = (value: string) => {
    const parsed = value ? Number(value) : NaN;
    const nextDeviceId = Number.isNaN(parsed) ? null : parsed;
    resetReturnFeedback();
    setReturnForm((current) => {
      const available = resolveAvailableQuantity(current.orderId, nextDeviceId);
      const nextQuantity = available > 0 ? Math.min(Math.max(1, current.quantity), available) : 0;
      return {
        ...current,
        deviceId: nextDeviceId,
        quantity: nextDeviceId ? nextQuantity : current.quantity,
      };
    });
  };

  const handleReturnQuantityChange = (value: number) => {
    setReturnForm((current) => {
      const available = resolveAvailableQuantity(current.orderId, current.deviceId);
      if (!Number.isFinite(value)) {
        return current;
      }
      const normalized = Math.max(0, Math.trunc(value));
      if (available > 0 && normalized > available) {
        return { ...current, quantity: available };
      }
      return { ...current, quantity: normalized };
    });
  };

  const handleReturnDispositionChange = (value: ReturnDisposition) => {
    setReturnForm((current) => ({ ...current, disposition: value }));
  };

  const handleReturnCategoryChange = (value: ReturnReasonCategory) => {
    setReturnForm((current) => ({ ...current, category: value }));
  };

  const handleReturnWarehouseChange = (value: string) => {
    const parsed = value ? Number(value) : NaN;
    setReturnForm((current) => ({
      ...current,
      warehouseId: Number.isNaN(parsed) ? null : parsed,
    }));
  };

  const handleReturnReasonChange = (value: string) => {
    setReturnForm((current) => ({ ...current, reason: value }));
  };

  const handleSubmitReturn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!accessToken) {
      return;
    }
    resetReturnFeedback();

    const { storeId, orderId, deviceId, quantity, reason: reasonText, disposition, category, warehouseId } =
      returnForm;
    if (!storeId || !orderId || !deviceId) {
      setReturnError("Selecciona la sucursal, la orden y el dispositivo a devolver.");
      return;
    }
    const order = orders.find((entry) => entry.id === orderId) ?? null;
    const available = resolveAvailableQuantity(orderId, deviceId);
    if (available <= 0) {
      setReturnError("No hay cantidad disponible para devolver de este artículo.");
      return;
    }
    const normalizedQuantity = Math.min(Math.max(1, Math.trunc(quantity)), available);
    if (normalizedQuantity <= 0) {
      setReturnError("Indica una cantidad válida para la devolución.");
      return;
    }
    const trimmedReason = reasonText.trim();
    if (trimmedReason.length < 5) {
      setReturnError("El motivo debe tener al menos 5 caracteres.");
      return;
    }
    const corporateReason = promptCorporateReason(
      `Devolución proveedor - ${order?.supplier ?? "Proveedor"}`,
    );
    const normalizedCorporate = corporateReason?.trim() ?? "";
    if (normalizedCorporate.length < 5) {
      setReturnError("Debes capturar un motivo corporativo válido (mínimo 5 caracteres).");
      return;
    }

    setReturnSubmitting(true);
    try {
      const response: PurchaseReturn = await registerPurchaseReturn(
        accessToken,
        orderId,
        {
          device_id: deviceId,
          quantity: normalizedQuantity,
          reason: trimmedReason,
          disposition,
          category,
          ...(warehouseId ? { warehouse_id: warehouseId } : {}),
        },
        normalizedCorporate,
      );

      const creditAmount = response.credit_note_amount ?? 0;
      const supplierLabel = order?.supplier ?? "Proveedor";
      setReturnMessage(
        `Devolución registrada para ${supplierLabel}. Nota de crédito por ${currency.format(creditAmount)}.`,
      );

      const documentLines = [
        "Softmobile 2025 v2.2.0 — Devolución a proveedor",
        `Fecha: ${new Date(response.created_at ?? Date.now()).toLocaleString("es-HN")}`,
        `Sucursal: ${selectedStore?.name ?? storeId}`,
        `Orden de compra: #${orderId}`,
        `Proveedor: ${supplierLabel}`,
        `Dispositivo ID: ${deviceId}`,
        `Cantidad devuelta: ${normalizedQuantity}`,
        `Nota de crédito: ${currency.format(creditAmount)}`,
        `Motivo técnico: ${trimmedReason}`,
        `Motivo corporativo: ${normalizedCorporate}`,
      ];
      const blob = new Blob([documentLines.join("\n")], {
        type: "text/plain;charset=utf-8",
      });
      if (returnDocument) {
        URL.revokeObjectURL(returnDocument.url);
      }
      setReturnDocument({
        url: URL.createObjectURL(blob),
        filename: `devolucion-${orderId}-${response.id}.txt`,
      });

      const remaining = Math.max(0, available - normalizedQuantity);
      await fetchOrders(storeId);
      setReturnForm((current) => ({
        ...current,
        quantity: remaining,
      }));
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "No fue posible registrar la devolución a proveedor.";
      setReturnError(message);
    } finally {
      setReturnSubmitting(false);
    }
  };

  const handleSubmitDraft = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draft || !accessToken) {
      return;
    }

    const normalizedSupplier = draft.supplier.trim();
    if (normalizedSupplier.length < 3) {
      setError("Indica un proveedor válido para la orden de compra.");
      return;
    }

    const items = draft.items
      .map((item) => ({
        device_id: item.deviceId,
        quantity_ordered: Math.max(0, Math.trunc(item.quantity)),
        unit_cost: Number.isFinite(item.unitCost) ? Number(item.unitCost) : 0,
      }))
      .filter((item) => item.quantity_ordered > 0);

    if (items.length === 0) {
      setError("Agrega al menos un artículo con cantidad mayor a cero.");
      return;
    }

    const reason = promptCorporateReason(`Generar PO automática - ${draft.storeName}`);
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo válido (mínimo 5 caracteres).");
      return;
    }

    const payload: PurchaseOrderCreateInput = {
      store_id: draft.storeId,
      supplier: normalizedSupplier,
      items,
    };

    setSubmitting(true);
    setError(null);
    try {
      const order: PurchaseOrder = await createPurchaseOrderFromSuggestion(
        accessToken,
        payload,
        reason,
      );
      setMessage(`Orden de compra #${order.id} generada para ${draft.storeName}.`);
      setDraft(null);
      await fetchSuggestions();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "No fue posible generar la orden automática.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRefresh = () => {
    fetchSuggestions();
  };

  const hasSuggestions = (suggestions?.stores.length ?? 0) > 0;

  return (
    <div className="module-content purchases-module" style={{ display: "grid", gap: 16 }}>
      <section className="card" style={{ display: "grid", gap: 12 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <h1 style={{ margin: 0 }}>Sugerencias de compra</h1>
          <p className="card-subtitle" style={{ margin: 0 }}>
            Consolidado por sucursal con base en umbrales mínimos y ventas recientes.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={handleRefresh}
            disabled={loading}
          >
            {loading ? "Actualizando…" : "Actualizar"}
          </button>
          {suggestions && (
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <span className="muted-text">
                Última generación: {new Date(suggestions.generated_at).toLocaleString("es-HN")}
              </span>
              <span className="muted-text">
                Umbral mínimo: {suggestions.minimum_stock} unidades · Horizonte: {suggestions.planning_horizon_days} días
              </span>
              <span className="muted-text">
                Sugerencias activas: {suggestions.total_items}
              </span>
            </div>
          )}
        </div>
        {message && (
          <div className="alert alert--success" role="status">
            {message}
          </div>
        )}
        {error && (
          <div className="alert alert--error" role="alert">
            {error}
          </div>
        )}
        {loading && <p className="muted-text">Cargando sugerencias de compra…</p>}
        {!loading && !hasSuggestions && (
          <p className="muted-text" style={{ margin: 0 }}>
            No hay sugerencias pendientes. El inventario actual cumple con los umbrales definidos.
          </p>
        )}
      </section>

      {!loading &&
        suggestions?.stores.map((store) => {
          const suggestedValue = currency.format(store.total_value);
          return (
            <section key={store.store_id} className="card" style={{ display: "grid", gap: 16 }}>
              <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h2 style={{ margin: 0 }}>{store.store_name}</h2>
                  <p className="card-subtitle" style={{ margin: 0 }}>
                    {store.total_suggested} unidades sugeridas · Valor estimado {suggestedValue}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => handleOpenDraft(store)}
                >
                  Generar PO
                </button>
              </header>

              <div className="table-responsive">
                <table>
                  <thead>
                    <tr>
                      <th>SKU</th>
                      <th>Producto</th>
                      <th>Proveedor sugerido</th>
                      <th>Stock actual</th>
                      <th>Venta diaria</th>
                      <th>Cobertura (días)</th>
                      <th>Sugerido</th>
                      <th>Motivo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {store.items.map((item) => (
                      <tr key={item.device_id}>
                        <td>{item.sku}</td>
                        <td>{item.name}</td>
                        <td>{item.supplier_name ?? "Sin proveedor"}</td>
                        <td>{item.current_quantity}</td>
                        <td>{item.average_daily_sales.toFixed(2)}</td>
                        <td>{item.projected_coverage_days ?? "—"}</td>
                        <td>
                          {item.suggested_quantity} ({currency.format(item.suggested_value)})
                        </td>
                        <td>{reasonLabels[item.reason]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          );
        })}

      <section className="card" style={{ display: "grid", gap: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <h2 style={{ margin: 0 }}>Devolución a proveedor</h2>
          <p className="card-subtitle" style={{ margin: 0 }}>
            Registra notas de crédito y ajusta inventario con motivo corporativo.
          </p>
        </div>
        {returnMessage && (
          <div className="alert alert--success" role="status">
            {returnMessage}
          </div>
        )}
        {returnError && (
          <div className="alert alert--error" role="alert">
            {returnError}
          </div>
        )}
        <form onSubmit={handleSubmitReturn} className="form-grid" style={{ gap: 12 }}>
          <label>
            Sucursal
            <select
              value={returnForm.storeId ?? ""}
              onChange={(event) => handleReturnStoreChange(event.target.value)}
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
            Orden de compra
            <select
              value={returnForm.orderId ?? ""}
              onChange={(event) => handleReturnOrderChange(event.target.value)}
              disabled={!returnForm.storeId || orders.length === 0}
            >
              <option value="">Selecciona una orden</option>
              {orders.map((order) => (
                <option key={order.id} value={order.id}>
                  #{order.id} · {order.supplier}
                </option>
              ))}
            </select>
          </label>
          <label>
            Dispositivo
            <select
              value={returnForm.deviceId ?? ""}
              onChange={(event) => handleReturnDeviceChange(event.target.value)}
              disabled={!returnForm.orderId}
            >
              <option value="">Selecciona un dispositivo</option>
              {selectedOrder?.items.map((item) => (
                <option key={item.id} value={item.device_id}>
                  #{item.device_id} · {item.quantity_received}/{item.quantity_ordered} recibidos
                </option>
              ))}
            </select>
          </label>
          <label>
            Cantidad a devolver
            <input
              type="number"
              min={0}
              value={returnForm.quantity}
              onChange={(event) => handleReturnQuantityChange(Number(event.target.value))}
              disabled={!returnForm.deviceId}
            />
            <span className="muted-text">
              Disponible: {availableForReturn} · Devuelto antes: {returnedQuantity}
            </span>
          </label>
          <label>
            Estado del lote
            <select
              value={returnForm.disposition}
              onChange={(event) => handleReturnDispositionChange(event.target.value as ReturnDisposition)}
            >
              {dispositionOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Categoría del motivo
            <select
              value={returnForm.category}
              onChange={(event) => handleReturnCategoryChange(event.target.value as ReturnReasonCategory)}
            >
              {categoryOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Almacén destino
            <select
              value={returnForm.warehouseId ?? ""}
              onChange={(event) => handleReturnWarehouseChange(event.target.value)}
            >
              <option value="">Mantener en sucursal</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </label>
          <label className="form-span">
            Motivo técnico
            <input
              type="text"
              value={returnForm.reason}
              onChange={(event) => handleReturnReasonChange(event.target.value)}
              placeholder="Describe el motivo técnico"
              maxLength={255}
            />
          </label>
          <p className="muted-text form-span" style={{ margin: 0 }}>
            Nota de crédito estimada: {currency.format(creditNotePreview || 0)}
          </p>
          <div className="form-span" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="submit" className="btn btn--primary" disabled={returnSubmitting}>
              {returnSubmitting ? "Registrando…" : "Registrar devolución"}
            </button>
          </div>
        </form>
        {returnDocument ? (
          <a
            className="btn btn--secondary"
            href={returnDocument.url}
            download={returnDocument.filename}
          >
            Descargar comprobante generado
          </a>
        ) : null}
      </section>

      {draft && (
        <section className="card" style={{ display: "grid", gap: 16 }}>
          <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h2 style={{ margin: 0 }}>Generar orden sugerida</h2>
              <p className="card-subtitle" style={{ margin: 0 }}>
                {draft.storeName} · Valor estimado {currency.format(draftTotal)}
              </p>
            </div>
            <button type="button" className="btn btn--ghost" onClick={handleCloseDraft}>
              Cancelar
            </button>
          </header>

          <form onSubmit={handleSubmitDraft} className="form-grid" style={{ gap: 12 }}>
            <label className="form-span">
              Proveedor
              <input
                type="text"
                value={draft.supplier}
                onChange={(event) => handleSupplierChange(event.target.value)}
                placeholder="Proveedor corporativo"
                minLength={3}
                required
              />
            </label>

            <div className="table-responsive form-span">
              <table>
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Producto</th>
                    <th>Cantidad</th>
                    <th>Costo unitario MXN</th>
                  </tr>
                </thead>
                <tbody>
                  {draft.items.map((item) => (
                    <tr key={item.deviceId}>
                      <td>{item.sku}</td>
                      <td>{item.name}</td>
                      <td>
                        <input
                          type="number"
                          min={0}
                          value={item.quantity}
                          onChange={(event) =>
                            handleUpdateItem(item.deviceId, "quantity", Number(event.target.value))
                          }
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          min={0}
                          step={0.01}
                          value={item.unitCost}
                          onChange={(event) =>
                            handleUpdateItem(item.deviceId, "unitCost", Number(event.target.value))
                          }
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="form-actions" style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button type="submit" className="btn btn--primary" disabled={submitting}>
                {submitting ? "Generando…" : "Confirmar orden"}
              </button>
              <button type="button" className="btn" onClick={handleCloseDraft}>
                Cerrar
              </button>
            </div>
          </form>
        </section>
      )}
    </div>
  );
}

export default Purchases;
