import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import type {
  Device,
  PurchaseOrder,
  PurchaseRecord,
  PurchaseRecordPayload,
  PurchaseStatistics,
  PurchaseVendor,
  PurchaseVendorHistory,
  PurchaseVendorPayload,
  RecurringOrder,
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
 
const statusLabels: Record<PurchaseOrder["status"], string> = {
  PENDIENTE: "Pendiente",
  PARCIAL: "Recepción parcial",
  COMPLETADA: "Completada",
  CANCELADA: "Cancelada",
};

type Props = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

type PurchaseForm = {
  storeId: number | null;
  supplier: string;
  deviceId: number | null;
  quantity: number;
  unitCost: number;
};

const initialForm: PurchaseForm = {
  storeId: null,
  supplier: "",
  deviceId: null,
  quantity: 1,
  unitCost: 0,
};

type PurchaseRecordForm = {
  storeId: number | null;
  vendorId: number | null;
  paymentMethod: string;
  status: string;
  taxRate: number;
  date: string;
};

type PurchaseRecordDraftItem = {
  productId: number | null;
  quantity: number;
  unitCost: number;
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

const paymentOptions = ["EFECTIVO", "TRANSFERENCIA", "TARJETA", "CREDITO", "OTRO"];

const recordStatuses = ["REGISTRADA", "PAGADA", "CANCELADA", "DEVUELTA"] as const;

type VendorFilters = {
  query: string;
  status: string;
};

type VendorForm = {
  nombre: string;
  telefono: string;
  correo: string;
  direccion: string;
  tipo: string;
  notas: string;
};

type VendorHistoryFilters = {
  limit: number;
  dateFrom: string;
  dateTo: string;
};

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

const emptyRecordFilters = {
  vendorId: "",
  userId: "",
  dateFrom: "",
  dateTo: "",
  status: "",
  search: "",
};

function Purchases({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [recurringOrders, setRecurringOrders] = useState<RecurringOrder[]>([]);
  const [form, setForm] = useState<PurchaseForm>({ ...initialForm, storeId: defaultStoreId });
  const [recordForm, setRecordForm] = useState<PurchaseRecordForm>({
    ...recordInitialForm,
    storeId: defaultStoreId ?? null,
  });
  const [recordItems, setRecordItems] = useState<PurchaseRecordDraftItem[]>([
    { ...blankRecordItem },
  ]);
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

  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }),
    []
  );

  const selectedStore = useMemo(
    () => stores.find((store) => store.id === form.storeId) ?? null,
    [stores, form.storeId]
  );

  const selectedVendor = useMemo(
    () => vendors.find((vendor) => vendor.id_proveedor === selectedVendorId) ?? null,
    [vendors, selectedVendorId]
  );

  const recordStatusOptions = useMemo(() => {
    const baseStatuses = [...recordStatuses];
    if (recordForm.status && !baseStatuses.includes(recordForm.status)) {
      baseStatuses.push(recordForm.status);
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

  const refreshOrders = async (storeId?: number | null) => {
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
  };

  const loadVendors = useCallback(async () => {
    try {
      setVendorsLoading(true);
      const data = await listPurchaseVendors(token, {
        limit: 200,
        query: vendorFilters.query ? vendorFilters.query.trim() : undefined,
        status: vendorFilters.status ? vendorFilters.status.trim() : undefined,
      });
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
        const data = await getPurchaseVendorHistory(token, vendorId, {
          limit: vendorHistoryFilters.limit,
          dateFrom: vendorHistoryFilters.dateFrom || undefined,
          dateTo: vendorHistoryFilters.dateTo || undefined,
        });
        setVendorHistory(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible obtener el historial del proveedor");
      } finally {
        setVendorHistoryLoading(false);
      }
    },
    [token, vendorHistoryFilters]
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
      const data = await listPurchaseRecords(token, {
        proveedorId: recordFilters.vendorId ? Number(recordFilters.vendorId) : undefined,
        usuarioId: recordFilters.userId ? Number(recordFilters.userId) : undefined,
        dateFrom: recordFilters.dateFrom || undefined,
        dateTo: recordFilters.dateTo || undefined,
        estado: recordFilters.status || undefined,
        query: recordFilters.search || undefined,
        limit: 200,
      });
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
    loadRecurringOrders();
  }, [loadRecurringOrders]);

  useEffect(() => {
    loadVendors();
  }, [loadVendors]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    loadRecords();
  }, [loadRecords]);

  useEffect(() => {
    loadStatistics();
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
    refreshOrders(form.storeId ?? undefined);
  }, [form.storeId, token]);

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

    loadDevices();
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

  const updateForm = (updates: Partial<PurchaseForm>) => {
    setForm((current) => ({ ...current, ...updates }));
  };

  const updateRecordForm = (updates: Partial<PurchaseRecordForm>) => {
    setRecordForm((current) => ({ ...current, ...updates }));
  };

  const updateRecordItem = (index: number, updates: Partial<PurchaseRecordDraftItem>) => {
    setRecordItems((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              ...updates,
            }
          : item
      )
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
        reason
      );
      setMessage("Orden de compra registrada correctamente");
      setForm((current) => ({ ...initialForm, storeId: current.storeId }));
      await refreshOrders(form.storeId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible crear la orden de compra");
    }
  };

  const askReason = (promptText: string) => {
    const reason = window.prompt(promptText, "");
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo (mínimo 5 caracteres).");
      return null;
    }
    return reason.trim();
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleVendorFiltersSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setVendorFilters(vendorFiltersDraft);
  };

  const handleVendorFiltersReset = () => {
    setVendorFiltersDraft({ ...emptyVendorFilters });
    setVendorFilters({ ...emptyVendorFilters });
  };

  const handleVendorInputChange = (field: keyof VendorForm, value: string) => {
    setVendorForm((current) => ({ ...current, [field]: value }));
  };

  const resetVendorForm = () => {
    setVendorForm({ ...emptyVendorForm });
    setEditingVendorId(null);
  };

  const handleVendorFormSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!vendorForm.nombre.trim()) {
      setError("Indica el nombre del proveedor.");
      return;
    }
    const payload: PurchaseVendorPayload = {
      nombre: vendorForm.nombre.trim(),
      telefono: vendorForm.telefono.trim() || undefined,
      correo: vendorForm.correo.trim() || undefined,
      direccion: vendorForm.direccion.trim() || undefined,
      tipo: vendorForm.tipo.trim() || undefined,
      notas: vendorForm.notas.trim() || undefined,
    };
    const reason = askReason(
      editingVendorId ? "Motivo corporativo para actualizar proveedor" : "Motivo corporativo para registrar proveedor"
    );
    if (!reason) {
      return;
    }
    try {
      setVendorSaving(true);
      setError(null);
      if (editingVendorId) {
        await updatePurchaseVendor(token, editingVendorId, payload, reason);
        setMessage("Proveedor actualizado correctamente");
      } else {
        await createPurchaseVendor(token, payload, reason);
        setMessage("Proveedor registrado correctamente");
      }
      resetVendorForm();
      await loadVendors();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible guardar el proveedor");
    } finally {
      setVendorSaving(false);
    }
  };

  const handleVendorEdit = (vendor: PurchaseVendor) => {
    setEditingVendorId(vendor.id_proveedor);
    setVendorForm({
      nombre: vendor.nombre,
      telefono: vendor.telefono ?? "",
      correo: vendor.correo ?? "",
      direccion: vendor.direccion ?? "",
      tipo: vendor.tipo ?? "",
      notas: vendor.notas ?? "",
    });
  };

  const handleVendorStatusToggle = async (vendor: PurchaseVendor) => {
    const nextStatus = vendor.estado === "activo" ? "inactivo" : "activo";
    const reason = askReason(
      nextStatus === "inactivo"
        ? `Motivo corporativo para desactivar a ${vendor.nombre}`
        : `Motivo corporativo para reactivar a ${vendor.nombre}`
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
      const blob = await exportPurchaseVendorsCsv(
        token,
        {
          query: vendorFilters.query ? vendorFilters.query.trim() : undefined,
          status: vendorFilters.status ? vendorFilters.status.trim() : undefined,
        },
        reason
      );
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      downloadBlob(blob, `proveedores_compras_${timestamp}.csv`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible exportar los proveedores");
    } finally {
      setVendorExporting(false);
    }
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
      (item) => item.productId && Number.isFinite(item.quantity) && item.quantity > 0
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
      estado: recordForm.status || undefined,
      impuesto_tasa: recordForm.taxRate >= 0 ? recordForm.taxRate : undefined,
      fecha: recordForm.date ? new Date(recordForm.date).toISOString() : undefined,
      items: validItems.map((item) => ({
        producto_id: item.productId as number,
        cantidad: Math.max(1, Math.trunc(item.quantity)),
        costo_unitario: Math.max(0, item.unitCost),
      })),
    };
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
        : "Motivo corporativo para exportar compras a Excel"
    );
    if (!reason) {
      return;
    }
    const filters = {
      proveedorId: recordFilters.vendorId ? Number(recordFilters.vendorId) : undefined,
      usuarioId: recordFilters.userId ? Number(recordFilters.userId) : undefined,
      dateFrom: recordFilters.dateFrom || undefined,
      dateTo: recordFilters.dateTo || undefined,
      estado: recordFilters.status || undefined,
      query: recordFilters.search || undefined,
    };
    try {
      const blob =
        format === "pdf"
          ? await exportPurchaseRecordsPdf(token, filters, reason)
          : await exportPurchaseRecordsExcel(token, filters, reason);
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const filename = `compras_${timestamp}.${format}`;
      downloadBlob(blob, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible exportar el historial de compras");
    }
  };

  const handleReceive = async (order: PurchaseOrder) => {
    const pendingItems = order.items.filter((item) => item.quantity_ordered > item.quantity_received);
    if (pendingItems.length === 0) {
      setMessage("La orden ya fue recibida en su totalidad.");
      return;
    }
    const reason = askReason("Motivo de la recepción");
    if (!reason) {
      return;
    }
    try {
      setError(null);
      const payload = {
        items: pendingItems.map((item) => ({
          device_id: item.device_id,
          quantity: item.quantity_ordered - item.quantity_received,
        })),
      };
      await receivePurchaseOrder(token, order.id, payload, reason);
      setMessage("Recepción aplicada correctamente");
      await refreshOrders(form.storeId);
      onInventoryRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible recibir la orden");
    }
  };

  const handleCancel = async (order: PurchaseOrder) => {
    if (order.status === "COMPLETADA" || order.status === "CANCELADA") {
      setMessage("La orden ya está cerrada.");
      return;
    }
    const reason = askReason("Motivo de cancelación");
    if (!reason) {
      return;
    }
    try {
      setError(null);
      await cancelPurchaseOrder(token, order.id, reason);
      setMessage("Orden cancelada");
      await refreshOrders(form.storeId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cancelar la orden");
    }
  };

  const handleReturn = async (order: PurchaseOrder) => {
    if (order.items.length === 0) {
      return;
    }
    const deviceId = order.items[0].device_id;
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
        reason
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
    const payload = {
      name: normalizedName,
      description: normalizedDescription || undefined,
      order_type: "purchase" as const,
      payload: {
        store_id: form.storeId,
        supplier: form.supplier.trim(),
        notes: normalizedDescription || undefined,
        items: [
          {
            device_id: form.deviceId,
            quantity_ordered: Math.max(1, form.quantity),
            unit_cost: Math.max(0, form.unitCost),
          },
        ],
      },
    };
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

  return (
    <>
      {error ? <div className="alert error">{error}</div> : null}
      {message ? <div className="alert success">{message}</div> : null}

      <section className="card">
        <h2>Registro directo de compras</h2>
        <p className="card-subtitle">
          Captura compras inmediatas con impuestos calculados automáticamente y vínculos al inventario seleccionado.
        </p>
        <form className="form-grid" onSubmit={handleRecordSubmit}>
          <label>
            Proveedor
            <select
              value={recordForm.vendorId ?? ""}
              onChange={(event) =>
                updateRecordForm({ vendorId: event.target.value ? Number(event.target.value) : null })
              }
            >
              <option value="">Selecciona un proveedor</option>
              {vendors.map((vendor) => (
                <option key={vendor.id_proveedor} value={vendor.id_proveedor}>
                  {vendor.nombre}
                </option>
              ))}
            </select>
          </label>
          <label>
            Sucursal de referencia
            <select
              value={recordForm.storeId ?? ""}
              onChange={(event) =>
                updateRecordForm({ storeId: event.target.value ? Number(event.target.value) : null })
              }
            >
              <option value="">Opcional</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Método de pago
            <select
              value={recordForm.paymentMethod}
              onChange={(event) => updateRecordForm({ paymentMethod: event.target.value })}
            >
              {paymentOptions.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </label>
          <label>
            Estado
            <select
              value={recordForm.status}
              onChange={(event) => updateRecordForm({ status: event.target.value })}
            >
              {recordStatusOptions.map((statusValue) => (
                <option key={statusValue} value={statusValue}>
                  {statusValue}
                </option>
              ))}
            </select>
          </label>
          <label>
            Fecha de la compra
            <input
              type="date"
              value={recordForm.date}
              onChange={(event) => updateRecordForm({ date: event.target.value })}
            />
          </label>
          <label>
            Tasa de impuesto
            <input
              type="number"
              min={0}
              max={1}
              step="0.01"
              value={recordForm.taxRate}
              onChange={(event) => updateRecordForm({ taxRate: Number(event.target.value) })}
            />
          </label>

          <div className="table-responsive form-span">
            <table>
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Cantidad</th>
                  <th>Costo unitario</th>
                  <th>Subtotal</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {recordItems.map((item, index) => (
                  <tr key={`record-item-${index}`}>
                    <td>
                      <select
                        value={item.productId ?? ""}
                        onChange={(event) =>
                          updateRecordItem(index, {
                            productId: event.target.value ? Number(event.target.value) : null,
                          })
                        }
                      >
                        <option value="">Selecciona un producto</option>
                        {recordDevices.map((device) => (
                          <option key={device.id} value={device.id}>
                            {device.sku} · {device.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="number"
                        min={1}
                        value={item.quantity}
                        onChange={(event) =>
                          updateRecordItem(index, { quantity: Number(event.target.value) })
                        }
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min={0}
                        step="0.01"
                        value={item.unitCost}
                        onChange={(event) =>
                          updateRecordItem(index, { unitCost: Number(event.target.value) })
                        }
                      />
                    </td>
                    <td>{currencyFormatter.format(Math.max(0, item.quantity) * Math.max(0, item.unitCost))}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn--ghost"
                        onClick={() => removeRecordItem(index)}
                        disabled={recordItems.length === 1}
                      >
                        Quitar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="form-actions form-span">
            <div className="actions-row">
              <button type="button" className="btn btn--secondary" onClick={addRecordItem}>
                Agregar producto
              </button>
            </div>
            <div className="totals-card">
              <span>
                <strong>Subtotal:</strong> {currencyFormatter.format(recordSubtotal)}
              </span>
              <span>
                <strong>Impuestos:</strong> {currencyFormatter.format(recordTax)}
              </span>
              <span>
                <strong>Total:</strong> {currencyFormatter.format(recordTotal)}
              </span>
            </div>
          </div>
          <button type="submit" className="btn btn--primary form-span">
            Registrar compra
          </button>
        </form>
      </section>

      <section className="card">
        <h2>Listado general de compras</h2>
        <p className="card-subtitle">
          Consulta todas las compras registradas y filtra por proveedor, fechas o usuario responsable.
        </p>
        <form className="form-grid" onSubmit={handleRecordFiltersSubmit}>
          <label>
            Proveedor
            <select
              value={recordFiltersDraft.vendorId}
              onChange={(event) =>
                setRecordFiltersDraft((current) => ({ ...current, vendorId: event.target.value }))
              }
            >
              <option value="">Todos</option>
              {vendors.map((vendor) => (
                <option key={vendor.id_proveedor} value={vendor.id_proveedor}>
                  {vendor.nombre}
                </option>
              ))}
            </select>
          </label>
          <label>
            Usuario
            <select
              value={recordFiltersDraft.userId}
              onChange={(event) =>
                setRecordFiltersDraft((current) => ({ ...current, userId: event.target.value }))
              }
            >
              <option value="">Todos</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name || user.username}
                </option>
              ))}
            </select>
          </label>
          <label>
            Desde
            <input
              type="date"
              value={recordFiltersDraft.dateFrom}
              onChange={(event) =>
                setRecordFiltersDraft((current) => ({ ...current, dateFrom: event.target.value }))
              }
            />
          </label>
          <label>
            Hasta
            <input
              type="date"
              value={recordFiltersDraft.dateTo}
              onChange={(event) =>
                setRecordFiltersDraft((current) => ({ ...current, dateTo: event.target.value }))
              }
            />
          </label>
          <label>
            Estado
            <input
              value={recordFiltersDraft.status}
              onChange={(event) =>
                setRecordFiltersDraft((current) => ({ ...current, status: event.target.value }))
              }
              placeholder="Ej. REGISTRADA"
            />
          </label>
          <label>
            Búsqueda
            <input
              value={recordFiltersDraft.search}
              onChange={(event) =>
                setRecordFiltersDraft((current) => ({ ...current, search: event.target.value }))
              }
              placeholder="Proveedor, referencia..."
            />
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn--primary">
              Aplicar filtros
            </button>
            <button type="button" className="btn btn--ghost" onClick={handleRecordFiltersReset}>
              Limpiar
            </button>
          </div>
        </form>
        <div className="actions-row">
          <button type="button" className="btn btn--secondary" onClick={() => handleExportRecords("pdf")}>
            Exportar PDF
          </button>
          <button type="button" className="btn btn--secondary" onClick={() => handleExportRecords("xlsx")}>
            Exportar Excel
          </button>
        </div>
        {recordsLoading ? <p className="muted-text">Cargando compras…</p> : null}
        {!recordsLoading && records.length === 0 ? (
          <p className="muted-text">No hay compras registradas con los filtros actuales.</p>
        ) : null}
        {!recordsLoading && records.length > 0 ? (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Proveedor</th>
                  <th>Fecha</th>
                  <th>Total</th>
                  <th>Impuesto</th>
                  <th>Pago</th>
                  <th>Estado</th>
                  <th>Usuario</th>
                  <th>Productos</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr key={record.id_compra}>
                    <td>#{record.id_compra}</td>
                    <td>{record.proveedor_nombre}</td>
                    <td>{new Date(record.fecha).toLocaleString("es-MX")}</td>
                    <td>{currencyFormatter.format(record.total)}</td>
                    <td>{currencyFormatter.format(record.impuesto)}</td>
                    <td>{record.forma_pago}</td>
                    <td>{record.estado}</td>
                    <td>{record.usuario_nombre || "—"}</td>
                    <td>
                      <ul className="compact-list">
                        {record.items.map((item) => (
                          <li key={item.id_detalle}>
                            {(item.producto_nombre || `Producto #${item.producto_id}`) + " · "}
                            {item.cantidad} × {currencyFormatter.format(item.costo_unitario)}
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="card">
        <h2>Panel de proveedores</h2>
        <p className="card-subtitle">
          Administra proveedores corporativos, consulta su historial y exporta la información en un clic.
        </p>

        <div className="section-grid">
          <form className="form-grid" onSubmit={handleVendorFormSubmit}>
            <h3 className="form-span">
              {editingVendorId ? "Editar proveedor" : "Registrar nuevo proveedor"}
            </h3>
            <label className="form-span">
              Nombre
              <input
                value={vendorForm.nombre}
                onChange={(event) => handleVendorInputChange("nombre", event.target.value)}
                placeholder="Proveedor corporativo"
                required
              />
            </label>
            <label>
              Teléfono
              <input
                value={vendorForm.telefono}
                onChange={(event) => handleVendorInputChange("telefono", event.target.value)}
                placeholder="Opcional"
              />
            </label>
            <label>
              Correo
              <input
                type="email"
                value={vendorForm.correo}
                onChange={(event) => handleVendorInputChange("correo", event.target.value)}
                placeholder="Opcional"
              />
            </label>
            <label>
              Dirección
              <input
                value={vendorForm.direccion}
                onChange={(event) => handleVendorInputChange("direccion", event.target.value)}
                placeholder="Opcional"
              />
            </label>
            <label>
              Tipo
              <input
                value={vendorForm.tipo}
                onChange={(event) => handleVendorInputChange("tipo", event.target.value)}
                placeholder="Ej. Mayorista"
              />
            </label>
            <label className="form-span">
              Notas
              <textarea
                value={vendorForm.notas}
                onChange={(event) => handleVendorInputChange("notas", event.target.value)}
                rows={3}
              />
            </label>
            <div className="form-actions form-span">
              <button type="submit" className="btn btn--primary" disabled={vendorSaving}>
                {vendorSaving
                  ? "Guardando…"
                  : editingVendorId
                  ? "Actualizar proveedor"
                  : "Registrar proveedor"}
              </button>
              {editingVendorId ? (
                <button type="button" className="btn btn--ghost" onClick={resetVendorForm}>
                  Cancelar edición
                </button>
              ) : null}
            </div>
          </form>

          <form className="form-grid" onSubmit={handleVendorFiltersSubmit}>
            <h3 className="form-span">Filtros</h3>
            <label>
              Búsqueda
              <input
                value={vendorFiltersDraft.query}
                onChange={(event) =>
                  setVendorFiltersDraft((current) => ({ ...current, query: event.target.value }))
                }
                placeholder="Nombre, correo o notas"
              />
            </label>
            <label>
              Estado
              <select
                value={vendorFiltersDraft.status}
                onChange={(event) =>
                  setVendorFiltersDraft((current) => ({ ...current, status: event.target.value }))
                }
              >
                <option value="">Todos</option>
                <option value="activo">Activos</option>
                <option value="inactivo">Inactivos</option>
              </select>
            </label>
            <div className="form-actions">
              <button type="submit" className="btn btn--primary">
                Aplicar filtros
              </button>
              <button type="button" className="btn btn--ghost" onClick={handleVendorFiltersReset}>
                Limpiar
              </button>
            </div>
            <button
              type="button"
              className="btn btn--secondary form-span"
              onClick={handleVendorExport}
              disabled={vendorExporting}
            >
              {vendorExporting ? "Exportando…" : "Exportar proveedores CSV"}
            </button>
          </form>
        </div>

        {vendorsLoading ? <p className="muted-text">Cargando proveedores…</p> : null}
        {!vendorsLoading && vendors.length === 0 ? (
          <p className="muted-text">No se encontraron proveedores con los filtros actuales.</p>
        ) : null}

        {!vendorsLoading && vendors.length > 0 ? (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Proveedor</th>
                  <th>Estado</th>
                  <th>Total compras</th>
                  <th>Impuesto</th>
                  <th>Registros</th>
                  <th>Última compra</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {vendors.map((vendor) => (
                  <tr key={vendor.id_proveedor}>
                    <td>
                      <strong>{vendor.nombre}</strong>
                      <br />
                      <small className="muted-text">
                        {vendor.correo ? `${vendor.correo} · ` : ""}
                        {vendor.telefono || "Sin teléfono"}
                      </small>
                    </td>
                    <td>
                      <span className={`badge ${vendor.estado === "activo" ? "success" : "neutral"}`}>
                        {vendor.estado.toUpperCase()}
                      </span>
                    </td>
                    <td>{currencyFormatter.format(vendor.total_compras)}</td>
                    <td>{currencyFormatter.format(vendor.total_impuesto)}</td>
                    <td>{vendor.compras_registradas}</td>
                    <td>{vendor.ultima_compra ? new Date(vendor.ultima_compra).toLocaleString("es-MX") : "—"}</td>
                    <td>
                      <div className="transfer-actions">
                        <button
                          type="button"
                          className="btn btn--ghost"
                          onClick={() => handleSelectVendor(vendor.id_proveedor)}
                        >
                          Ver historial
                        </button>
                        <button
                          type="button"
                          className="btn btn--ghost"
                          onClick={() => handleVendorEdit(vendor)}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="btn btn--ghost"
                          onClick={() => handleVendorStatusToggle(vendor)}
                        >
                          {vendor.estado === "activo" ? "Desactivar" : "Reactivar"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        <div className="section-divider">
          <h3>Detalle e historial del proveedor</h3>
          {!selectedVendor ? (
            <p className="muted-text">Selecciona un proveedor para consultar su historial.</p>
          ) : (
            <div className="section-grid">
              <div className="totals-card">
                <h4>{selectedVendor.nombre}</h4>
                <p className="muted-text">
                  {selectedVendor.tipo ? `${selectedVendor.tipo} · ` : ""}
                  {selectedVendor.estado === "activo" ? "Activo" : "Inactivo"}
                </p>
                {selectedVendor.direccion ? <p>{selectedVendor.direccion}</p> : null}
                {selectedVendor.notas ? <p className="muted-text">{selectedVendor.notas}</p> : null}
                <p>
                  Compras registradas: <strong>{selectedVendor.compras_registradas}</strong>
                </p>
                <p>Total: {currencyFormatter.format(selectedVendor.total_compras)}</p>
                <p>Impuestos: {currencyFormatter.format(selectedVendor.total_impuesto)}</p>
              </div>

              <form className="form-grid" onSubmit={handleVendorHistoryFiltersSubmit}>
                <h4 className="form-span">Filtrar historial</h4>
                <label>
                  Desde
                  <input
                    type="date"
                    value={vendorHistoryFiltersDraft.dateFrom}
                    onChange={(event) =>
                      setVendorHistoryFiltersDraft((current) => ({
                        ...current,
                        dateFrom: event.target.value,
                      }))
                    }
                  />
                </label>
                <label>
                  Hasta
                  <input
                    type="date"
                    value={vendorHistoryFiltersDraft.dateTo}
                    onChange={(event) =>
                      setVendorHistoryFiltersDraft((current) => ({
                        ...current,
                        dateTo: event.target.value,
                      }))
                    }
                  />
                </label>
                <label>
                  Límite
                  <input
                    type="number"
                    min={1}
                    max={200}
                    value={vendorHistoryFiltersDraft.limit}
                    onChange={(event) =>
                      setVendorHistoryFiltersDraft((current) => ({
                        ...current,
                        limit: Number(event.target.value) || 10,
                      }))
                    }
                  />
                </label>
                <div className="form-actions">
                  <button type="submit" className="btn btn--primary">
                    Aplicar
                  </button>
                  <button type="button" className="btn btn--ghost" onClick={handleVendorHistoryFiltersReset}>
                    Limpiar
                  </button>
                </div>
              </form>
            </div>
          )}

          {vendorHistoryLoading ? <p className="muted-text">Cargando historial…</p> : null}
          {!vendorHistoryLoading && vendorHistory && vendorHistory.compras.length === 0 ? (
            <p className="muted-text">El proveedor aún no registra compras en el rango seleccionado.</p>
          ) : null}

          {!vendorHistoryLoading && vendorHistory && vendorHistory.compras.length > 0 ? (
            <div className="table-responsive">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Fecha</th>
                    <th>Total</th>
                    <th>Impuestos</th>
                    <th>Usuario</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {vendorHistory.compras.map((purchase) => (
                    <tr key={purchase.id_compra}>
                      <td>#{purchase.id_compra}</td>
                      <td>{new Date(purchase.fecha).toLocaleString("es-MX")}</td>
                      <td>{currencyFormatter.format(purchase.total)}</td>
                      <td>{currencyFormatter.format(purchase.impuesto)}</td>
                      <td>{purchase.usuario_nombre || "—"}</td>
                      <td>{purchase.estado}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          {!vendorHistoryLoading && vendorHistory ? (
            <p className="muted-text">
              Total en el rango: {currencyFormatter.format(vendorHistory.total)} · Impuestos: {" "}
              {currencyFormatter.format(vendorHistory.impuesto)} · Registros analizados: {vendorHistory.registros}
            </p>
          ) : null}
        </div>
      </section>

      <section className="card">
        <h2>Estadísticas de compras</h2>
        <p className="card-subtitle">Visualiza los totales mensuales y los proveedores con mayor participación.</p>
        {statsLoading ? <p className="muted-text">Calculando estadísticas…</p> : null}
        {!statsLoading && statistics ? (
          <div className="stats-grid">
            <div className="metric-card">
              <h3>Total invertido</h3>
              <p className="metric-primary">{currencyFormatter.format(statistics.total)}</p>
              <p className="metric-secondary">Impuestos: {currencyFormatter.format(statistics.impuesto)}</p>
            </div>
            <div className="metric-card">
              <h3>Órdenes registradas</h3>
              <p className="metric-primary">{statistics.compras_registradas}</p>
            </div>
            <div className="metric-card">
              <h3>Proveedores frecuentes</h3>
              <ul className="compact-list">
                {statistics.top_vendors.length === 0 ? (
                  <li className="muted-text">Sin datos disponibles</li>
                ) : (
                  statistics.top_vendors.map((item) => (
                    <li key={item.vendor_id}>
                      {item.vendor_name} · {currencyFormatter.format(item.total)} ({item.orders} órdenes)
                    </li>
                  ))
                )}
              </ul>
            </div>
            <div className="metric-card">
              <h3>Usuarios con más compras</h3>
              <ul className="compact-list">
                {statistics.top_users.length === 0 ? (
                  <li className="muted-text">Sin datos disponibles</li>
                ) : (
                  statistics.top_users.map((item) => (
                    <li key={item.user_id}>
                      {(item.user_name || `Usuario #${item.user_id}`) + " · "}
                      {currencyFormatter.format(item.total)} ({item.orders} órdenes)
                    </li>
                  ))
                )}
              </ul>
            </div>
            <div className="metric-card form-span">
              <h3>Totales mensuales</h3>
              <ul className="compact-list">
                {statistics.monthly_totals.length === 0 ? (
                  <li className="muted-text">Sin registros recientes</li>
                ) : (
                  statistics.monthly_totals.map((point) => (
                    <li key={point.label}>
                      {point.label}: {currencyFormatter.format(point.value)}
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>
        ) : null}
        {!statsLoading && !statistics ? <p className="muted-text">Sin métricas disponibles.</p> : null}
      </section>

      <section className="card">
        <h2>Órdenes de compra</h2>
        <p className="card-subtitle">
          Captura nuevas órdenes, recibe productos parciales y conserva un historial auditado de compras.
        </p>
        <form className="form-grid" onSubmit={handleCreate}>
          <label>
            Sucursal
            <select
              value={form.storeId ?? ""}
              onChange={(event) => updateForm({ storeId: event.target.value ? Number(event.target.value) : null })}
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
            Proveedor
            <input
              value={form.supplier}
              onChange={(event) => updateForm({ supplier: event.target.value })}
              placeholder="Proveedor corporativo"
            />
          </label>
          <label>
            Dispositivo
            <select
              value={form.deviceId ?? ""}
              onChange={(event) => updateForm({ deviceId: event.target.value ? Number(event.target.value) : null })}
              disabled={!selectedStore}
            >
              <option value="">Selecciona un dispositivo</option>
              {devices.map((device) => (
                <option key={device.id} value={device.id}>
                  {device.sku} · {device.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Cantidad ordenada
            <input
              type="number"
              min={1}
              value={form.quantity}
              onChange={(event) => updateForm({ quantity: Number(event.target.value) })}
            />
          </label>
          <label>
            Costo unitario MXN
            <input
              type="number"
              min={0}
              step="0.01"
              value={form.unitCost}
              onChange={(event) => updateForm({ unitCost: Number(event.target.value) })}
            />
          </label>
          <button type="submit" className="btn btn--primary">
            Registrar orden
          </button>
        </form>

        <div className="section-divider">
          <h3>Plantillas recurrentes y carga masiva</h3>
          <div className="section-grid">
            <form className="form-grid" onSubmit={handleImportCsv}>
              <label className="form-span">
                Archivo CSV
                <input type="file" name="csvFile" accept=".csv" required />
              </label>
              <button type="submit" className="btn btn--secondary" disabled={csvLoading}>
                {csvLoading ? "Importando…" : "Importar CSV"}
              </button>
              <p className="muted-text form-span">
                Columnas esperadas: <code>store_id,supplier,device_id,quantity,unit_cost[,reference][,notes]</code>
              </p>
            </form>

            <form className="form-grid" onSubmit={handleSaveTemplate}>
              <label>
                Nombre de la plantilla
                <input
                  type="text"
                  value={templateName}
                  onChange={(event) => setTemplateName(event.target.value)}
                  minLength={3}
                  required
                />
              </label>
              <label>
                Descripción
                <input
                  type="text"
                  value={templateDescription}
                  onChange={(event) => setTemplateDescription(event.target.value)}
                  placeholder="Opcional"
                />
              </label>
              <button type="submit" className="btn btn--secondary" disabled={templateSaving}>
                {templateSaving ? "Guardando…" : "Guardar como plantilla"}
              </button>
              <p className="muted-text form-span">
                Se utilizarán los datos actuales del formulario para generar la plantilla recurrente.
              </p>
            </form>
          </div>

          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Proveedor base</th>
                  <th>Último uso</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {recurringLoading ? (
                  <tr>
                    <td colSpan={4} className="muted-text">
                      Cargando plantillas…
                    </td>
                  </tr>
                ) : recurringOrders.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="muted-text">
                      Aún no hay plantillas registradas para compras.
                    </td>
                  </tr>
                ) : (
                  recurringOrders.map((template) => (
                    <tr key={template.id}>
                      <td>{template.name}</td>
                      <td>{getTemplateSupplier(template)}</td>
                      <td>
                        {template.last_used_at
                          ? new Date(template.last_used_at).toLocaleString("es-MX")
                          : "Nunca"}
                      </td>
                      <td>
                        <div className="transfer-actions">
                          <button
                            type="button"
                            className="btn btn--ghost"
                            onClick={() => handleApplyTemplate(template)}
                          >
                            Usar datos
                          </button>
                          <button
                            type="button"
                            className="btn btn--primary"
                            onClick={() => handleExecuteTemplate(template)}
                          >
                            Ejecutar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="section-divider">
          <h3>Historial reciente</h3>
          {loading ? <p className="muted-text">Cargando órdenes…</p> : null}
          {orders.length === 0 && !loading ? (
            <p className="muted-text">No hay órdenes registradas para la sucursal seleccionada.</p>
          ) : null}
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Proveedor</th>
                  <th>Estado</th>
                  <th>Creación</th>
                  <th>Artículos</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id}>
                    <td>#{order.id}</td>
                    <td>{order.supplier}</td>
                    <td>
                      <span className={`badge ${order.status === "COMPLETADA" ? "success" : "neutral"}`}>
                        {statusLabels[order.status]}
                      </span>
                    </td>
                    <td>{new Date(order.created_at).toLocaleString("es-MX")}</td>
                    <td>
                      <ul className="compact-list">
                        {order.items.map((item) => (
                          <li key={item.id}>
                            Dispositivo #{item.device_id} · {item.quantity_received}/{item.quantity_ordered} unidades
                          </li>
                        ))}
                      </ul>
                    </td>
                    <td>
                      <div className="transfer-actions">
                        <button type="button" className="btn btn--ghost" onClick={() => handleReceive(order)}>
                          Recibir pendientes
                        </button>
                        <button type="button" className="btn btn--ghost" onClick={() => handleReturn(order)}>
                          Registrar devolución
                        </button>
                        <button type="button" className="btn btn--ghost" onClick={() => handleCancel(order)}>
                          Cancelar orden
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </>
  );
}

export default Purchases;
