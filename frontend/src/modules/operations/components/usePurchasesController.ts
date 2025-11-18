import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import type {
  Device,
  PurchaseOrder,
  PurchaseReceiveInput,
  PurchaseRecord,
  PurchaseRecordPayload,
  PurchaseStatistics,
  PurchaseVendor,
  PurchaseVendorHistory,
  PurchaseVendorPayload,
  RecurringOrder,
  RecurringOrderPayload,
  Store,
  UserAccount,
} from "../../../api";
import {
  cancelPurchaseOrder,
  createPurchaseOrder,
  createPurchaseRecord,
  createRecurringOrder,
  createPurchaseVendor,
  exportPurchaseRecordsExcel,
  exportPurchaseRecordsPdf,
  exportPurchaseVendorsCsv,
  getDevices,
  getPurchaseVendorHistory,
  getPurchaseStatistics,
  importPurchaseOrdersCsv,
  listPurchaseOrders,
  listPurchaseRecords,
  listPurchaseVendors,
  listRecurringOrders,
  listUsers,
  receivePurchaseOrder,
  registerPurchaseReturn,
  executeRecurringOrder,
  setPurchaseVendorStatus,
  updatePurchaseVendor,
} from "../../../api";
import type {
  PurchaseForm,
  PurchaseRecordDraftItem,
  PurchaseRecordFilters,
  PurchaseRecordForm,
  VendorFilters,
  VendorForm,
  VendorHistoryFilters,
} from "../../../types/purchases";

export type PurchasesControllerParams = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

const initialForm: PurchaseForm = {
  storeId: null,
  supplier: "",
  deviceId: null,
  quantity: 1,
  unitCost: 0,
};

const recordInitialForm: PurchaseRecordForm = {
  storeId: null,
  vendorId: null,
  paymentMethod: "TRANSFERENCIA",
  status: "REGISTRADA",
  taxRate: 0.16,
  date: new Date().toISOString().slice(0, 10),
};

const blankRecordItem: PurchaseRecordDraftItem = {
  productId: null,
  quantity: 1,
  unitCost: 0,
};

const recordStatuses = ["REGISTRADA", "PAGADA", "CANCELADA", "DEVUELTA"] as const;

const paymentOptions = ["EFECTIVO", "TRANSFERENCIA", "TARJETA", "CREDITO", "OTRO"] as const;

const emptyVendorFilters: VendorFilters = { query: "", status: "" };

const emptyVendorForm: VendorForm = {
  nombre: "",
  telefono: "",
  correo: "",
  direccion: "",
  tipo: "",
  notas: "",
};

const emptyVendorHistoryFilters: VendorHistoryFilters = {
  limit: 10,
  dateFrom: "",
  dateTo: "",
};

const emptyRecordFilters: PurchaseRecordFilters = {
  vendorId: "",
  userId: "",
  dateFrom: "",
  dateTo: "",
  status: "",
  search: "",
};

const useReasonPrompt = (setError: (message: string | null) => void) => {
  return (promptText: string) => {
    const reason = window.prompt(promptText, "");
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo (mínimo 5 caracteres).");
      return null;
    }
    return reason.trim();
  };
};

const useBlobDownloader = () => {
  return (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };
};

export const usePurchasesController = ({
  token,
  stores,
  defaultStoreId = null,
  onInventoryRefresh,
}: PurchasesControllerParams) => {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [recurringOrders, setRecurringOrders] = useState<RecurringOrder[]>([]);
  const [form, setForm] = useState<PurchaseForm>({ ...initialForm, storeId: defaultStoreId });
  const [recordForm, setRecordForm] = useState<PurchaseRecordForm>({
    ...recordInitialForm,
    storeId: defaultStoreId ?? null,
  });
  const [recordItems, setRecordItems] = useState<PurchaseRecordDraftItem[]>([{
    ...blankRecordItem,
  }]);
  const [recordDevices, setRecordDevices] = useState<Device[]>([]);
  const [vendors, setVendors] = useState<PurchaseVendor[]>([]);
  const [records, setRecords] = useState<PurchaseRecord[]>([]);
  const [statistics, setStatistics] = useState<PurchaseStatistics | null>(null);
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [recordFilters, setRecordFilters] = useState({ ...emptyRecordFilters });
  const [recordFiltersDraft, setRecordFiltersDraft] = useState({ ...emptyRecordFilters });
  const [vendorFilters, setVendorFilters] = useState({ ...emptyVendorFilters });
  const [vendorFiltersDraft, setVendorFiltersDraft] = useState({ ...emptyVendorFilters });
  const [vendorForm, setVendorForm] = useState({ ...emptyVendorForm });
  const [editingVendorId, setEditingVendorId] = useState<number | null>(null);
  const [selectedVendorId, setSelectedVendorId] = useState<number | null>(null);
  const [vendorHistory, setVendorHistory] = useState<PurchaseVendorHistory | null>(null);
  const [vendorHistoryFilters, setVendorHistoryFilters] = useState({
    ...emptyVendorHistoryFilters,
  });
  const [vendorHistoryFiltersDraft, setVendorHistoryFiltersDraft] = useState({
    ...emptyVendorHistoryFilters,
  });
  const [loading, setLoading] = useState(false);
  const [recurringLoading, setRecurringLoading] = useState(false);
  const [csvLoading, setCsvLoading] = useState(false);
  const [templateSaving, setTemplateSaving] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [vendorsLoading, setVendorsLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [usersLoading, setUsersLoading] = useState(false);
  const [vendorHistoryLoading, setVendorHistoryLoading] = useState(false);
  const [vendorSaving, setVendorSaving] = useState(false);
  const [vendorExporting, setVendorExporting] = useState(false);

  const askReason = useReasonPrompt(setError);
  const downloadBlob = useBlobDownloader();

  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" }),
    [],
  );

  const selectedStore = useMemo(
    () => stores.find((store) => store.id === form.storeId) ?? null,
    [stores, form.storeId],
  );

  const selectedVendor = useMemo(
    () => vendors.find((vendor) => vendor.id_proveedor === selectedVendorId) ?? null,
    [vendors, selectedVendorId],
  );

  const recordStatusOptions = useMemo(() => {
    const baseStatuses = [...recordStatuses];
    if (recordForm.status && !baseStatuses.includes(recordForm.status as (typeof recordStatuses)[number])) {
      baseStatuses.push(recordForm.status as (typeof recordStatuses)[number]);
    }
    return baseStatuses;
  }, [recordForm.status]);

  const loadRecurringOrders = useCallback(async () => {
    try {
      setRecurringLoading(true);
      const data = await listRecurringOrders(token, "purchase");
      setRecurringOrders(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar las plantillas de compras");
    } finally {
      setRecurringLoading(false);
    }
  }, [token]);

  const refreshOrders = useCallback(
    async (storeId?: number | null) => {
      if (!storeId) {
        setOrders([]);
        return;
      }
      try {
        setLoading(true);
        const data = await listPurchaseOrders(token, storeId);
        setOrders(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar las órdenes de compra");
      } finally {
        setLoading(false);
      }
    },
    [token],
  );

  const loadVendors = useCallback(async () => {
    try {
      setVendorsLoading(true);
      const vendorQuery = vendorFilters.query.trim();
      const vendorStatus = vendorFilters.status.trim();
      const vendorArgs: Parameters<typeof listPurchaseVendors>[1] = { limit: 200 };
      if (vendorQuery) {
        vendorArgs.query = vendorQuery;
      }
      if (vendorStatus) {
        vendorArgs.status = vendorStatus;
      }
      const data = await listPurchaseVendors(token, vendorArgs);
      setVendors(data);
      if (data.length === 0) {
        setSelectedVendorId(null);
        setVendorHistory(null);
        return;
      }
      setSelectedVendorId((current) => {
        if (current && data.some((vendor) => vendor.id_proveedor === current)) {
          return current;
        }
        return data[0]?.id_proveedor ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar los proveedores de compras");
    } finally {
      setVendorsLoading(false);
    }
  }, [token, vendorFilters.query, vendorFilters.status]);

  const loadVendorHistory = useCallback(
    async (vendorId?: number | null) => {
      if (!vendorId) {
        setVendorHistory(null);
        return;
      }
      try {
        setVendorHistoryLoading(true);
        const historyArgs: Parameters<typeof getPurchaseVendorHistory>[2] = {
          limit: vendorHistoryFilters.limit,
        };
        const fromNormalized = vendorHistoryFilters.dateFrom.trim();
        const toNormalized = vendorHistoryFilters.dateTo.trim();
        if (fromNormalized) {
          historyArgs.dateFrom = fromNormalized;
        }
        if (toNormalized) {
          historyArgs.dateTo = toNormalized;
        }
        const data = await getPurchaseVendorHistory(token, vendorId, historyArgs);
        setVendorHistory(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible obtener el historial del proveedor");
      } finally {
        setVendorHistoryLoading(false);
      }
    },
    [token, vendorHistoryFilters],
  );

  const loadUsers = useCallback(async () => {
    try {
      setUsersLoading(true);
      const data = await listUsers(token);
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar usuarios disponibles");
    } finally {
      setUsersLoading(false);
    }
  }, [token]);

  const loadRecords = useCallback(async () => {
    try {
      setRecordsLoading(true);
      const recordArgs: Parameters<typeof listPurchaseRecords>[1] = { limit: 200 };
      if (recordFilters.vendorId) {
        recordArgs.proveedorId = Number(recordFilters.vendorId);
      }
      if (recordFilters.userId) {
        recordArgs.usuarioId = Number(recordFilters.userId);
      }
      const fromNormalized = recordFilters.dateFrom.trim();
      if (fromNormalized) {
        recordArgs.dateFrom = fromNormalized;
      }
      const toNormalized = recordFilters.dateTo.trim();
      if (toNormalized) {
        recordArgs.dateTo = toNormalized;
      }
      const statusNormalized = recordFilters.status.trim();
      if (statusNormalized) {
        recordArgs.estado = statusNormalized;
      }
      const searchNormalized = recordFilters.search.trim();
      if (searchNormalized) {
        recordArgs.query = searchNormalized;
      }
      const data = await listPurchaseRecords(token, recordArgs);
      setRecords(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible listar las compras registradas");
    } finally {
      setRecordsLoading(false);
    }
  }, [token, recordFilters]);

  const loadStatistics = useCallback(async () => {
    try {
      setStatsLoading(true);
      const data = await getPurchaseStatistics(token);
      setStatistics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible obtener las estadísticas de compras");
    } finally {
      setStatsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadRecurringOrders();
  }, [loadRecurringOrders]);

  useEffect(() => {
    void loadVendors();
  }, [loadVendors]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    void loadRecords();
  }, [loadRecords]);

  useEffect(() => {
    void loadStatistics();
  }, [loadStatistics]);

  useEffect(() => {
    void loadVendorHistory(selectedVendorId);
  }, [loadVendorHistory, selectedVendorId]);

  useEffect(() => {
    setForm((current) => ({ ...current, storeId: defaultStoreId ?? null }));
  }, [defaultStoreId]);

  useEffect(() => {
    setRecordForm((current) => ({ ...current, storeId: defaultStoreId ?? null }));
  }, [defaultStoreId]);

  useEffect(() => {
    void refreshOrders(form.storeId ?? undefined);
  }, [form.storeId, refreshOrders]);

  useEffect(() => {
    const loadDevices = async () => {
      if (!form.storeId) {
        setDevices([]);
        return;
      }
      try {
        const data = await getDevices(token, form.storeId);
        setDevices(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los dispositivos");
      }
    };

    void loadDevices();
  }, [form.storeId, token]);

  useEffect(() => {
    const loadRecordDevices = async () => {
      if (!recordForm.storeId) {
        setRecordDevices([]);
        return;
      }
      try {
        const data = await getDevices(token, recordForm.storeId);
        setRecordDevices(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los productos disponibles");
      }
    };

    void loadRecordDevices();
  }, [recordForm.storeId, token]);

  const handleRecordFiltersDraftChange = <Field extends keyof PurchaseRecordFilters>(
    field: Field,
    value: PurchaseRecordFilters[Field],
  ) => {
    setRecordFiltersDraft((current) => ({ ...current, [field]: value }));
  };

  const handleVendorFiltersDraftChange = <Field extends keyof VendorFilters>(
    field: Field,
    value: VendorFilters[Field],
  ) => {
    setVendorFiltersDraft((current) => ({ ...current, [field]: value }));
  };

  const handleVendorHistoryFiltersDraftChange = <Field extends keyof VendorHistoryFilters>(
    field: Field,
    value: VendorHistoryFilters[Field],
  ) => {
    setVendorHistoryFiltersDraft((current) => ({ ...current, [field]: value }));
  };

  const updateForm = (updates: Partial<PurchaseForm>) => {
    setForm((current) => ({ ...current, ...updates }));
  };

  const updateRecordForm = (updates: Partial<PurchaseRecordForm>) => {
    setRecordForm((current) => ({ ...current, ...updates }));
  };

  const updateRecordItem = (index: number, updates: Partial<PurchaseRecordDraftItem>) => {
    setRecordItems((current) =>
      current.map((item, itemIndex) => (itemIndex === index ? { ...item, ...updates } : item)),
    );
  };

  const addRecordItem = () => {
    setRecordItems((current) => [...current, { ...blankRecordItem }]);
  };

  const removeRecordItem = (index: number) => {
    setRecordItems((current) => {
      if (current.length <= 1) {
        return [{ ...blankRecordItem }];
      }
      return current.filter((_, itemIndex) => itemIndex !== index);
    });
  };

  const recordSubtotal = useMemo(() => {
    return recordItems.reduce((acc, item) => {
      if (!item.productId) {
        return acc;
      }
      const quantity = Number.isFinite(item.quantity) ? Math.max(0, item.quantity) : 0;
      const unitCost = Number.isFinite(item.unitCost) ? Math.max(0, item.unitCost) : 0;
      return acc + quantity * unitCost;
    }, 0);
  }, [recordItems]);

  const taxRate = recordForm.taxRate >= 0 ? recordForm.taxRate : 0;
  const recordTax = useMemo(() => recordSubtotal * taxRate, [recordSubtotal, taxRate]);
  const recordTotal = useMemo(() => recordSubtotal + recordTax, [recordSubtotal, recordTax]);

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.storeId || !form.deviceId) {
      setError("Selecciona sucursal y dispositivo.");
      return;
    }
    if (!form.supplier.trim()) {
      setError("Indica un proveedor válido.");
      return;
    }
    const reason = askReason("Motivo corporativo de la compra");
    if (!reason) {
      return;
    }
    try {
      setError(null);
      await createPurchaseOrder(
        token,
        {
          store_id: form.storeId,
          supplier: form.supplier.trim(),
          items: [
            {
              device_id: form.deviceId,
              quantity_ordered: Math.max(1, form.quantity),
              unit_cost: Math.max(0, form.unitCost),
            },
          ],
        },
        reason,
      );
      setMessage("Orden de compra registrada correctamente");
      setForm((current) => ({ ...initialForm, storeId: current.storeId }));
      await refreshOrders(form.storeId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible crear la orden de compra");
    }
  };

  const handleReceive = async (order: PurchaseOrder) => {
    const reason = askReason("Motivo de la recepción");
    if (!reason) {
      return;
    }
    const pendingItems = order.items
      .map((item) => ({
        device_id: item.device_id,
        quantity: Math.max(0, item.quantity_ordered - item.quantity_received),
      }))
      .filter((entry) => entry.quantity > 0);

    if (pendingItems.length === 0) {
      setMessage("La orden ya fue recibida por completo.");
      return;
    }
    const itemsWithBatch: PurchaseReceiveInput["items"] = [];
    for (const entry of pendingItems) {
      const deviceInfo =
        recordDevices.find((device) => device.id === entry.device_id) ??
        devices.find((device) => device.id === entry.device_id);
      const promptLabel = deviceInfo
        ? `Lote recibido para ${deviceInfo.sku} · ${deviceInfo.name} (opcional)`
        : `Lote recibido para el dispositivo #${entry.device_id} (opcional)`;
      const batchInput = window.prompt(promptLabel, "");
      if (batchInput === null) {
        setMessage("Recepción cancelada por el usuario.");
        return;
      }
      const normalizedBatch = batchInput.trim();
      if (normalizedBatch) {
        itemsWithBatch.push({ ...entry, batch_code: normalizedBatch });
      } else {
        itemsWithBatch.push(entry);
      }
    }

    try {
      await receivePurchaseOrder(token, order.id, { items: itemsWithBatch }, reason);
      setMessage("Orden actualizada y productos recibidos");
      await refreshOrders(order.store_id);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible recibir la orden");
    }
  };

  const handleCancel = async (order: PurchaseOrder) => {
    const reason = askReason("Motivo de cancelación");
    if (!reason) {
      return;
    }
    try {
      await cancelPurchaseOrder(token, order.id, reason);
      setMessage("Orden cancelada");
      await refreshOrders(order.store_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cancelar la orden");
    }
  };

  const handleVendorFormSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedName = vendorForm.nombre.trim();
    if (normalizedName.length < 3) {
      setError("Indica un nombre válido para el proveedor.");
      return;
    }
    const reason = askReason("Motivo corporativo para guardar proveedor");
    if (!reason) {
      return;
    }
    setVendorSaving(true);
    try {
      setError(null);
      const payload: PurchaseVendorPayload = { nombre: normalizedName };
      const telefonoNormalized = vendorForm.telefono.trim();
      if (telefonoNormalized) {
        payload.telefono = telefonoNormalized;
      }
      const correoNormalized = vendorForm.correo.trim();
      if (correoNormalized) {
        payload.correo = correoNormalized;
      }
      const direccionNormalized = vendorForm.direccion.trim();
      if (direccionNormalized) {
        payload.direccion = direccionNormalized;
      }
      const tipoNormalized = vendorForm.tipo.trim();
      if (tipoNormalized) {
        payload.tipo = tipoNormalized;
      }
      const notasNormalized = vendorForm.notas.trim();
      if (notasNormalized) {
        payload.notas = notasNormalized;
      }
      if (editingVendorId) {
        await updatePurchaseVendor(token, editingVendorId, payload, reason);
        setMessage("Proveedor actualizado correctamente");
      } else {
        await createPurchaseVendor(token, payload, reason);
        setMessage("Proveedor registrado correctamente");
      }
      setVendorForm({ ...emptyVendorForm });
      setEditingVendorId(null);
      await loadVendors();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible guardar el proveedor");
    } finally {
      setVendorSaving(false);
    }
  };

  const handleVendorInputChange = <Field extends keyof VendorForm>(field: Field, value: VendorForm[Field]) => {
    setVendorForm((current) => ({ ...current, [field]: value }));
  };

  const resetVendorForm = () => {
    setVendorForm({ ...emptyVendorForm });
    setEditingVendorId(null);
  };

  const handleVendorEdit = (vendor: PurchaseVendor) => {
    setVendorForm({
      nombre: vendor.nombre,
      telefono: vendor.telefono ?? "",
      correo: vendor.correo ?? "",
      direccion: vendor.direccion ?? "",
      tipo: vendor.tipo ?? "",
      notas: vendor.notas ?? "",
    });
    setEditingVendorId(vendor.id_proveedor);
  };

  const handleVendorStatusToggle = async (vendor: PurchaseVendor, nextStatus: "activo" | "inactivo") => {
    const reason = askReason(
      nextStatus === "inactivo"
        ? "Motivo corporativo para desactivar proveedor"
        : "Motivo corporativo para reactivar proveedor",
    );
    if (!reason) {
      return;
    }
    try {
      setError(null);
      await setPurchaseVendorStatus(token, vendor.id_proveedor, { estado: nextStatus }, reason);
      setMessage(`Proveedor ${nextStatus === "inactivo" ? "desactivado" : "reactivado"} correctamente`);
      await loadVendors();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible actualizar el estado del proveedor");
    }
  };

  const handleVendorExport = async () => {
    const reason = askReason("Motivo corporativo para exportar proveedores");
    if (!reason) {
      return;
    }
    try {
      setVendorExporting(true);
      const exportArgs: Parameters<typeof exportPurchaseVendorsCsv>[1] = {};
      const queryNormalized = vendorFilters.query.trim();
      const statusNormalized = vendorFilters.status.trim();
      if (queryNormalized) {
        exportArgs.query = queryNormalized;
      }
      if (statusNormalized) {
        exportArgs.status = statusNormalized;
      }
      const blob = await exportPurchaseVendorsCsv(token, exportArgs, reason);
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      downloadBlob(blob, `proveedores_compras_${timestamp}.csv`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible exportar los proveedores");
    } finally {
      setVendorExporting(false);
    }
  };

  const handleVendorFiltersSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setVendorFilters(vendorFiltersDraft);
  };

  const handleVendorFiltersReset = () => {
    setVendorFiltersDraft({ ...emptyVendorFilters });
    setVendorFilters({ ...emptyVendorFilters });
  };

  const handleVendorHistoryFiltersSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setVendorHistoryFilters(vendorHistoryFiltersDraft);
  };

  const handleVendorHistoryFiltersReset = () => {
    setVendorHistoryFiltersDraft({ ...emptyVendorHistoryFilters });
    setVendorHistoryFilters({ ...emptyVendorHistoryFilters });
  };

  const handleSelectVendor = (vendorId: number) => {
    setSelectedVendorId(vendorId);
  };

  const handleRecordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!recordForm.vendorId) {
      setError("Selecciona un proveedor de compras.");
      return;
    }
    const validItems = recordItems.filter(
      (item) => item.productId && Number.isFinite(item.quantity) && item.quantity > 0,
    );
    if (validItems.length === 0) {
      setError("Agrega al menos un producto válido.");
      return;
    }
    const reason = askReason("Motivo corporativo del registro de compra");
    if (!reason) {
      return;
    }
    const payload: PurchaseRecordPayload = {
      proveedor_id: recordForm.vendorId,
      forma_pago: recordForm.paymentMethod,
      items: validItems.map((item) => ({
        producto_id: item.productId as number,
        cantidad: Math.max(1, Math.trunc(item.quantity)),
        costo_unitario: Math.max(0, item.unitCost),
      })),
    };
    const statusNormalized = recordForm.status.trim();
    if (statusNormalized) {
      payload.estado = statusNormalized;
    }
    if (recordForm.taxRate >= 0) {
      payload.impuesto_tasa = recordForm.taxRate;
    }
    if (recordForm.date) {
      payload.fecha = new Date(recordForm.date).toISOString();
    }
    try {
      setError(null);
      await createPurchaseRecord(token, payload, reason);
      setMessage("Compra registrada correctamente");
      setRecordForm((current) => ({ ...recordInitialForm, storeId: current.storeId }));
      setRecordItems([{ ...blankRecordItem }]);
      await loadRecords();
      await loadStatistics();
      await loadVendors();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible registrar la compra");
    }
  };

  const handleRecordFiltersSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setRecordFilters(recordFiltersDraft);
  };

  const handleRecordFiltersReset = () => {
    setRecordFiltersDraft({ ...emptyRecordFilters });
    setRecordFilters({ ...emptyRecordFilters });
  };

  const handleExportRecords = async (format: "pdf" | "xlsx") => {
    const reason = askReason(
      format === "pdf"
        ? "Motivo corporativo para exportar compras a PDF"
        : "Motivo corporativo para exportar compras a Excel",
    );
    if (!reason) {
      return;
    }
    const filters: Parameters<typeof exportPurchaseRecordsPdf>[1] = {};
    if (recordFilters.vendorId) {
      filters.proveedorId = Number(recordFilters.vendorId);
    }
    if (recordFilters.userId) {
      filters.usuarioId = Number(recordFilters.userId);
    }
    const fromNormalized = recordFilters.dateFrom.trim();
    if (fromNormalized) {
      filters.dateFrom = fromNormalized;
    }
    const toNormalized = recordFilters.dateTo.trim();
    if (toNormalized) {
      filters.dateTo = toNormalized;
    }
    const statusNormalized = recordFilters.status.trim();
    if (statusNormalized) {
      filters.estado = statusNormalized;
    }
    const searchNormalized = recordFilters.search.trim();
    if (searchNormalized) {
      filters.query = searchNormalized;
    }
    try {
      const blob =
        format === "pdf"
          ? await exportPurchaseRecordsPdf(token, filters, reason)
          : await exportPurchaseRecordsExcel(token, filters, reason);
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const filename =
        format === "pdf"
          ? `compras_registradas_${timestamp}.pdf`
          : `compras_registradas_${timestamp}.xlsx`;
      downloadBlob(blob, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible exportar las compras registradas");
    }
  };

  const handleReturn = async (order: PurchaseOrder) => {
    const firstItem = order.items[0];
    if (!firstItem) {
      return;
    }
    const deviceId = firstItem.device_id;
    const quantityRaw = window.prompt("Cantidad a devolver al proveedor", "1");
    const quantity = quantityRaw ? Number(quantityRaw) : NaN;
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError("Indica una cantidad válida para la devolución.");
      return;
    }
    const reason = askReason("Motivo corporativo de la devolución");
    if (!reason) {
      return;
    }
    try {
      await registerPurchaseReturn(
        token,
        order.id,
        { device_id: deviceId, quantity, reason },
        reason,
      );
      setMessage("Devolución al proveedor registrada");
      await refreshOrders(form.storeId);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible registrar la devolución");
    }
  };

  const handleImportCsv = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const fileInput = event.currentTarget.elements.namedItem("csvFile") as HTMLInputElement | null;
    const file = fileInput?.files?.[0];
    if (!file) {
      setError("Selecciona un archivo CSV corporativo.");
      return;
    }
    const reason = askReason("Motivo corporativo de la importación CSV");
    if (!reason) {
      return;
    }
    try {
      setError(null);
      setCsvLoading(true);
      const response = await importPurchaseOrdersCsv(token, file, reason);
      setMessage(`Importación completada: ${response.imported} orden(es).`);
      if (response.errors.length > 0) {
        setError(response.errors.join(" · "));
      }
      const targetStore = form.storeId ?? response.orders[0]?.store_id ?? null;
      if (targetStore) {
        await refreshOrders(targetStore);
      }
      await loadRecurringOrders();
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible importar el CSV de compras");
    } finally {
      setCsvLoading(false);
      event.currentTarget.reset();
    }
  };

  const handleSaveTemplate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.storeId || !form.deviceId) {
      setError("Selecciona sucursal y dispositivo antes de guardar la plantilla.");
      return;
    }
    if (!form.supplier.trim()) {
      setError("Indica un proveedor válido antes de guardar la plantilla.");
      return;
    }
    const normalizedName = templateName.trim();
    if (normalizedName.length < 3) {
      setError("El nombre de la plantilla debe tener al menos 3 caracteres.");
      return;
    }
    const reason = askReason("Motivo corporativo para guardar la plantilla");
    if (!reason) {
      return;
    }
    const normalizedDescription = templateDescription.trim();
    const templatePayload: Record<string, unknown> = {
      store_id: form.storeId,
      supplier: form.supplier.trim(),
      items: [
        {
          device_id: form.deviceId,
          quantity_ordered: Math.max(1, form.quantity),
          unit_cost: Math.max(0, form.unitCost),
        },
      ],
    };
    if (normalizedDescription) {
      templatePayload.notes = normalizedDescription;
    }

    const payload: RecurringOrderPayload = {
      name: normalizedName,
      order_type: "purchase",
      payload: templatePayload,
    };
    if (normalizedDescription) {
      payload.description = normalizedDescription;
    }
    try {
      setError(null);
      setTemplateSaving(true);
      await createRecurringOrder(token, payload, reason);
      setMessage("Plantilla de compra guardada correctamente.");
      setTemplateName("");
      setTemplateDescription("");
      await loadRecurringOrders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible guardar la plantilla");
    } finally {
      setTemplateSaving(false);
    }
  };

  const handleApplyTemplate = (template: RecurringOrder) => {
    const payload = template.payload as Record<string, unknown>;
    const items = Array.isArray(payload?.items) ? (payload.items as Record<string, unknown>[]) : [];
    const firstItem = items[0] ?? {};
    const supplierValue = typeof payload?.supplier === "string" ? (payload.supplier as string) : form.supplier;
    const storeValue = typeof payload?.store_id === "number" ? (payload.store_id as number) : form.storeId;
    setForm({
      storeId: storeValue ?? null,
      supplier: supplierValue,
      deviceId: typeof firstItem.device_id === "number" ? (firstItem.device_id as number) : form.deviceId,
      quantity: typeof firstItem.quantity_ordered === "number" ? (firstItem.quantity_ordered as number) : form.quantity,
      unitCost: typeof firstItem.unit_cost === "number" ? (firstItem.unit_cost as number) : form.unitCost,
    });
    setMessage(`Plantilla "${template.name}" aplicada al formulario.`);
  };

  const handleExecuteTemplate = async (template: RecurringOrder) => {
    const reason = askReason(`Motivo corporativo para ejecutar "${template.name}"`);
    if (!reason) {
      return;
    }
    try {
      setError(null);
      const result = await executeRecurringOrder(token, template.id, reason);
      setMessage(result.summary);
      const targetStore = template.store_id ?? form.storeId;
      if (targetStore) {
        await refreshOrders(targetStore);
      }
      await loadRecurringOrders();
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible ejecutar la plantilla");
    }
  };

  const getTemplateSupplier = (template: RecurringOrder): string => {
    const payload = template.payload as Record<string, unknown>;
    if (payload && typeof payload.supplier === "string") {
      return payload.supplier as string;
    }
    return template.store_name ?? "Proveedor no especificado";
  };

  return {
    orders,
    devices,
    recurringOrders,
    form,
    recordForm,
    recordItems,
    recordDevices,
    vendors,
    records,
    statistics,
    users,
    recordFiltersDraft,
    vendorFiltersDraft,
    vendorHistoryFiltersDraft,
    vendorForm,
    editingVendorId,
    selectedVendor,
    vendorHistory,
    vendorSaving,
    vendorExporting,
    vendorsLoading,
    vendorHistoryLoading,
    usersLoading,
    recordsLoading,
    statsLoading,
    recordStatusOptions,
    recordSubtotal,
    recordTax,
    recordTotal,
    paymentOptions,
    currencyFormatter,
    templateName,
    templateDescription,
    csvLoading,
    templateSaving,
    recurringLoading,
    loading,
    message,
    error,
    selectedStore,
    setTemplateName,
    setTemplateDescription,
    handleRecordFiltersDraftChange,
    handleVendorFiltersDraftChange,
    handleVendorHistoryFiltersDraftChange,
    updateForm,
    updateRecordForm,
    updateRecordItem,
    addRecordItem,
    removeRecordItem,
    handleCreate,
    handleRecordSubmit,
    handleRecordFiltersSubmit,
    handleRecordFiltersReset,
    handleExportRecords,
    handleVendorFormSubmit,
    handleVendorInputChange,
    resetVendorForm,
    handleVendorFiltersSubmit,
    handleVendorFiltersReset,
    handleVendorExport,
    handleVendorEdit,
    handleVendorStatusToggle,
    handleVendorHistoryFiltersSubmit,
    handleVendorHistoryFiltersReset,
    handleSelectVendor,
    handleImportCsv,
    handleSaveTemplate,
    handleApplyTemplate,
    handleExecuteTemplate,
    getTemplateSupplier,
    handleReceive,
    handleReturn,
    handleCancel,
  } as const;
};

export type PurchasesControllerState = ReturnType<typeof usePurchasesController>;

export { paymentOptions };
