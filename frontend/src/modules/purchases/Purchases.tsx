import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import type {
  PurchaseOrder,
  PurchaseOrderCreateInput,
  PurchaseSuggestionStore,
  PurchaseSuggestionsResponse,
} from "../../api";
import {
  createPurchaseOrderFromSuggestion,
  getPurchaseSuggestions,
} from "../../api";
import { useAuth } from "../../auth/useAuth";
import { promptCorporateReason } from "../../utils/corporateReason";

const reasonLabels: Record<PurchaseSuggestionStore["items"][number]["reason"], string> = {
  below_minimum: "Stock por debajo del mínimo",
  projected_consumption: "Cobertura insuficiente",
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

  const currency = useMemo(
    () => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }),
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
                Última generación: {new Date(suggestions.generated_at).toLocaleString("es-MX")}
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
