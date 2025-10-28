import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import type { Customer, Device, RepairOrder } from "../../../../api";
import { getDevices, listCustomers, listRepairOrders } from "../../../../api";
import { useDashboard } from "../../../dashboard/context/DashboardContext";
import type { ModuleStatus } from "../../../../shared/components/ModuleHeader";

import { createRepairRowRenderer } from "./createRepairRowRenderer";
import {
  VISUAL_STORAGE_KEY,
  initialRepairForm,
  repairStatusLabels,
  repairStatusOptions,
  resolveDamageIcon,
  type RepairVisual,
} from "./repairOrdersBoardConstants";
import type { RepairForm, RepairPartForm } from "./RepairOrdersTypes";
import useRepairOrderActions from "./useRepairOrderActions";

type RepairOrdersBoardHookOptions = {
  token: string;
  selectedStoreId: number | null;
  onSelectedStoreChange: (storeId: number | null) => void;
  onInventoryRefresh?: () => void;
  onModuleStatusChange?: (status: ModuleStatus, label: string) => void;
  initialStatusFilter?: RepairOrder["status"] | "TODOS";
  statusFilterOptions?: Array<RepairOrder["status"] | "TODOS">;
  showCreateForm?: boolean;
};

type RepairOrdersBoardHookResult = {
  localStoreId: number | null;
  handleStoreChange: (storeId: number | null) => void;
  message: string | null;
  error: string | null;
  loading: boolean;
  orders: RepairOrder[];
  form: RepairForm;
  updateForm: (updates: Partial<RepairForm>) => void;
  updatePart: (index: number, updates: Partial<RepairPartForm>) => void;
  addPart: () => void;
  removePart: (index: number) => void;
  resetForm: () => void;
  customers: Customer[];
  customerSearch: string;
  setCustomerSearch: (value: string) => void;
  devices: Device[];
  handleCreate: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleExportCsv: () => void;
  renderRepairRow: (order: RepairOrder) => ReactNode;
  statusFilter: RepairOrder["status"] | "TODOS";
  handleStatusFilterChange: (value: RepairOrder["status"] | "TODOS") => void;
  availableStatusFilters: Array<RepairOrder["status"] | "TODOS">;
  getStatusLabel: (status: RepairOrder["status"]) => string;
  search: string;
  handleSearchChange: (value: string) => void;
  showCreateForm: boolean;
};

function useRepairOrdersBoard({
  token,
  selectedStoreId,
  onSelectedStoreChange,
  onInventoryRefresh,
  onModuleStatusChange,
  initialStatusFilter = "TODOS",
  statusFilterOptions,
  showCreateForm = true,
}: RepairOrdersBoardHookOptions): RepairOrdersBoardHookResult {
  const { globalSearchTerm, setGlobalSearchTerm } = useDashboard();

  const [orders, setOrders] = useState<RepairOrder[]>([]);
  const [form, setForm] = useState<RepairForm>({ ...initialRepairForm, storeId: selectedStoreId ?? null });
  const [devices, setDevices] = useState<Device[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerSearch, setCustomerSearch] = useState("");
  const [localStoreId, setLocalStoreId] = useState<number | null>(selectedStoreId);
  const [statusFilter, setStatusFilter] = useState<RepairOrder["status"] | "TODOS">(initialStatusFilter);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [visuals, setVisuals] = useState<Record<number, RepairVisual>>(() => {
    if (typeof window === "undefined") {
      return {};
    }
    try {
      const stored = window.localStorage.getItem(VISUAL_STORAGE_KEY);
      return stored ? (JSON.parse(stored) as Record<number, RepairVisual>) : {};
    } catch {
      return {};
    }
  });

  const previousStoreIdRef = useRef<number | null>(null);

  useEffect(() => {
    setSearch(globalSearchTerm);
  }, [globalSearchTerm]);

  useEffect(() => {
    setStatusFilter(initialStatusFilter);
  }, [initialStatusFilter]);

  useEffect(() => {
    setLocalStoreId(selectedStoreId);
    setForm((current) => ({ ...current, storeId: selectedStoreId }));
  }, [selectedStoreId]);

  const formatError = useCallback((err: unknown, fallback: string) => {
    if (err instanceof Error) {
      const messageText = err.message;
      if (messageText.toLowerCase().includes("failed to fetch")) {
        return "No fue posible conectar con el servicio Softmobile. Verifica tu red e inténtalo nuevamente.";
      }
      return messageText;
    }
    return fallback;
  }, []);

  const refreshOrders = useCallback(
    async (storeId?: number | null, query?: string, status?: RepairOrder["status"] | "TODOS") => {
      if (!storeId) {
        setOrders([]);
        setLoading(false);
        setError(null);
        return;
      }
      try {
        setLoading(true);
        setError(null);
        const params: { store_id?: number; status?: string; q?: string; limit?: number } = { limit: 100 };
        params.store_id = storeId;
        if (status && status !== "TODOS") {
          params.status = status;
        }
        const trimmed = query?.trim();
        if (trimmed) {
          params.q = trimmed;
        }
        const data = await listRepairOrders(token, params);
        setOrders(data);
      } catch (err) {
        setError(formatError(err, "No fue posible cargar las órdenes de reparación."));
      } finally {
        setLoading(false);
      }
    },
    [formatError, token],
  );

  const refreshDevices = useCallback(
    async (storeId: number | null) => {
      if (!storeId) {
        setDevices([]);
        return;
      }
      try {
        const storeDevices = await getDevices(token, storeId);
        setDevices(storeDevices);
      } catch (err) {
        setError(formatError(err, "No fue posible cargar los dispositivos de la sucursal."));
      }
    },
    [formatError, token],
  );

  const refreshCustomers = useCallback(
    async (query?: string) => {
      try {
        const trimmed = query?.trim();
        const results = await listCustomers(token, {
          query: trimmed && trimmed.length > 0 ? trimmed : undefined,
          limit: 100,
        });
        setCustomers(results);
      } catch (err) {
        setError(formatError(err, "No fue posible cargar los clientes para reparaciones."));
      }
    },
    [formatError, token],
  );

  useEffect(() => {
    if (!localStoreId) {
      previousStoreIdRef.current = null;
      return;
    }
    const trimmed = search.trim();
    const storeChanged = previousStoreIdRef.current !== localStoreId;
    const handler = window.setTimeout(() => {
      void refreshOrders(localStoreId, trimmed, statusFilter);
    }, storeChanged ? 0 : 350);
    previousStoreIdRef.current = localStoreId;
    return () => window.clearTimeout(handler);
  }, [search, statusFilter, localStoreId, refreshOrders]);

  useEffect(() => {
    const trimmed = customerSearch.trim();
    const handler = window.setTimeout(() => {
      void refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
    }, 350);
    return () => window.clearTimeout(handler);
  }, [customerSearch, refreshCustomers]);

  useEffect(() => {
    void refreshCustomers();
  }, [refreshCustomers]);

  useEffect(() => {
    if (!localStoreId) {
      setOrders([]);
      setDevices([]);
      setForm((current) => ({ ...current, storeId: null, parts: [] }));
      setLoading(false);
      return;
    }
    setForm((current) => ({ ...current, storeId: localStoreId }));
    void refreshDevices(localStoreId);
  }, [localStoreId, refreshDevices]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(VISUAL_STORAGE_KEY, JSON.stringify(visuals));
  }, [visuals]);

  useEffect(() => {
    if (!onModuleStatusChange) {
      return;
    }
    if (loading) {
      onModuleStatusChange("warning", "Cargando reparaciones");
      return;
    }
    const now = Date.now();
    const delayed = orders.filter((order) => {
      if (order.status !== "PENDIENTE") {
        return false;
      }
      const opened = new Date(order.opened_at).getTime();
      return Number.isFinite(opened) && now - opened > 48 * 60 * 60 * 1000;
    }).length;
    if (delayed > 0) {
      onModuleStatusChange("critical", `${delayed} reparaciones pendientes con más de 48h`);
      return;
    }
    const inProgress = orders.filter((order) => order.status === "EN_PROCESO").length;
    if (inProgress > 0) {
      onModuleStatusChange("warning", `${inProgress} reparaciones en proceso`);
      return;
    }
    onModuleStatusChange("ok", orders.length === 0 ? "Sin órdenes activas" : "Reparaciones al día");
  }, [loading, onModuleStatusChange, orders]);

  const updateForm = (updates: Partial<RepairForm>) => {
    setForm((current) => ({ ...current, ...updates }));
  };

  const updatePart = (index: number, updates: Partial<RepairPartForm>) => {
    setForm((current) => ({
      ...current,
      parts: current.parts.map((part, position) => (position === index ? { ...part, ...updates } : part)),
    }));
  };

  const addPart = () => {
    setForm((current) => ({
      ...current,
      parts: [...current.parts, { deviceId: null, quantity: 1, unitCost: 0 }],
    }));
  };

  const removePart = (index: number) => {
    setForm((current) => ({
      ...current,
      parts: current.parts.filter((_, position) => position !== index),
    }));
  };

  const resetForm = () => {
    setForm((current) => ({ ...initialRepairForm, storeId: current.storeId }));
  };

  const { handleCreate, handleStatusChange, handleDelete, handleDownload, handleExportCsv } =
    useRepairOrderActions({
      token,
      form,
      setForm: (updater) => setForm((current) => updater(current)),
      formatError,
      setError,
      setMessage,
      refreshOrders,
      onInventoryRefresh,
      localStoreId,
      search,
      statusFilter,
      orders,
    });

  const getVisual = (order: RepairOrder): RepairVisual => {
    return visuals[order.id] ?? { icon: resolveDamageIcon(order.damage_type) };
  };

  const handleVisualEdit = (order: RepairOrder) => {
    const current = getVisual(order);
    const iconInput = window.prompt(
      "Emoji representativo del dispositivo o daño (ej. 📱, 🔋)",
      current.icon ?? resolveDamageIcon(order.damage_type),
    );
    if (iconInput === null) {
      return;
    }
    const sanitizedIcon = iconInput.trim() || resolveDamageIcon(order.damage_type);
    const imageInput = window.prompt(
      "URL de imagen opcional del dispositivo (deja vacío para mostrar solo el ícono)",
      current.imageUrl ?? "",
    );
    if (imageInput === null) {
      setVisuals((previous) => ({
        ...previous,
        [order.id]: { icon: sanitizedIcon, imageUrl: current.imageUrl },
      }));
      return;
    }
    const trimmedImage = imageInput.trim();
    setVisuals((previous) => ({
      ...previous,
      [order.id]: trimmedImage ? { icon: sanitizedIcon, imageUrl: trimmedImage } : { icon: sanitizedIcon },
    }));
  };

  const devicesById = useMemo(() => {
    const map = new Map<number, Device>();
    devices.forEach((device) => map.set(device.id, device));
    return map;
  }, [devices]);

  const renderRepairRow = useMemo(() => {
    return createRepairRowRenderer({
      devicesById,
      getVisual,
      handleVisualEdit,
      handleStatusChange,
      handleDownload,
      handleDelete,
    });
  }, [devicesById, getVisual, handleVisualEdit, handleStatusChange, handleDownload, handleDelete]);


  const availableStatusFilters = useMemo(() => {
    if (!statusFilterOptions || statusFilterOptions.length === 0) {
      return ["TODOS", ...repairStatusOptions];
    }
    const withTodos = statusFilterOptions.includes("TODOS")
      ? statusFilterOptions
      : ["TODOS", ...statusFilterOptions];
    return Array.from(new Set(withTodos));
  }, [statusFilterOptions]);

  const handleStatusFilterChange = (value: RepairOrder["status"] | "TODOS") => {
    setStatusFilter(value);
    void refreshOrders(localStoreId, search.trim(), value);
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setGlobalSearchTerm(value);
  };

  const getStatusLabel = (status: RepairOrder["status"]) => repairStatusLabels[status];

  const handleStoreChange = (storeId: number | null) => {
    setLocalStoreId(storeId);
    onSelectedStoreChange(storeId);
  };

  return {
    localStoreId,
    handleStoreChange,
    message,
    error,
    loading,
    orders,
    form,
    updateForm,
    updatePart,
    addPart,
    removePart,
    resetForm,
    customers,
    customerSearch,
    setCustomerSearch,
    devices,
    handleCreate,
    handleExportCsv,
    renderRepairRow,
    statusFilter,
    handleStatusFilterChange,
    availableStatusFilters,
    getStatusLabel,
    search,
    handleSearchChange,
    showCreateForm,
  };
}

export type { RepairOrdersBoardHookOptions, RepairOrdersBoardHookResult, RepairVisual };
export { repairStatusLabels, repairStatusOptions };
export default useRepairOrdersBoard;
