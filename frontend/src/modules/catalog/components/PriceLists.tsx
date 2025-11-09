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
