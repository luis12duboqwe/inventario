import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  createPurchaseRecord,
  exportPurchaseRecordsExcel,
  exportPurchaseRecordsPdf,
  listPurchaseRecords,
} from "../../../../../api/purchases";
import type {
  PurchaseRecord,
  PurchaseRecordPayload,
} from "../../../../../api/purchases";
import type {
  PurchaseRecordDraftItem,
  PurchaseRecordFilters,
  PurchaseRecordForm,
} from "../../../../../types/purchases";
import type { Device } from "../../../../../api/inventory";
import { getDevices } from "../../../../../api/inventory";

type UsePurchaseRecordsParams = {
  token: string;
  defaultStoreId: number | null;
  askReason: (prompt: string) => string | null;
  setError: (msg: string | null) => void;
  setMessage: (msg: string | null) => void;
  downloadBlob: (blob: Blob, filename: string) => void;
  loadStatistics: () => Promise<void>;
  loadVendors: () => Promise<void>;
};

const recordInitialForm: PurchaseRecordForm = {
  storeId: null,
  vendorId: null,
  paymentMethod: "TRANSFERENCIA",
  status: "REGISTRADA",
  taxRate: 0.16,
  date: new Date().toISOString().slice(0, 10),
};

const createBlankRecordItem = (): PurchaseRecordDraftItem => ({
  tempId: Math.random().toString(36).substring(2) + Date.now().toString(36),
  productId: null,
  quantity: 1,
  unitCost: 0,
});

const recordStatuses = ["REGISTRADA", "PAGADA", "CANCELADA", "DEVUELTA"] as const;
const emptyRecordFilters: PurchaseRecordFilters = {
  vendorId: "",
  userId: "",
  dateFrom: "",
  dateTo: "",
  status: "",
  search: "",
};

export function usePurchaseRecords(params: UsePurchaseRecordsParams) {
  const {
    token,
    defaultStoreId,
    askReason,
    setError,
    setMessage,
    downloadBlob,
    loadStatistics,
    loadVendors,
  } = params;
  const [records, setRecords] = useState<PurchaseRecord[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordForm, setRecordForm] = useState<PurchaseRecordForm>({
    ...recordInitialForm,
    storeId: defaultStoreId ?? null,
  });
  const [recordItems, setRecordItems] = useState<PurchaseRecordDraftItem[]>([
    createBlankRecordItem(),
  ]);
  const [recordDevices, setRecordDevices] = useState<Device[]>([]);
  const [recordFilters, setRecordFilters] = useState({ ...emptyRecordFilters });
  const [recordFiltersDraft, setRecordFiltersDraft] = useState({ ...emptyRecordFilters });

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
  }, [token, recordFilters, setError]);

  useEffect(() => {
    void loadRecords();
  }, [loadRecords]);

  useEffect(() => {
    setRecordForm((current) => ({ ...current, storeId: defaultStoreId ?? null }));
  }, [defaultStoreId]);

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
  }, [recordForm.storeId, token, setError]);

  const handleRecordFiltersDraftChange = <Field extends keyof PurchaseRecordFilters>(
    field: Field,
    value: PurchaseRecordFilters[Field],
  ) => {
    setRecordFiltersDraft((current) => ({ ...current, [field]: value }));
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
    setRecordItems((current) => [...current, createBlankRecordItem()]);
  };

  const removeRecordItem = (index: number) => {
    setRecordItems((current) => {
      if (current.length <= 1) {
        return [createBlankRecordItem()];
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

  const recordStatusOptions = useMemo(() => {
    const baseStatuses = [...recordStatuses];
    if (recordForm.status && !baseStatuses.includes(recordForm.status as (typeof recordStatuses)[number])) {
      baseStatuses.push(recordForm.status as (typeof recordStatuses)[number]);
    }
    return baseStatuses;
  }, [recordForm.status]);

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
      setRecordItems([createBlankRecordItem()]);
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

  return {
    records,
    recordsLoading,
    recordForm,
    recordItems,
    recordDevices,
    recordFiltersDraft,
    recordStatusOptions,
    recordSubtotal,
    recordTax,
    recordTotal,
    handleRecordFiltersDraftChange,
    updateRecordForm,
    updateRecordItem,
    addRecordItem,
    removeRecordItem,
    handleRecordSubmit,
    handleRecordFiltersSubmit,
    handleRecordFiltersReset,
    handleExportRecords,
  };
}
