import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  createPurchaseVendor,
  exportPurchaseVendorsCsv,
  getPurchaseVendorHistory,
  listPurchaseVendors,
  setPurchaseVendorStatus,
  updatePurchaseVendor,
} from "../../../../../api/purchases";
import type {
  PurchaseVendor,
  PurchaseVendorHistory,
  PurchaseVendorPayload,
} from "../../../../../api/purchases";
import type {
  VendorFilters,
  VendorForm,
  VendorHistoryFilters,
} from "../../../../../types/purchases";

type UsePurchaseVendorsParams = {
  token: string;
  askReason: (prompt: string) => string | null;
  setError: (msg: string | null) => void;
  setMessage: (msg: string | null) => void;
  downloadBlob: (blob: Blob, filename: string) => void;
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

export function usePurchaseVendors(params: UsePurchaseVendorsParams) {
  const { token, askReason, setError, setMessage, downloadBlob } = params;

  const [vendors, setVendors] = useState<PurchaseVendor[]>([]);
  const [vendorsLoading, setVendorsLoading] = useState(false);
  const [vendorForm, setVendorForm] = useState({ ...emptyVendorForm });
  const [editingVendorId, setEditingVendorId] = useState<number | null>(null);
  const [selectedVendorId, setSelectedVendorId] = useState<number | null>(null);
  const [vendorHistory, setVendorHistory] = useState<PurchaseVendorHistory | null>(null);
  const [vendorHistoryLoading, setVendorHistoryLoading] = useState(false);
  const [vendorSaving, setVendorSaving] = useState(false);
  const [vendorExporting, setVendorExporting] = useState(false);
  const [vendorFilters, setVendorFilters] = useState({ ...emptyVendorFilters });
  const [vendorFiltersDraft, setVendorFiltersDraft] = useState({ ...emptyVendorFilters });
  const [vendorHistoryFilters, setVendorHistoryFilters] = useState({
    ...emptyVendorHistoryFilters,
  });
  const [vendorHistoryFiltersDraft, setVendorHistoryFiltersDraft] = useState({
    ...emptyVendorHistoryFilters,
  });

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
  }, [token, vendorFilters.query, vendorFilters.status, setError]);

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
    [token, vendorHistoryFilters, setError],
  );

  useEffect(() => {
    void loadVendors();
  }, [loadVendors]);

  useEffect(() => {
    void loadVendorHistory(selectedVendorId);
  }, [loadVendorHistory, selectedVendorId]);

  const selectedVendor = useMemo(
    () => vendors.find((vendor) => vendor.id_proveedor === selectedVendorId) ?? null,
    [vendors, selectedVendorId],
  );

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

  return {
    vendors,
    vendorsLoading,
    vendorForm,
    editingVendorId,
    selectedVendor,
    vendorHistory,
    vendorHistoryLoading,
    vendorSaving,
    vendorExporting,
    vendorFiltersDraft,
    vendorHistoryFiltersDraft,
    loadVendors,
    handleVendorFormSubmit,
    handleVendorInputChange,
    resetVendorForm,
    handleVendorEdit,
    handleVendorStatusToggle,
    handleVendorExport,
    handleVendorFiltersSubmit,
    handleVendorFiltersReset,
    handleVendorHistoryFiltersSubmit,
    handleVendorHistoryFiltersReset,
    handleSelectVendor,
    handleVendorFiltersDraftChange,
    handleVendorHistoryFiltersDraftChange,
  };
}
