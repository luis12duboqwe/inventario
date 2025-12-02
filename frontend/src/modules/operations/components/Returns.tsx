import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import type { PurchaseOrder } from "@api/purchases";
import { listPurchaseOrders, registerPurchaseReturn } from "@api/purchases";
import type {
  ReturnDisposition,
  ReturnReasonCategory,
  ReturnRecord,
  ReturnsTotals,
  Sale,
} from "@api/sales";
import { listReturns, listSales, registerSaleReturn } from "@api/sales";
import type { Store } from "@api/inventory";
import ReturnsSearch from "./ReturnsSearch";

type Props = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

type PurchaseReturnForm = {
  storeId: number | null;
  orderId: number | null;
  deviceId: number | null;
  quantity: number;
  reason: string;
  disposition: ReturnDisposition;
  warehouseId: number | null;
  category: ReturnReasonCategory;
};

type SaleReturnForm = {
  storeId: number | null;
  saleId: number | null;
  deviceId: number | null;
  quantity: number;
  reason: string;
  disposition: ReturnDisposition;
  warehouseId: number | null;
  category: ReturnReasonCategory;
  supervisorUsername: string;
  supervisorPin: string;
};

const initialPurchaseReturn: PurchaseReturnForm = {
  storeId: null,
  orderId: null,
  deviceId: null,
  quantity: 1,
  reason: "Falla de calidad",
  disposition: "defectuoso",
  warehouseId: null,
  category: "defecto",
};

const initialSaleReturn: SaleReturnForm = {
  storeId: null,
  saleId: null,
  deviceId: null,
  quantity: 1,
  reason: "Cambio del cliente",
  disposition: "vendible",
  warehouseId: null,
  category: "cliente",
  supervisorUsername: "",
  supervisorPin: "",
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

function dispositionLabel(value: ReturnDisposition): string {
  const match = dispositionOptions.find((option) => option.value === value);
  return match ? match.label : value;
}

function categoryLabel(value: ReturnReasonCategory | string): string {
  const match = categoryOptions.find((option) => option.value === value);
  return match ? match.label : value;
}
const initialHistoryTotals: ReturnsTotals = {
  total: 0,
  sales: 0,
  purchases: 0,
  refunds_by_method: {},
  refund_total_amount: 0,
  credit_notes_total: 0,
  categories: {},
};

function Returns({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  // Para evitar setState en efectos cuando cambia defaultStoreId,
  // se remonta un subcomponente con key basada en el defaultStoreId.
  return (
    <ReturnsInner
      key={String(defaultStoreId ?? "none")}
      token={token}
      stores={stores}
      defaultStoreId={defaultStoreId}
      {...(onInventoryRefresh ? { onInventoryRefresh } : {})}
    />
  );
}

function ReturnsInner({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [sales, setSales] = useState<Sale[]>([]);
  const [purchaseForm, setPurchaseForm] = useState<PurchaseReturnForm>(() => ({
    ...initialPurchaseReturn,
    storeId: defaultStoreId,
  }));
  const [saleForm, setSaleForm] = useState<SaleReturnForm>(() => ({
    ...initialSaleReturn,
    storeId: defaultStoreId,
  }));
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [historyStoreId, setHistoryStoreId] = useState<number | null>(defaultStoreId);
  const [history, setHistory] = useState<ReturnRecord[]>([]);
  const [historyTotals, setHistoryTotals] = useState<ReturnsTotals>(initialHistoryTotals);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [saleApprovalRequired, setSaleApprovalRequired] = useState(false);
  const [saleApprovalVisible, setSaleApprovalVisible] = useState(false);

  const parseErrorMessage = useCallback((message: string) => {
    const match = message.match(/^\[([^\]]+)]\s*(.*)$/);
    if (match) {
      return { code: match[1], text: match[2] || match[1] };
    }
    return { code: null, text: message };
  }, []);

  const formatCurrency = useCallback(
    (value: number) =>
      value.toLocaleString("es-HN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    [],
  );

  const selectedPurchaseOrder = useMemo(
    () => purchaseOrders.find((order) => order.id === purchaseForm.orderId) ?? null,
    [purchaseOrders, purchaseForm.orderId],
  );

  const selectedSale = useMemo(
    () => sales.find((sale) => sale.id === saleForm.saleId) ?? null,
    [sales, saleForm.saleId],
  );

  const showSupervisorFields =
    saleApprovalVisible ||
    saleApprovalRequired ||
    saleForm.supervisorUsername.trim().length > 0 ||
    saleForm.supervisorPin.trim().length > 0;

  const refreshOrders = useCallback(
    async (storeId?: number | null) => {
      if (!storeId) {
        setPurchaseOrders([]);
        return;
      }
      try {
        const data = await listPurchaseOrders(token, storeId);
        setPurchaseOrders(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "No fue posible cargar las órdenes de compra",
        );
      }
    },
    [token],
  );

  const refreshSales = useCallback(
    async (storeId?: number | null) => {
      if (!storeId) {
        setSales([]);
        return;
      }
      try {
        const data = await listSales(token, { storeId, limit: 100 });
        setSales(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar las ventas");
      }
    },
    [token],
  );

  useEffect(() => {
    // Evita setState sincrónico en el efecto
    Promise.resolve().then(() => {
      void refreshOrders(purchaseForm.storeId ?? undefined);
    });
  }, [purchaseForm.storeId, refreshOrders]);

  useEffect(() => {
    // Evita setState sincrónico en el efecto
    Promise.resolve().then(() => {
      void refreshSales(saleForm.storeId ?? undefined);
    });
  }, [saleForm.storeId, refreshSales]);

  const refreshHistory = useCallback(
    async (storeId?: number | null) => {
      setHistoryLoading(true);
      try {
        const overview = await listReturns(token, {
          ...(typeof storeId === "number" ? { storeId } : {}),
          limit: 25,
        });
        setHistory(overview.items);
        const totals = overview.totals ?? initialHistoryTotals;
        setHistoryTotals({
          ...initialHistoryTotals,
          ...totals,
          refunds_by_method: totals.refunds_by_method ?? {},
          categories: totals.categories ?? {},
          refund_total_amount: totals.refund_total_amount ?? 0,
        });
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "No fue posible cargar el historial de devoluciones",
        );
      } finally {
        setHistoryLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    Promise.resolve().then(() => {
      void refreshHistory(historyStoreId);
    });
  }, [historyStoreId, refreshHistory]);

  const updatePurchaseForm = (updates: Partial<PurchaseReturnForm>) => {
    setPurchaseForm((current) => ({ ...current, ...updates }));
  };

  const updateSaleForm = (updates: Partial<SaleReturnForm>) => {
    setSaleForm((current) => ({ ...current, ...updates }));
  };

  const handlePurchaseReturn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!purchaseForm.storeId || !purchaseForm.orderId || !purchaseForm.deviceId) {
      setError("Selecciona orden y dispositivo para la devolución.");
      return;
    }
    if (!purchaseForm.reason.trim() || purchaseForm.reason.trim().length < 5) {
      setError("El motivo debe contener al menos 5 caracteres.");
      return;
    }
    try {
      setError(null);
      await registerPurchaseReturn(
        token,
        purchaseForm.orderId,
        {
          device_id: purchaseForm.deviceId,
          quantity: Math.max(1, purchaseForm.quantity),
          reason: purchaseForm.reason.trim(),
          disposition: purchaseForm.disposition,
          category: purchaseForm.category,
          ...(purchaseForm.warehouseId ? { warehouse_id: purchaseForm.warehouseId } : {}),
        },
        purchaseForm.reason.trim(),
      );
      setMessage("Devolución al proveedor registrada correctamente");
      await refreshOrders(purchaseForm.storeId);
      await refreshHistory(historyStoreId);
      onInventoryRefresh?.();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No fue posible registrar la devolución de compra",
      );
    }
  };

  const handleSaleReturn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!saleForm.storeId || !saleForm.saleId || !saleForm.deviceId) {
      setError("Selecciona la venta y el dispositivo a devolver.");
      return;
    }
    if (!saleForm.reason.trim() || saleForm.reason.trim().length < 5) {
      setError("El motivo debe contener al menos 5 caracteres.");
      return;
    }
    const trimmedReason = saleForm.reason.trim();
    const supervisorUsername = saleForm.supervisorUsername.trim();
    const supervisorPin = saleForm.supervisorPin.trim();
    const shouldSendApproval = saleApprovalVisible || saleApprovalRequired;
    if (saleApprovalRequired && (!supervisorUsername || !supervisorPin)) {
      setError("Captura el usuario y PIN del supervisor para autorizar la devolución.");
      return;
    }
    const approval =
      shouldSendApproval && supervisorUsername && supervisorPin
        ? { supervisor_username: supervisorUsername, pin: supervisorPin }
        : undefined;
    try {
      setError(null);
      await registerSaleReturn(
        token,
        {
          sale_id: saleForm.saleId,
          items: [
            {
              device_id: saleForm.deviceId,
              quantity: Math.max(1, saleForm.quantity),
              reason: trimmedReason,
              disposition: saleForm.disposition,
              category: saleForm.category,
              ...(saleForm.warehouseId ? { warehouse_id: saleForm.warehouseId } : {}),
            },
          ],
          ...(approval ? { approval } : {}),
        },
        trimmedReason,
      );
      setMessage("Devolución de cliente registrada correctamente");
      await refreshSales(saleForm.storeId);
      await refreshHistory(historyStoreId);
      onInventoryRefresh?.();
      setSaleForm((current) => ({
        ...current,
        supervisorUsername: "",
        supervisorPin: "",
      }));
      setSaleApprovalRequired(false);
      setSaleApprovalVisible(false);
    } catch (err) {
      const { code, text } = parseErrorMessage(
        err instanceof Error ? err.message : "No fue posible registrar la devolución de venta",
      );
      setError(text ?? null);
      if (code && code.startsWith("sale_return_supervisor_")) {
        setSaleApprovalVisible(true);
        if (code === "sale_return_supervisor_required") {
          setSaleApprovalRequired(true);
        }
      }
    }
  };

  return (
    <div className="returns-stack" data-testid="returns-list">
      <section className="card">
        <h2>Devoluciones y ajustes</h2>
        <p className="card-subtitle">
          Registra devoluciones a proveedores y reingresos de clientes para mantener la auditoría
          financiera.
        </p>
        {error ? <div className="alert error">{error}</div> : null}
        {message ? <div className="alert success">{message}</div> : null}

        <div className="returns-grid">
          <form onSubmit={handlePurchaseReturn}>
            <h3>Devolución a proveedor</h3>
            <label>
              Sucursal
              <select
                value={purchaseForm.storeId ?? ""}
                onChange={(event) =>
                  updatePurchaseForm({
                    storeId: event.target.value ? Number(event.target.value) : null,
                    orderId: null,
                    deviceId: null,
                    warehouseId: null,
                  })
                }
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
                value={purchaseForm.orderId ?? ""}
                onChange={(event) =>
                  updatePurchaseForm({
                    orderId: event.target.value ? Number(event.target.value) : null,
                    deviceId: null,
                  })
                }
                disabled={!purchaseForm.storeId}
              >
                <option value="">Selecciona una orden</option>
                {purchaseOrders.map((order) => (
                  <option key={order.id} value={order.id}>
                    #{order.id} · {order.supplier}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Dispositivo
              <select
                value={purchaseForm.deviceId ?? ""}
                onChange={(event) =>
                  updatePurchaseForm({
                    deviceId: event.target.value ? Number(event.target.value) : null,
                  })
                }
                disabled={!selectedPurchaseOrder}
              >
                <option value="">Selecciona un dispositivo</option>
                {selectedPurchaseOrder?.items.map((item) => (
                  <option key={item.id} value={item.device_id}>
                    #{item.device_id} · {item.quantity_received}/{item.quantity_ordered} recibidos
                  </option>
                ))}
              </select>
            </label>
            <label>
              Cantidad
              <input
                type="number"
                min={1}
                value={purchaseForm.quantity}
                onChange={(event) => updatePurchaseForm({ quantity: Number(event.target.value) })}
              />
            </label>
            <label>
              Estado del lote
              <select
                value={purchaseForm.disposition}
                onChange={(event) =>
                  updatePurchaseForm({ disposition: event.target.value as ReturnDisposition })
                }
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
                value={purchaseForm.category}
                onChange={(event) =>
                  updatePurchaseForm({
                    category: event.target.value as ReturnReasonCategory,
                  })
                }
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
                value={purchaseForm.warehouseId ?? ""}
                onChange={(event) =>
                  updatePurchaseForm({
                    warehouseId: event.target.value ? Number(event.target.value) : null,
                  })
                }
              >
                <option value="">Mantener en sucursal</option>
                {stores.map((store) => (
                  <option key={store.id} value={store.id}>
                    {store.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Motivo corporativo
              <input
                value={purchaseForm.reason}
                onChange={(event) => updatePurchaseForm({ reason: event.target.value })}
                placeholder="Describe el motivo"
              />
            </label>
            <button type="submit" className="btn btn--primary">
              Registrar devolución a proveedor
            </button>
          </form>

          <form onSubmit={handleSaleReturn}>
            <h3>Devolución de cliente</h3>
            <label>
              Sucursal
              <select
                value={saleForm.storeId ?? ""}
                onChange={(event) => {
                  setSaleApprovalRequired(false);
                  setSaleApprovalVisible(false);
                  updateSaleForm({
                    storeId: event.target.value ? Number(event.target.value) : null,
                    saleId: null,
                    deviceId: null,
                    warehouseId: null,
                    supervisorUsername: "",
                    supervisorPin: "",
                  });
                }}
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
              Venta
              <select
                value={saleForm.saleId ?? ""}
                onChange={(event) =>
                  updateSaleForm({
                    saleId: event.target.value ? Number(event.target.value) : null,
                    deviceId: null,
                  })
                }
                disabled={!saleForm.storeId}
              >
                <option value="">Selecciona una venta</option>
                {sales.map((sale) => (
                  <option key={sale.id} value={sale.id}>
                    #{sale.id} · {new Date(sale.created_at).toLocaleString("es-HN")}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Dispositivo
              <select
                value={saleForm.deviceId ?? ""}
                onChange={(event) =>
                  updateSaleForm({
                    deviceId: event.target.value ? Number(event.target.value) : null,
                  })
                }
                disabled={!selectedSale}
              >
                <option value="">Selecciona un dispositivo</option>
                {selectedSale?.items.map((item) => (
                  <option key={item.id} value={item.device_id}>
                    #{item.device_id} · {item.quantity} vendidos
                  </option>
                ))}
              </select>
            </label>
            <label>
              Cantidad
              <input
                type="number"
                min={1}
                value={saleForm.quantity}
                onChange={(event) => updateSaleForm({ quantity: Number(event.target.value) })}
              />
            </label>
            <label>
              Estado del producto
              <select
                value={saleForm.disposition}
                onChange={(event) =>
                  updateSaleForm({ disposition: event.target.value as ReturnDisposition })
                }
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
                value={saleForm.category}
                onChange={(event) =>
                  updateSaleForm({ category: event.target.value as ReturnReasonCategory })
                }
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
                value={saleForm.warehouseId ?? ""}
                onChange={(event) =>
                  updateSaleForm({
                    warehouseId: event.target.value ? Number(event.target.value) : null,
                  })
                }
              >
                <option value="">Mantener en sucursal</option>
                {stores.map((store) => (
                  <option key={store.id} value={store.id}>
                    {store.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Motivo corporativo
              <input
                value={saleForm.reason}
                onChange={(event) => updateSaleForm({ reason: event.target.value })}
                placeholder="Describe el motivo"
              />
            </label>
            {showSupervisorFields ? (
              <fieldset className="returns-approval">
                <legend>Autorización de supervisor</legend>
                <label>
                  Usuario supervisor
                  <input
                    value={saleForm.supervisorUsername}
                    onChange={(event) => updateSaleForm({ supervisorUsername: event.target.value })}
                    placeholder="correo@supervisor"
                  />
                </label>
                <label>
                  PIN de supervisor
                  <input
                    type="password"
                    value={saleForm.supervisorPin}
                    onChange={(event) => updateSaleForm({ supervisorPin: event.target.value })}
                    placeholder="••••"
                  />
                </label>
                {saleApprovalRequired ? (
                  <p className="muted-text">
                    Esta devolución superó el límite corporativo y requiere autorización.
                  </p>
                ) : null}
              </fieldset>
            ) : (
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setSaleApprovalVisible(true)}
              >
                Capturar autorización de supervisor
              </button>
            )}
            <button type="submit" className="btn btn--primary">
              Registrar devolución de cliente
            </button>
          </form>

          <div className="returns-history">
            <div className="returns-history__header">
              <h3>Historial de devoluciones</h3>
              <div className="returns-history__filters">
                <label>
                  Sucursal
                  <select
                    value={historyStoreId ?? ""}
                    onChange={(event) => {
                      const value = event.target.value ? Number(event.target.value) : null;
                      setHistoryStoreId(value);
                    }}
                  >
                    <option value="">Todas las sucursales</option>
                    {stores.map((store) => (
                      <option key={store.id} value={store.id}>
                        {store.name}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => {
                    setError(null);
                    void refreshHistory(historyStoreId);
                  }}
                >
                  Actualizar
                </button>
              </div>
            </div>
            <div className="returns-history__totals" aria-live="polite">
              <span>Total: {historyTotals.total}</span>
              <span>Clientes: {historyTotals.sales}</span>
              <span>Proveedores: {historyTotals.purchases}</span>
              <span>Reembolsos: ${formatCurrency(historyTotals.refund_total_amount ?? 0)}</span>
              <span>
                Notas de crédito: ${formatCurrency(historyTotals.credit_notes_total ?? 0)}
              </span>
            </div>
            {Object.keys(historyTotals.refunds_by_method ?? {}).length > 0 ? (
              <div className="returns-history__refunds muted-text" aria-live="polite">
                {Object.entries(historyTotals.refunds_by_method).map(([method, amount]) => (
                  <span key={method}>
                    {method}: ${formatCurrency(amount ?? 0)}
                  </span>
                ))}
              </div>
            ) : null}
            {Object.keys(historyTotals.categories ?? {}).length > 0 ? (
              <div className="returns-history__categories muted-text" aria-live="polite">
                {Object.entries(historyTotals.categories).map(([category, count]) => (
                  <span key={category}>
                    {categoryLabel(category as ReturnReasonCategory)}: {count}
                  </span>
                ))}
              </div>
            ) : null}
            {historyLoading ? (
              <div className="table-wrapper" role="status" aria-busy="true">
                <p>Cargando historial de devoluciones…</p>
              </div>
            ) : history.length === 0 ? (
              <div className="table-wrapper">
                <p>Sin devoluciones registradas en el periodo seleccionado.</p>
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th>Tipo</th>
                      <th>Documento</th>
                      <th>Dispositivo</th>
                      <th>Cantidad</th>
                      <th>Motivo</th>
                      <th>Categoría</th>
                      <th>Estado</th>
                      <th>Almacén</th>
                      <th>Relacionado</th>
                      <th>Responsable</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((record) => (
                      <tr key={`${record.type}-${record.id}`}>
                        <td>{new Date(record.occurred_at).toLocaleString("es-HN")}</td>
                        <td>
                          <span
                            className={`returns-history__badge returns-history__type--${record.type}`}
                          >
                            {record.type === "sale" ? "Cliente" : "Proveedor"}
                          </span>
                        </td>
                        <td>{record.reference_label}</td>
                        <td>{record.device_name ?? `#${record.device_id}`}</td>
                        <td>{record.quantity}</td>
                        <td>{record.reason}</td>
                        <td>{categoryLabel(record.reason_category)}</td>
                        <td>{dispositionLabel(record.disposition)}</td>
                        <td>
                          {record.warehouse_name ??
                            (record.warehouse_id ? `#${record.warehouse_id}` : "Sin asignar")}
                        </td>
                        <td>{record.partner_name ?? "Sin asociación"}</td>
                        <td>{record.processed_by_name ?? "Sin responsable"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </section>
      <ReturnsSearch token={token} />
    </div>
  );
}

export default Returns;
