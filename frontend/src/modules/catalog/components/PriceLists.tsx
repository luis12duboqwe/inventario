import { useCallback, useEffect, useMemo, useState } from "react";
import { DollarSign, ListChecks, PlusCircle, RefreshCcw, Save, Trash2 } from "lucide-react";

import { listCustomers, type Customer, type Device } from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { useInventoryLayout } from "../../inventory/pages/context/InventoryLayoutContext";
import { promptCorporateReason } from "../../../utils/corporateReason";
import {
  priceListsService,
  type PriceList,
  type PriceListItem,
  type PriceListListParams,
  type PriceResolution,
} from "../services/priceListsService";

type FormState = {
  name: string;
  description: string;
  is_active: boolean;
  store_id: number | null;
  customer_id: number | null;
  currency: string;
  valid_from: string;
  valid_until: string;
};

type NewItemState = {
  deviceId: string;
  price: string;
  discount: string;
  notes: string;
};

type FiltersState = {
  storeId: string;
  customerId: string;
  status: "all" | "active" | "inactive";
};

const DEFAULT_LIST_REASON = "Consulta listas de precios";
const DEFAULT_RESOLUTION_REASON = "Resolver precio por listas";

function createEmptyForm(storeId: number | null): FormState {
  return {
    name: "",
    description: "",
    is_active: true,
    store_id: storeId,
    customer_id: null,
    currency: "MXN",
    valid_from: "",
    valid_until: "",
  };
}

function createEmptyItem(): NewItemState {
  return {
    deviceId: "",
    price: "",
    discount: "",
    notes: "",
  };
}

function normalizeReason(
  defaultReason: string,
  onError: (message: string) => void,
): string | null {
  const value = promptCorporateReason(defaultReason);
  if (value === null) {
    return null;
  }
  const trimmed = value.trim();
  if (trimmed.length < 5) {
    onError("Debes capturar un motivo corporativo de al menos 5 caracteres.");
    return null;
  }
  return trimmed;
}

function resolveScopeLabel(list: PriceList): string {
  if (list.store_id && list.customer_id) {
    return "Sucursal + cliente";
  }
  if (list.customer_id) {
    return "Cliente";
  }
  if (list.store_id) {
    return "Sucursal";
  }
  return "Global";
}

function formatDateValue(value: string | null): string {
  if (!value) {
    return "";
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return trimmed;
  }
  const date = new Date(trimmed);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toISOString().slice(0, 10);
}

function validateForm(form: FormState): string[] {
  const errors: string[] = [];
  if (!form.name.trim()) {
    errors.push("Ingresa un nombre para la lista de precios.");
  } else if (form.name.trim().length < 3) {
    errors.push("El nombre debe tener al menos 3 caracteres.");
  }
  const normalizedCurrency = form.currency.trim().toUpperCase();
  if (!normalizedCurrency) {
    errors.push("Define la moneda para la lista.");
  } else if (normalizedCurrency.length < 3 || normalizedCurrency.length > 10) {
    errors.push("La moneda debe tener entre 3 y 10 caracteres.");
  }
  if (form.valid_from && form.valid_until && form.valid_from > form.valid_until) {
    errors.push("La fecha inicial no puede ser posterior a la fecha final.");
  }
  return errors;
}

function normalizeNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(value);
}

function PriceLists(): JSX.Element {
  const inventory = useInventoryLayout();
  const dashboard = useDashboard();

  const [priceLists, setPriceLists] = useState<PriceList[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [filters, setFilters] = useState<FiltersState>(() => ({
    storeId: inventory.module.selectedStoreId ? String(inventory.module.selectedStoreId) : "",
    customerId: "",
    status: "active",
  }));
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [itemSavingId, setItemSavingId] = useState<number | null>(null);
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [formState, setFormState] = useState<FormState>(() =>
    createEmptyForm(inventory.module.selectedStoreId ?? null),
  );
  const [newItemState, setNewItemState] = useState<NewItemState>(createEmptyItem);
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [editingItemState, setEditingItemState] = useState<NewItemState>(createEmptyItem);
  const [resolutionInput, setResolutionInput] = useState({
    deviceId: "",
    storeId: "",
    customerId: "",
    defaultPrice: "",
  });
  const [resolutionResult, setResolutionResult] = useState<PriceResolution | null>(null);
  const [resolutionLoading, setResolutionLoading] = useState(false);

  const deviceById = useMemo(() => {
    const map = new Map<number, Device>();
    for (const device of inventory.module.devices) {
      map.set(device.id, device);
    }
    return map;
  }, [inventory.module.devices]);

  useEffect(() => {
    if (inventory.module.selectedStoreId && !filters.storeId) {
      setFilters((current) => ({ ...current, storeId: String(inventory.module.selectedStoreId) }));
    }
  }, [inventory.module.selectedStoreId, filters.storeId]);

  const loadCustomers = useCallback(async () => {
    try {
      const list = await listCustomers(dashboard.token, { limit: 200 });
      setCustomers(list);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible cargar el catálogo de clientes corporativos.";
      dashboard.setError(message);
    }
  }, [dashboard]);

  const loadPriceLists = useCallback(async () => {
    setLoading(true);
    try {
      const params: PriceListListParams = { includeItems: true };
      if (filters.storeId) {
        params.storeId = Number(filters.storeId);
      }
      if (filters.customerId) {
        params.customerId = Number(filters.customerId);
      }
      if (filters.status !== "all") {
        params.isActive = filters.status === "active";
      }
      const lists = await priceListsService.list(dashboard.token, params, DEFAULT_LIST_REASON);
      setPriceLists(lists);
      if (!lists.length) {
        setSelectedListId(null);
        setFormState(createEmptyForm(inventory.module.selectedStoreId ?? null));
        return;
      }
      setSelectedListId((current) => {
        if (current && lists.some((list) => list.id === current)) {
          return current;
        }
        return lists[0].id;
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible consultar las listas de precios disponibles.";
      dashboard.setError(message);
      dashboard.pushToast({ message, variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [dashboard, filters.customerId, filters.status, filters.storeId, inventory.module.selectedStoreId]);

  useEffect(() => {
    void loadCustomers();
  }, [loadCustomers]);

  useEffect(() => {
    void loadPriceLists();
  }, [loadPriceLists]);

  useEffect(() => {
    if (selectedListId === null) {
      setFormState(createEmptyForm(inventory.module.selectedStoreId ?? null));
      return;
    }
    const target = priceLists.find((list) => list.id === selectedListId);
    if (!target) {
      return;
    }
    setFormState({
      name: target.name,
      description: target.description ?? "",
      is_active: target.is_active,
      store_id: target.store_id ?? null,
      customer_id: target.customer_id ?? null,
      currency: target.currency,
      valid_from: formatDateValue(target.valid_from),
      valid_until: formatDateValue(target.valid_until),
    });
  }, [inventory.module.selectedStoreId, priceLists, selectedListId]);

  const selectedList = useMemo(
    () => priceLists.find((list) => list.id === selectedListId) ?? null,
    [priceLists, selectedListId],
  );

  const handleFiltersChange = (patch: Partial<FiltersState>) => {
    setFilters((current) => ({ ...current, ...patch }));
  };

  const handleFormChange = (
    field: keyof FormState,
    value: string | number | boolean | null,
  ) => {
    setFormState((current) => ({
      ...current,
      [field]: value as FormState[typeof field],
    }));
  };

  const handleToggleActive = (value: boolean) => {
    setFormState((current) => ({ ...current, is_active: value }));
  };

  const handleNewList = () => {
    setSelectedListId(null);
    setFormState(createEmptyForm(inventory.module.selectedStoreId ?? null));
    setNewItemState(createEmptyItem());
    setEditingItemId(null);
    setEditingItemState(createEmptyItem());
    setResolutionResult(null);
  };

  const handleSubmitList = async () => {
    const validation = validateForm(formState);
    if (validation.length) {
      const message = validation.join(" ");
      dashboard.pushToast({ message, variant: "error" });
      return;
    }
    const payload = {
      name: formState.name.trim(),
      description: formState.description.trim() || null,
      is_active: formState.is_active,
      store_id: formState.store_id ?? null,
      customer_id: formState.customer_id ?? null,
      currency: formState.currency.trim().toUpperCase(),
      valid_from: formState.valid_from || null,
      valid_until: formState.valid_until || null,
    };

    const defaultReason = selectedList
      ? `Actualizar lista de precios ${selectedList.name}`
      : `Crear lista de precios ${payload.name || "nueva"}`;
    const reason = normalizeReason(defaultReason, (message) =>
      dashboard.pushToast({ message, variant: "error" }),
    );
    if (!reason) {
      return;
    }

    setSaving(true);
    try {
      if (selectedList) {
        await priceListsService.update(dashboard.token, selectedList.id, payload, reason);
        dashboard.pushToast({ message: "Lista de precios actualizada.", variant: "success" });
      } else {
        const created = await priceListsService.create(dashboard.token, payload, reason);
        dashboard.pushToast({ message: "Lista de precios creada.", variant: "success" });
        setSelectedListId(created.id);
      }
      await loadPriceLists();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible guardar la lista de precios.";
      dashboard.pushToast({ message, variant: "error" });
      dashboard.setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteList = async () => {
    if (!selectedList) {
      return;
    }
    if (!window.confirm(`¿Eliminar la lista "${selectedList.name}"?`)) {
      return;
    }
    const reason = normalizeReason(
      `Eliminar lista de precios ${selectedList.name}`,
      (message) => dashboard.pushToast({ message, variant: "error" }),
    );
    if (!reason) {
      return;
    }
    setSaving(true);
    try {
      await priceListsService.remove(dashboard.token, selectedList.id, reason);
      dashboard.pushToast({ message: "Lista de precios eliminada.", variant: "success" });
      setSelectedListId(null);
      await loadPriceLists();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible eliminar la lista de precios.";
      dashboard.pushToast({ message, variant: "error" });
      dashboard.setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleNewItemChange = (field: keyof NewItemState, value: string) => {
    setNewItemState((current) => ({ ...current, [field]: value }));
  };

  const handleSelectNewItemDevice = (value: string) => {
    const device = value ? deviceById.get(Number(value)) : null;
    setNewItemState((current) => ({
      ...current,
      deviceId: value,
      price:
        current.price || !device
          ? current.price
          : String(device.precio_venta ?? device.unit_price ?? ""),
    }));
  };

  const handleAddItem = async () => {
    if (!selectedList) {
      dashboard.pushToast({ message: "Selecciona una lista para agregar productos.", variant: "error" });
      return;
    }
    if (!newItemState.deviceId) {
      dashboard.pushToast({ message: "Elige un producto del catálogo.", variant: "error" });
      return;
    }
    const price = normalizeNumber(newItemState.price);
    if (!price || price <= 0) {
      dashboard.pushToast({ message: "Ingresa un precio válido mayor a cero.", variant: "error" });
      return;
    }
    const discount = normalizeNumber(newItemState.discount);
    if (discount !== null && (discount < 0 || discount > 100)) {
      dashboard.pushToast({ message: "El descuento debe estar entre 0 y 100%", variant: "error" });
      return;
    }
    const reason = normalizeReason(
      `Agregar producto a ${selectedList.name}`,
      (message) => dashboard.pushToast({ message, variant: "error" }),
    );
    if (!reason) {
      return;
    }

    setItemSavingId(-1);
    try {
      await priceListsService.addItem(
        dashboard.token,
        selectedList.id,
        {
          device_id: Number(newItemState.deviceId),
          price,
          discount_percentage: discount,
          notes: newItemState.notes.trim() || null,
        },
        reason,
      );
      dashboard.pushToast({ message: "Producto agregado a la lista.", variant: "success" });
      setNewItemState(createEmptyItem());
      await loadPriceLists();
      setSelectedListId(selectedList.id);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible agregar el producto a la lista.";
      dashboard.pushToast({ message, variant: "error" });
      dashboard.setError(message);
    } finally {
      setItemSavingId(null);
    }
  };

  const startEditItem = (item: PriceListItem) => {
    setEditingItemId(item.id);
    setEditingItemState({
      deviceId: String(item.device_id),
      price: String(item.price),
      discount: item.discount_percentage != null ? String(item.discount_percentage) : "",
      notes: item.notes ?? "",
    });
  };

  const cancelEditItem = () => {
    setEditingItemId(null);
    setEditingItemState(createEmptyItem());
  };

  const handleEditItemChange = (field: keyof NewItemState, value: string) => {
    setEditingItemState((current) => ({ ...current, [field]: value }));
  };

  const saveItem = async (item: PriceListItem) => {
    const price = normalizeNumber(editingItemState.price);
    if (!price || price <= 0) {
      dashboard.pushToast({ message: "Ingresa un precio válido mayor a cero.", variant: "error" });
      return;
    }
    const discount = normalizeNumber(editingItemState.discount);
    if (discount !== null && (discount < 0 || discount > 100)) {
      dashboard.pushToast({ message: "El descuento debe estar entre 0 y 100%", variant: "error" });
      return;
    }
    const reason = normalizeReason(
      `Actualizar precio de ${item.device_id}`,
      (message) => dashboard.pushToast({ message, variant: "error" }),
    );
    if (!reason) {
      return;
    }
    setItemSavingId(item.id);
    try {
      await priceListsService.updateItem(
        dashboard.token,
        item.id,
        {
          price,
          discount_percentage: discount,
          notes: editingItemState.notes.trim() || null,
        },
        reason,
      );
      dashboard.pushToast({ message: "Precio actualizado.", variant: "success" });
      await loadPriceLists();
      setSelectedListId((current) => current ?? selectedList?.id ?? null);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible actualizar el precio del producto.";
      dashboard.pushToast({ message, variant: "error" });
      dashboard.setError(message);
    } finally {
      setItemSavingId(null);
      cancelEditItem();
    }
  };

  const removeItem = async (item: PriceListItem) => {
    if (!window.confirm("¿Eliminar este producto de la lista de precios?")) {
      return;
    }
    const reason = normalizeReason(
      `Eliminar precio de ${item.device_id}`,
      (message) => dashboard.pushToast({ message, variant: "error" }),
    );
    if (!reason) {
      return;
    }
    setItemSavingId(item.id);
    try {
      await priceListsService.removeItem(dashboard.token, item.id, reason);
      dashboard.pushToast({ message: "Producto eliminado de la lista.", variant: "success" });
      await loadPriceLists();
      setSelectedListId((current) => current ?? selectedList?.id ?? null);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible eliminar el producto de la lista.";
      dashboard.pushToast({ message, variant: "error" });
      dashboard.setError(message);
    } finally {
      setItemSavingId(null);
    }
  };

  const handleResolvePrice = async () => {
    if (!resolutionInput.deviceId) {
      dashboard.pushToast({ message: "Selecciona un dispositivo para simular el precio.", variant: "error" });
      return;
    }
    setResolutionLoading(true);
    try {
      const result = await priceListsService.resolve(
        dashboard.token,
        {
          deviceId: Number(resolutionInput.deviceId),
          storeId: resolutionInput.storeId ? Number(resolutionInput.storeId) : undefined,
          customerId: resolutionInput.customerId ? Number(resolutionInput.customerId) : undefined,
          defaultPrice: normalizeNumber(resolutionInput.defaultPrice) ?? undefined,
        },
        DEFAULT_RESOLUTION_REASON,
      );
      setResolutionResult(result);
      if (!result) {
        dashboard.pushToast({ message: "No se encontró un precio aplicable.", variant: "warning" });
      }
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible resolver el precio para el dispositivo seleccionado.";
      dashboard.pushToast({ message, variant: "error" });
      dashboard.setError(message);
    } finally {
      setResolutionLoading(false);
    }
  };

  const scopeLabel = selectedList ? resolveScopeLabel(selectedList) : "";

  return (
    <div className="price-lists" data-testid="price-lists">
      <div className="price-lists__header">
        <div className="price-lists__title">
          <DollarSign aria-hidden="true" />
          <div>
            <h2>Listas de precios corporativas</h2>
            <p>
              Administra reglas de precios por sucursal y cliente para priorizar tarifas corporativas sin
              afectar el catálogo base.
            </p>
          </div>
        </div>
        <button
          type="button"
          className="price-lists__refresh"
          onClick={() => void loadPriceLists()}
          disabled={loading}
        >
          <RefreshCcw aria-hidden="true" /> Actualizar
        </button>
      </div>

      <section className="price-lists__filters">
        <div>
          <label htmlFor="price-lists-store">Sucursal</label>
          <select
            id="price-lists-store"
            value={filters.storeId}
            onChange={(event) => handleFiltersChange({ storeId: event.target.value })}
          >
            <option value="">Todas</option>
            {inventory.module.stores.map((store) => (
              <option key={store.id} value={store.id}>{store.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="price-lists-customer">Cliente</label>
          <select
            id="price-lists-customer"
            value={filters.customerId}
            onChange={(event) => handleFiltersChange({ customerId: event.target.value })}
          >
            <option value="">Todos</option>
            {customers.map((customer) => (
              <option key={customer.id} value={customer.id}>{customer.nombre}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="price-lists-status">Estado</label>
          <select
            id="price-lists-status"
            value={filters.status}
            onChange={(event) =>
              handleFiltersChange({ status: event.target.value as FiltersState["status"] })
            }
          >
            <option value="all">Todas</option>
            <option value="active">Activas</option>
            <option value="inactive">Inactivas</option>
          </select>
        </div>
        <button
          type="button"
          className="price-lists__new"
          onClick={handleNewList}
        >
          <PlusCircle aria-hidden="true" /> Nueva lista
        </button>
      </section>

      <div className="price-lists__grid">
        <aside className="price-lists__aside" aria-live="polite">
          {loading ? (
            <p className="price-lists__empty">Cargando listas de precios…</p>
          ) : priceLists.length === 0 ? (
            <p className="price-lists__empty">
              No hay listas configuradas todavía. Crea una nueva para comenzar a personalizar precios.
            </p>
          ) : (
            <ul className="price-lists__list">
              {priceLists.map((list) => (
                <li key={list.id}>
                  <button
                    type="button"
                    className={
                      list.id === selectedListId
                        ? "price-lists__list-item price-lists__list-item--active"
                        : "price-lists__list-item"
                    }
                    onClick={() => setSelectedListId(list.id)}
                    data-testid="price-list-row"
                  >
                    <strong>{list.name}</strong>
                    <span>{resolveScopeLabel(list)}</span>
                    <small>{list.is_active ? "Activa" : "Inactiva"}</small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <div className="price-lists__content">
          <section className="price-lists__card" aria-live="polite">
            <header className="price-lists__card-header">
              <div>
                <h3>{selectedList ? selectedList.name : "Nueva lista"}</h3>
                <p>
                  {selectedList
                    ? `Ámbito: ${scopeLabel}.`
                    : "Define los parámetros base y guarda para comenzar a agregar productos."}
                </p>
              </div>
            </header>
            <div className="price-lists__card-body">
              <div className="price-lists__form">
                <div>
                  <label htmlFor="price-list-name">Nombre</label>
                  <input
                    id="price-list-name"
                    value={formState.name}
                    onChange={(event) => handleFormChange("name", event.target.value)}
                    placeholder="Lista corporativa principal"
                  />
                </div>
                <div>
                  <label htmlFor="price-list-description">Descripción</label>
                  <textarea
                    id="price-list-description"
                    value={formState.description}
                    onChange={(event) => handleFormChange("description", event.target.value)}
                    placeholder="Notas internas sobre el objetivo de la lista"
                    rows={3}
                  />
                </div>
                <div className="price-lists__form-row">
                  <div>
                    <label htmlFor="price-list-store">Sucursal</label>
                    <select
                      id="price-list-store"
                      value={formState.store_id ?? ""}
                      onChange={(event) =>
                        handleFormChange(
                          "store_id",
                          event.target.value ? Number(event.target.value) : null,
                        )
                      }
                    >
                      <option value="">Global</option>
                      {inventory.module.stores.map((store) => (
                        <option key={store.id} value={store.id}>{store.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="price-list-customer">Cliente</label>
                    <select
                      id="price-list-customer"
                      value={formState.customer_id ?? ""}
                      onChange={(event) =>
                        handleFormChange(
                          "customer_id",
                          event.target.value ? Number(event.target.value) : null,
                        )
                      }
                    >
                      <option value="">Sin cliente</option>
                      {customers.map((customer) => (
                        <option key={customer.id} value={customer.id}>{customer.nombre}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="price-lists__form-row">
                  <div>
                    <label htmlFor="price-list-currency">Moneda</label>
                    <input
                      id="price-list-currency"
                      value={formState.currency}
                      onChange={(event) => handleFormChange("currency", event.target.value)}
                    />
                  </div>
                  <div className="price-lists__switch">
                    <label htmlFor="price-list-active">Activa</label>
                    <input
                      id="price-list-active"
                      type="checkbox"
                      checked={formState.is_active}
                      onChange={(event) => handleToggleActive(event.target.checked)}
                    />
                  </div>
                </div>
                <div className="price-lists__form-row">
                  <div>
                    <label htmlFor="price-list-valid-from">Vigencia inicial</label>
                    <input
                      id="price-list-valid-from"
                      type="date"
                      value={formState.valid_from}
                      onChange={(event) => handleFormChange("valid_from", event.target.value)}
                    />
                  </div>
                  <div>
                    <label htmlFor="price-list-valid-until">Vigencia final</label>
                    <input
                      id="price-list-valid-until"
                      type="date"
                      value={formState.valid_until}
                      onChange={(event) => handleFormChange("valid_until", event.target.value)}
                    />
                  </div>
                </div>
              </div>
            </div>
            <footer className="price-lists__card-footer">
              <button
                type="button"
                className="price-lists__primary"
                onClick={handleSubmitList}
                disabled={saving}
              >
                <Save aria-hidden="true" /> Guardar cambios
              </button>
              {selectedList ? (
                <button
                  type="button"
                  className="price-lists__danger"
                  onClick={handleDeleteList}
                  disabled={saving}
                >
                  <Trash2 aria-hidden="true" /> Eliminar lista
                </button>
              ) : null}
            </footer>
          </section>

          {selectedList ? (
            <section className="price-lists__card">
              <header className="price-lists__card-header">
                <div>
                  <h3>
                    <ListChecks aria-hidden="true" /> Productos asignados
                  </h3>
                  <p>Gestiona los precios específicos de este listado corporativo.</p>
                </div>
              </header>
              <div className="price-lists__card-body">
                <div className="price-lists__items-form">
                  <div>
                    <label htmlFor="price-list-item-device">Producto</label>
                    <select
                      id="price-list-item-device"
                      value={newItemState.deviceId}
                      onChange={(event) => handleSelectNewItemDevice(event.target.value)}
                    >
                      <option value="">Selecciona un producto</option>
                      {inventory.module.devices.map((device) => (
                        <option key={device.id} value={device.id}>
                          {device.name ?? device.sku ?? `Producto #${device.id}`}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="price-list-item-price">Precio</label>
                    <input
                      id="price-list-item-price"
                      value={newItemState.price}
                      onChange={(event) => handleNewItemChange("price", event.target.value)}
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label htmlFor="price-list-item-discount">Descuento %</label>
                    <input
                      id="price-list-item-discount"
                      value={newItemState.discount}
                      onChange={(event) => handleNewItemChange("discount", event.target.value)}
                      placeholder="0"
                    />
                  </div>
                  <div>
                    <label htmlFor="price-list-item-notes">Notas</label>
                    <input
                      id="price-list-item-notes"
                      value={newItemState.notes}
                      onChange={(event) => handleNewItemChange("notes", event.target.value)}
                      placeholder="Notas opcionales"
                    />
                  </div>
                  <button
                    type="button"
                    className="price-lists__primary"
                    onClick={handleAddItem}
                    disabled={itemSavingId !== null}
                  >
                    <PlusCircle aria-hidden="true" /> Agregar producto
                  </button>
                </div>

                <table className="price-lists__items-table">
                  <thead>
                    <tr>
                      <th>Producto</th>
                      <th>Precio base</th>
                      <th>Descuento</th>
                      <th>Notas</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedList.items.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="price-lists__empty">
                          Esta lista aún no tiene productos asignados.
                        </td>
                      </tr>
                    ) : (
                      selectedList.items.map((item) => {
                        const device = deviceById.get(item.device_id);
                        const name = device?.name ?? device?.sku ?? `Producto #${item.device_id}`;
                        const isEditing = editingItemId === item.id;
                        return (
                          <tr key={item.id} data-testid="price-list-item-row">
                            <td>{name}</td>
                            <td>
                              {isEditing ? (
                                <input
                                  value={editingItemState.price}
                                  onChange={(event) => handleEditItemChange("price", event.target.value)}
                                />
                              ) : (
                                formatCurrency(item.price)
                              )}
                            </td>
                            <td>
                              {isEditing ? (
                                <input
                                  value={editingItemState.discount}
                                  onChange={(event) =>
                                    handleEditItemChange("discount", event.target.value)
                                  }
                                />
                              ) : item.discount_percentage != null ? (
                                `${item.discount_percentage}%`
                              ) : (
                                "—"
                              )}
                            </td>
                            <td>
                              {isEditing ? (
                                <input
                                  value={editingItemState.notes}
                                  onChange={(event) => handleEditItemChange("notes", event.target.value)}
                                />
                              ) : item.notes ? (
                                item.notes
                              ) : (
                                "—"
                              )}
                            </td>
                            <td className="price-lists__actions">
                              {isEditing ? (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => saveItem(item)}
                                    disabled={itemSavingId !== null}
                                  >
                                    <Save aria-hidden="true" /> Guardar
                                  </button>
                                  <button type="button" onClick={cancelEditItem}>
                                    Cancelar
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button type="button" onClick={() => startEditItem(item)}>
                                    Editar
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => removeItem(item)}
                                    disabled={itemSavingId !== null}
                                  >
                                    <Trash2 aria-hidden="true" />
                                  </button>
                                </>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          <section className="price-lists__card">
            <header className="price-lists__card-header">
              <div>
                <h3>Simulador de resolución de precios</h3>
                <p>
                  Compara el precio final resultante de las listas activas considerando sucursal, cliente y
                  descuentos vigentes.
                </p>
              </div>
            </header>
            <div className="price-lists__card-body">
              <div className="price-lists__items-form">
                <div>
                  <label htmlFor="price-lists-resolve-device">Producto</label>
                  <select
                    id="price-lists-resolve-device"
                    value={resolutionInput.deviceId}
                    onChange={(event) =>
                      setResolutionInput((current) => ({ ...current, deviceId: event.target.value }))
                    }
                  >
                    <option value="">Selecciona un producto</option>
                    {inventory.module.devices.map((device) => (
                      <option key={device.id} value={device.id}>
                        {device.name ?? device.sku ?? `Producto #${device.id}`}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="price-lists-resolve-store">Sucursal</label>
                  <select
                    id="price-lists-resolve-store"
                    value={resolutionInput.storeId}
                    onChange={(event) =>
                      setResolutionInput((current) => ({ ...current, storeId: event.target.value }))
                    }
                  >
                    <option value="">Automático</option>
                    {inventory.module.stores.map((store) => (
                      <option key={store.id} value={store.id}>{store.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="price-lists-resolve-customer">Cliente</label>
                  <select
                    id="price-lists-resolve-customer"
                    value={resolutionInput.customerId}
                    onChange={(event) =>
                      setResolutionInput((current) => ({ ...current, customerId: event.target.value }))
                    }
                  >
                    <option value="">Automático</option>
                    {customers.map((customer) => (
                      <option key={customer.id} value={customer.id}>{customer.nombre}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="price-lists-resolve-default">Precio base (opcional)</label>
                  <input
                    id="price-lists-resolve-default"
                    value={resolutionInput.defaultPrice}
                    onChange={(event) =>
                      setResolutionInput((current) => ({ ...current, defaultPrice: event.target.value }))
                    }
                    placeholder="0.00"
                  />
                </div>
                <button
                  type="button"
                  className="price-lists__primary"
                  onClick={handleResolvePrice}
                  disabled={resolutionLoading}
                >
                  <RefreshCcw aria-hidden="true" /> Simular
                </button>
              </div>
              {resolutionResult ? (
                <div className="price-lists__resolution" data-testid="price-resolution-result">
                  <h4>Resultado</h4>
                  <ul>
                    <li>
                      Lista aplicada: {resolutionResult.price_list_name ?? "Predeterminada"} ({
                        resolutionResult.scope
                      })
                    </li>
                    <li>Precio base: {formatCurrency(resolutionResult.base_price)}</li>
                    <li>
                      Descuento: {resolutionResult.discount_percentage != null
                        ? `${resolutionResult.discount_percentage}%`
                        : "—"}
                    </li>
                    <li>Precio final: {formatCurrency(resolutionResult.final_price)}</li>
                  </ul>
                </div>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

export default PriceLists;
