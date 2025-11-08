import { useCallback, useEffect, useMemo, useState } from "react";
import { Layers, Plus, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";

import { useDashboard } from "../../dashboard/context/DashboardContext";
import { promptCorporateReason } from "../../../utils/corporateReason";
import type {
  PriceEvaluationResponse,
  PriceList,
  PriceListCreateInput,
  PriceListItemCreateInput,
} from "../../../services/api/pricing";
import {
  createPriceList,
  createPriceListItem,
  deletePriceList,
  deletePriceListItem,
  evaluatePrice,
  listPriceLists,
  updatePriceList,
  updatePriceListItem,
} from "../../../services/api/pricing";

const DEFAULT_SCOPE: ScopeOption = "store";

type ScopeOption = "global" | "store" | "customer";

type NewListDraft = {
  name: string;
  description: string;
  priority: number;
  scope: ScopeOption;
  customerId: string;
};

type ItemDraft = {
  deviceId: string;
  price: string;
  currency: string;
  notes: string;
};

function PriceLists(): JSX.Element {
  const dashboard = useDashboard();
  const { enablePriceLists: featureEnabled, selectedStore, selectedStoreId } = dashboard;
  const { formatCurrency, pushToast, setError } = dashboard;
  const [lists, setLists] = useState<PriceList[]>([]);
  const [loading, setLoading] = useState(false);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [customerFilterInput, setCustomerFilterInput] = useState("");
  const [customerFilter, setCustomerFilter] = useState<number | null>(null);
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [newList, setNewList] = useState<NewListDraft>({
    name: "",
    description: "",
    priority: 100,
    scope: DEFAULT_SCOPE,
    customerId: "",
  });
  const [itemDraft, setItemDraft] = useState<ItemDraft>({
    deviceId: "",
    price: "",
    currency: "MXN",
    notes: "",
  });
  const [evaluation, setEvaluation] = useState<PriceEvaluationResponse | null>(null);

  const selectedList = useMemo(() => {
    if (!selectedListId) {
      return null;
    }
    return lists.find((list) => list.id === selectedListId) ?? null;
  }, [lists, selectedListId]);

  const appliedCustomerId = useMemo(() => {
    if (customerFilter === null || Number.isNaN(customerFilter)) {
      return null;
    }
    return customerFilter;
  }, [customerFilter]);

  const fetchLists = useCallback(async () => {
    if (!featureEnabled) {
      setLists([]);
      setSelectedListId(null);
      return;
    }
    setLoading(true);
    try {
      const response = await listPriceLists({
        storeId: selectedStoreId ?? undefined,
        customerId: appliedCustomerId ?? undefined,
        includeInactive,
      });
      setLists(response);
      if (response.length === 0) {
        setSelectedListId(null);
      } else if (!selectedListId || !response.some((list) => list.id === selectedListId)) {
        setSelectedListId(response[0].id);
      }
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible cargar las listas de precios.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [
    appliedCustomerId,
    featureEnabled,
    includeInactive,
    pushToast,
    selectedListId,
    selectedStoreId,
    setError,
  ]);

  useEffect(() => {
    void fetchLists();
  }, [fetchLists]);

  useEffect(() => {
    if (!featureEnabled || !selectedList) {
      setEvaluation(null);
      return;
    }
    if (!itemDraft.deviceId.trim()) {
      setEvaluation(null);
      return;
    }
    const deviceId = Number(itemDraft.deviceId.trim());
    if (!Number.isFinite(deviceId) || deviceId <= 0) {
      setEvaluation(null);
      return;
    }
    const controller = new AbortController();
    evaluatePrice({
      device_id: deviceId,
      store_id: selectedStoreId ?? undefined,
      customer_id: appliedCustomerId ?? undefined,
    })
      .then((result) => {
        if (!controller.signal.aborted) {
          setEvaluation(result);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setEvaluation(null);
        }
      });
    return () => controller.abort();
  }, [
    appliedCustomerId,
    featureEnabled,
    itemDraft.deviceId,
    selectedList,
    selectedStoreId,
  ]);

  const handleReload = useCallback(
    (event?: React.FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      const trimmed = customerFilterInput.trim();
      if (!trimmed) {
        setCustomerFilter(null);
        void fetchLists();
        return;
      }
      const parsed = Number(trimmed);
      if (!Number.isFinite(parsed) || parsed <= 0) {
        pushToast({
          message: "Ingresa un identificador de cliente válido (número entero).",
          variant: "warning",
        });
        return;
      }
      setCustomerFilter(parsed);
      void fetchLists();
    },
    [customerFilterInput, fetchLists, pushToast],
  );

  const handleCreateList = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!featureEnabled) {
      return;
    }
    if (!newList.name.trim()) {
      pushToast({ message: "Captura un nombre para la lista.", variant: "warning" });
      return;
    }
    const reason = promptCorporateReason("Crear lista de precios");
    if (!reason || reason.length < 5) {
      pushToast({
        message: "Acción cancelada: se requiere un motivo corporativo válido.",
        variant: "info",
      });
      return;
    }
    const payload: PriceListCreateInput = {
      name: newList.name.trim(),
      description: newList.description.trim() || undefined,
      priority: Number.isFinite(newList.priority) ? newList.priority : 100,
    };
    if (newList.scope === "store") {
      if (!selectedStoreId) {
        pushToast({ message: "Selecciona una sucursal antes de crear la lista.", variant: "warning" });
        return;
      }
      payload.store_id = selectedStoreId;
    }
    if (newList.scope === "customer") {
      if (!selectedStoreId) {
        pushToast({ message: "Selecciona una sucursal para asociar la lista al cliente.", variant: "warning" });
        return;
      }
      const parsedCustomer = Number(newList.customerId.trim());
      if (!Number.isFinite(parsedCustomer) || parsedCustomer <= 0) {
        pushToast({
          message: "Ingresa un identificador de cliente válido para la lista.",
          variant: "warning",
        });
        return;
      }
      payload.store_id = selectedStoreId;
      payload.customer_id = parsedCustomer;
    }
    try {
      await createPriceList(payload, reason);
      pushToast({ message: "Lista creada correctamente.", variant: "success" });
      setNewList({ name: "", description: "", priority: 100, scope: newList.scope, customerId: "" });
      await fetchLists();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No se pudo crear la lista de precios.";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleToggleActive = async () => {
    if (!featureEnabled || !selectedList) {
      return;
    }
    const reason = promptCorporateReason(
      selectedList.is_active ? "Desactivar lista de precios" : "Activar lista de precios",
    );
    if (!reason || reason.length < 5) {
      pushToast({
        message: "Acción cancelada: se requiere un motivo corporativo válido.",
        variant: "info",
      });
      return;
    }
    try {
      await updatePriceList(selectedList.id, { is_active: !selectedList.is_active }, reason);
      pushToast({ message: "Estado actualizado", variant: "success" });
      await fetchLists();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible actualizar el estado de la lista.";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleDeleteList = async () => {
    if (!featureEnabled || !selectedList) {
      return;
    }
    const reason = promptCorporateReason("Eliminar lista de precios");
    if (!reason || reason.length < 5) {
      pushToast({
        message: "Acción cancelada: se requiere un motivo corporativo válido.",
        variant: "info",
      });
      return;
    }
    try {
      await deletePriceList(selectedList.id, reason);
      pushToast({ message: "Lista eliminada", variant: "success" });
      setSelectedListId(null);
      await fetchLists();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible eliminar la lista.";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleAddItem = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!featureEnabled || !selectedList) {
      pushToast({ message: "Selecciona una lista para agregar precios.", variant: "info" });
      return;
    }
    const deviceId = Number(itemDraft.deviceId.trim());
    const priceValue = Number(itemDraft.price.trim());
    if (!Number.isFinite(deviceId) || deviceId <= 0) {
      pushToast({ message: "Ingresa un ID de producto válido.", variant: "warning" });
      return;
    }
    if (!Number.isFinite(priceValue) || priceValue < 0) {
      pushToast({ message: "Ingresa un precio válido.", variant: "warning" });
      return;
    }
    const reason = promptCorporateReason("Asignar precio específico");
    if (!reason || reason.length < 5) {
      pushToast({
        message: "Acción cancelada: se requiere un motivo corporativo válido.",
        variant: "info",
      });
      return;
    }
    const payload: PriceListItemCreateInput = {
      device_id: deviceId,
      price: priceValue,
      currency: itemDraft.currency.trim() || "MXN",
      notes: itemDraft.notes.trim() || undefined,
    };
    try {
      await createPriceListItem(selectedList.id, payload, reason);
      pushToast({ message: "Precio asignado", variant: "success" });
      setItemDraft({ deviceId: "", price: "", currency: itemDraft.currency, notes: "" });
      await fetchLists();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible asignar el precio al producto.";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleUpdateItemPrice = async (itemId: number, currentPrice: number) => {
    if (!featureEnabled || !selectedList) {
      return;
    }
    const userInput = window.prompt(
      "Ingresa el nuevo precio para el producto",
      currentPrice.toString(),
    );
    if (userInput === null) {
      return;
    }
    const normalized = Number(userInput.trim());
    if (!Number.isFinite(normalized) || normalized < 0) {
      pushToast({ message: "Ingresa un precio válido.", variant: "warning" });
      return;
    }
    const reason = promptCorporateReason("Actualizar precio específico");
    if (!reason || reason.length < 5) {
      pushToast({
        message: "Acción cancelada: se requiere un motivo corporativo válido.",
        variant: "info",
      });
      return;
    }
    try {
      await updatePriceListItem(
        selectedList.id,
        itemId,
        { price: normalized },
        reason,
      );
      pushToast({ message: "Precio actualizado", variant: "success" });
      await fetchLists();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible actualizar el precio.";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    if (!featureEnabled || !selectedList) {
      return;
    }
    const reason = promptCorporateReason("Eliminar precio específico");
    if (!reason || reason.length < 5) {
      pushToast({
        message: "Acción cancelada: se requiere un motivo corporativo válido.",
        variant: "info",
      });
      return;
    }
    try {
      await deletePriceListItem(selectedList.id, itemId, reason);
      pushToast({ message: "Precio eliminado", variant: "success" });
      await fetchLists();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible eliminar el precio.";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleScopeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const scope = event.target.value as ScopeOption;
    setNewList((prev) => ({ ...prev, scope }));
  };

  if (!featureEnabled) {
    return null;
  }

  return (
    <div className="price-lists-panel">
      <header className="panel-header">
        <div className="panel-header__title">
          <Layers size={20} aria-hidden="true" />
          <div>
            <h2>Listas de precios personalizadas</h2>
            <p>
              {selectedStore
                ? `Gestiona precios específicos para ${selectedStore.name}.`
                : "Selecciona una sucursal para vincular nuevas listas."}
            </p>
          </div>
        </div>
        <div className="panel-header__actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => void fetchLists()}
            disabled={loading}
          >
            <RefreshCw size={16} aria-hidden="true" /> Actualizar
          </button>
        </div>
      </header>

      <section className="price-lists-filter" aria-label="Filtros de listas de precio">
        <form className="filters-form" onSubmit={handleReload}>
          <label htmlFor="price-list-customer-filter">Cliente (ID)</label>
          <input
            id="price-list-customer-filter"
            type="number"
            min={1}
            value={customerFilterInput}
            onChange={(event) => setCustomerFilterInput(event.target.value)}
            placeholder="Ej. 101"
          />
          <label className="checkbox">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(event) => setIncludeInactive(event.target.checked)}
            />
            Mostrar inactivas
          </label>
          <button type="submit" className="btn btn--secondary" disabled={loading}>
            Aplicar filtros
          </button>
        </form>
      </section>

      <section className="price-lists-grid">
        <div className="price-lists-grid__column">
          <h3>Listas registradas</h3>
          <div className={`price-lists-table ${loading ? "is-loading" : ""}`}>
            {lists.length === 0 ? (
              <p className="empty-state">No se han definido listas de precios para la vista actual.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Prioridad</th>
                    <th>Ámbito</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {lists.map((list) => (
                    <tr
                      key={list.id}
                      className={list.id === selectedListId ? "is-selected" : ""}
                      onClick={() => setSelectedListId(list.id)}
                      role="button"
                      tabIndex={0}
                    >
                      <td>{list.name}</td>
                      <td>{list.priority}</td>
                      <td>{resolveScopeLabel(list.scope)}</td>
                      <td>
                        {list.is_active ? (
                          <span className="status status--success">Activa</span>
                        ) : (
                          <span className="status status--muted">Inactiva</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="price-lists-grid__column">
          <h3>Nueva lista</h3>
          <form className="new-list-form" onSubmit={handleCreateList}>
            <label htmlFor="new-price-list-name">Nombre</label>
            <input
              id="new-price-list-name"
              value={newList.name}
              onChange={(event) => setNewList((prev) => ({ ...prev, name: event.target.value }))}
              placeholder="Ej. Clientes VIP"
              required
            />

            <label htmlFor="new-price-list-description">Descripción</label>
            <textarea
              id="new-price-list-description"
              value={newList.description}
              onChange={(event) =>
                setNewList((prev) => ({ ...prev, description: event.target.value }))
              }
              placeholder="Notas internas o criterios aplicados"
              rows={2}
            />

            <label htmlFor="new-price-list-priority">Prioridad</label>
            <input
              id="new-price-list-priority"
              type="number"
              min={0}
              max={10000}
              value={newList.priority}
              onChange={(event) =>
                setNewList((prev) => ({ ...prev, priority: Number(event.target.value) }))
              }
            />

            <label htmlFor="new-price-list-scope">Ámbito</label>
            <select id="new-price-list-scope" value={newList.scope} onChange={handleScopeChange}>
              <option value="global">General</option>
              <option value="store">Sucursal actual</option>
              <option value="customer">Cliente específico</option>
            </select>

            {newList.scope === "customer" && (
              <label htmlFor="new-price-list-customer">
                Cliente (ID)
                <input
                  id="new-price-list-customer"
                  type="number"
                  min={1}
                  value={newList.customerId}
                  onChange={(event) =>
                    setNewList((prev) => ({ ...prev, customerId: event.target.value }))
                  }
                  placeholder="Ej. 150"
                />
              </label>
            )}

            <button type="submit" className="btn btn--primary" disabled={loading || !selectedStore}>
              <Plus size={16} aria-hidden="true" /> Crear lista
            </button>
            <p className="helper-text">
              <ShieldCheck size={14} aria-hidden="true" /> Todas las operaciones requieren un motivo
              corporativo válido (mínimo 5 caracteres).
            </p>
          </form>
        </div>
      </section>

      <section className="price-list-detail" aria-live="polite">
        {!selectedList ? (
          <p className="empty-state">Selecciona una lista para consultar sus precios asignados.</p>
        ) : (
          <div className="detail-card">
            <header className="detail-card__header">
              <div>
                <h3>{selectedList.name}</h3>
                <p>
                  Prioridad {selectedList.priority} · {resolveScopeLabel(selectedList.scope)} · Última
                  actualización {new Date(selectedList.updated_at).toLocaleString("es-MX")}
                </p>
              </div>
              <div className="detail-card__actions">
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={() => void handleToggleActive()}
                >
                  {selectedList.is_active ? "Desactivar" : "Activar"}
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleDeleteList()}
                >
                  <Trash2 size={16} aria-hidden="true" /> Eliminar
                </button>
              </div>
            </header>

            <form className="price-item-form" onSubmit={handleAddItem}>
              <h4>Asignar nuevo precio</h4>
              <div className="form-grid">
                <label htmlFor="price-item-device">ID de producto</label>
                <input
                  id="price-item-device"
                  type="number"
                  min={1}
                  value={itemDraft.deviceId}
                  onChange={(event) =>
                    setItemDraft((prev) => ({ ...prev, deviceId: event.target.value }))
                  }
                  placeholder="Ej. 501"
                  required
                />

                <label htmlFor="price-item-price">Precio</label>
                <input
                  id="price-item-price"
                  type="number"
                  min={0}
                  step="0.01"
                  value={itemDraft.price}
                  onChange={(event) =>
                    setItemDraft((prev) => ({ ...prev, price: event.target.value }))
                  }
                  placeholder="Ej. 899.90"
                  required
                />

                <label htmlFor="price-item-currency">Moneda</label>
                <input
                  id="price-item-currency"
                  value={itemDraft.currency}
                  onChange={(event) =>
                    setItemDraft((prev) => ({ ...prev, currency: event.target.value.toUpperCase() }))
                  }
                  maxLength={8}
                />

                <label htmlFor="price-item-notes">Notas</label>
                <input
                  id="price-item-notes"
                  value={itemDraft.notes}
                  onChange={(event) =>
                    setItemDraft((prev) => ({ ...prev, notes: event.target.value }))
                  }
                  placeholder="Opcional"
                />
              </div>
              {evaluation && evaluation.price_list_id === selectedList.id && (
                <p className="helper-text">
                  Precio resultante para el dispositivo #{evaluation.device_id}: {" "}
                  {evaluation.price !== null ? formatCurrency(evaluation.price) : "no definido"}
                </p>
              )}
              <button type="submit" className="btn btn--primary">
                <Plus size={16} aria-hidden="true" /> Agregar precio
              </button>
            </form>

            <div className="price-items-table">
              {selectedList.items.length === 0 ? (
                <p className="empty-state">Aún no se han asignado precios específicos.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Producto</th>
                      <th>Precio</th>
                      <th>Moneda</th>
                      <th>Notas</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedList.items.map((item) => (
                      <tr key={item.id}>
                        <td>{item.device_id}</td>
                        <td>{formatCurrency(item.price)}</td>
                        <td>{item.currency}</td>
                        <td>{item.notes ?? "—"}</td>
                        <td className="actions">
                          <button
                            type="button"
                            className="btn btn--ghost"
                            onClick={() => void handleUpdateItemPrice(item.id, item.price)}
                          >
                            Actualizar
                          </button>
                          <button
                            type="button"
                            className="btn btn--ghost"
                            onClick={() => void handleDeleteItem(item.id)}
                          >
                            Eliminar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function resolveScopeLabel(scope: string): string {
  switch (scope) {
    case "store":
      return "Sucursal";
    case "customer":
      return "Cliente";
    case "store_customer":
      return "Sucursal y cliente";
    default:
      return "General";
  }
}

export default PriceLists;
