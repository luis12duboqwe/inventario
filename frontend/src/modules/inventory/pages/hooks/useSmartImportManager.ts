import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type {
  Device,
  InventoryImportHistoryEntry,
  InventorySmartImportPreview,
  InventorySmartImportResponse,
  InventorySmartImportResult,
} from "@api/inventory";
import type { Store } from "@api/types";
import type { ToastMessage } from "../../../dashboard/context/DashboardContext";
import { promptCorporateReason } from "../../../../utils/corporateReason";
import megasupplierTemplateXlsxBase64 from "../../../../assets/importacion/plantilla_megasupplier.xlsx.b64?raw";
import { buildSmartSummaryPdf } from "../../../../utils/pdf";

export type SmartImportManagerDeps = {
  smartImportInventory: (
    file: File,
    reason: string,
    options?: { commit?: boolean; overrides?: Record<string, string> },
  ) => Promise<InventorySmartImportResponse>;
  fetchSmartImportHistory: (limit?: number) => Promise<InventoryImportHistoryEntry[]>;
  fetchIncompleteDevices: (storeId?: number, limit?: number) => Promise<Device[]>;
  refreshSummary: () => Promise<void> | void;
  selectedStore: Store | null;
  selectedStoreId: number | null;
  pushToast: (toast: Omit<ToastMessage, "id">) => void;
  setError: (message: string | null) => void;
};

export type SmartImportVendorTemplate = {
  id: string;
  proveedor: string;
  descripcion: string;
  downloads: Array<{ label: string; url: string }>;
  overrides: Record<string, string>;
};

const SMART_IMPORT_GUIDE_URL = "/docs/importacion/proveedores";

const MEGASUPPLIER_XLSX_DATA_URL = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${megasupplierTemplateXlsxBase64.trim()}`;

const SMART_IMPORT_VENDOR_TEMPLATES: SmartImportVendorTemplate[] = [
  {
    id: "megasupplier",
    proveedor: "MegaSupplier",
    descripcion:
      "Plantilla con margen, garantía, imagen y descripción extendida alineadas al catálogo pro.",
    downloads: [
      { label: "Descargar CSV", url: "/importacion/plantilla_megasupplier.csv" },
      { label: "Descargar XLSX", url: MEGASUPPLIER_XLSX_DATA_URL },
    ],
    overrides: {
      sku: "SKU Proveedor",
      name: "Nombre Catálogo",
      marca: "Marca",
      modelo: "Modelo",
      color: "Color",
      capacidad_gb: "Storage (GB)",
      imei: "IMEI",
      cantidad: "Unidades",
      precio: "Precio Publico",
      costo: "Costo Distribuidor",
      garantia_meses: "Warranty (months)",
      margen_porcentaje: "Margin %",
      imagen_url: "Image URL",
      descripcion: "Descripción extendida",
      proveedor: "Proveedor",
      tienda: "Sucursal",
    },
  },
];

export function useSmartImportManager({
  smartImportInventory,
  fetchSmartImportHistory,
  fetchIncompleteDevices,
  refreshSummary,
  selectedStore,
  selectedStoreId,
  pushToast,
  setError,
}: SmartImportManagerDeps) {
  const [smartImportFile, setSmartImportFile] = useState<File | null>(null);
  const [smartImportPreviewState, setSmartImportPreviewState] =
    useState<InventorySmartImportPreview | null>(null);
  const [smartImportResult, setSmartImportResult] = useState<InventorySmartImportResult | null>(null);
  const [smartImportReason, setSmartImportReason] = useState<string | null>(null);
  const [smartImportOverrides, setSmartImportOverrides] = useState<Record<string, string>>({});
  const [smartImportLoading, setSmartImportLoading] = useState(false);
  const [smartImportHistory, setSmartImportHistory] = useState<InventoryImportHistoryEntry[]>([]);
  const [smartImportHistoryLoading, setSmartImportHistoryLoading] = useState(false);
  const [pendingDevices, setPendingDevices] = useState<Device[]>([]);
  const [pendingDevicesLoading, setPendingDevicesLoading] = useState(false);
  const [smartPreviewDirty, setSmartPreviewDirty] = useState(false);
  const smartFileInputRef = useRef<HTMLInputElement | null>(null);
  const vendorTemplates = useMemo(
    () =>
      SMART_IMPORT_VENDOR_TEMPLATES.map((template) => ({
        ...template,
        downloads: [...template.downloads],
      })),
    [],
  );

  const ensureSmartReason = useCallback((): string | null => {
    const defaultReason = selectedStore
      ? `Importación inteligente ${selectedStore.name}`
      : "Importación inteligente de inventario";
    if (smartImportReason && smartImportReason.length >= 5) {
      return smartImportReason;
    }
    const reason = promptCorporateReason(defaultReason);
    if (reason === null) {
      pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
      return null;
    }
    const normalized = reason.trim();
    if (normalized.length < 5) {
      const message = "Ingresa un motivo corporativo de al menos 5 caracteres.";
      setError(message);
      pushToast({ message, variant: "error" });
      return null;
    }
    setSmartImportReason(normalized);
    return normalized;
  }, [pushToast, selectedStore, setError, smartImportReason]);

  const refreshSmartImportHistory = useCallback(async () => {
    try {
      setSmartImportHistoryLoading(true);
      const history = await fetchSmartImportHistory(10);
      setSmartImportHistory(history);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible obtener el historial de importaciones inteligentes.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setSmartImportHistoryLoading(false);
    }
  }, [fetchSmartImportHistory, pushToast, setError]);

  const refreshPendingDevices = useCallback(async () => {
    try {
      setPendingDevicesLoading(true);
      const devicesResponse = await fetchIncompleteDevices(selectedStoreId ?? undefined, 200);
      setPendingDevices(devicesResponse);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible obtener los dispositivos con información pendiente.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setPendingDevicesLoading(false);
    }
  }, [fetchIncompleteDevices, pushToast, selectedStoreId, setError]);

  useEffect(() => {
    void refreshSmartImportHistory();
  }, [refreshSmartImportHistory]);

  const applyVendorTemplate = useCallback(
    (templateId: string) => {
      const template = vendorTemplates.find((entry) => entry.id === templateId);
      if (!template) {
        pushToast({ message: "Selecciona una plantilla válida.", variant: "error" });
        return;
      }
      setSmartImportOverrides((current) => ({ ...current, ...template.overrides }));
      setSmartPreviewDirty(true);
      pushToast({
        message: `Plantilla ${template.proveedor} aplicada. Reanaliza el archivo para confirmar coincidencias.`,
        variant: "info",
      });
    },
    [pushToast, vendorTemplates],
  );

  const handleSmartOverrideChange = useCallback((field: string, header: string) => {
    setSmartImportOverrides((current) => {
      const next = { ...current };
      if (!header) {
        delete next[field];
      } else {
        next[field] = header;
      }
      return next;
    });
    setSmartPreviewDirty(true);
  }, []);

  const handleSmartPreview = useCallback(async () => {
    if (!smartImportFile) {
      const message = "Selecciona un archivo Excel o CSV antes de analizar.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    const reason = ensureSmartReason();
    if (!reason) {
      return;
    }
    setSmartImportLoading(true);
    try {
      const response = await smartImportInventory(smartImportFile, reason, {
        commit: false,
        overrides: smartImportOverrides,
      });
      setSmartImportPreviewState(response.preview);
      setSmartImportResult(response.resultado ?? null);
      setSmartPreviewDirty(false);
      if (response.preview.advertencias.length > 0) {
        pushToast({ message: "Análisis completado con advertencias.", variant: "warning" });
      } else {
        pushToast({ message: "Análisis completado correctamente.", variant: "success" });
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible analizar el archivo de inventario.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setSmartImportLoading(false);
    }
  }, [
    ensureSmartReason,
    pushToast,
    setError,
    smartImportFile,
    smartImportInventory,
    smartImportOverrides,
  ]);

  const handleSmartCommit = useCallback(async () => {
    if (!smartImportFile) {
      const message = "Selecciona un archivo antes de importar.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    const reason = ensureSmartReason();
    if (!reason) {
      return;
    }
    setSmartImportLoading(true);
    try {
      const response = await smartImportInventory(smartImportFile, reason, {
        commit: true,
        overrides: smartImportOverrides,
      });
      setSmartImportPreviewState(response.preview);
      setSmartImportResult(response.resultado ?? null);
      setSmartPreviewDirty(false);
      setSmartImportFile(null);
      if (smartFileInputRef.current) {
        smartFileInputRef.current.value = "";
      }
      pushToast({ message: "Importación inteligente completada.", variant: "success" });
      await refreshSmartImportHistory();
      await refreshPendingDevices();
      void refreshSummary();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible completar la importación inteligente.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setSmartImportLoading(false);
    }
  }, [
    ensureSmartReason,
    pushToast,
    refreshPendingDevices,
    refreshSmartImportHistory,
    refreshSummary,
    setError,
    smartImportFile,
    smartImportInventory,
    smartImportOverrides,
  ]);

  const smartImportHeaders = useMemo(() => {
    if (!smartImportPreviewState) {
      return [] as string[];
    }
    const headers = new Set<string>();
    smartImportPreviewState.columnas.forEach((match) => {
      if (match.encabezado_origen) {
        headers.add(match.encabezado_origen);
      }
    });
    return Array.from(headers).sort((a, b) => a.localeCompare(b));
  }, [smartImportPreviewState]);

  const resetSmartImportContext = useCallback(() => {
    setSmartImportPreviewState(null);
    setSmartImportResult(null);
    setSmartImportOverrides({});
    setSmartPreviewDirty(false);
  }, []);

  const downloadSmartResultCsv = useCallback(() => {
    if (!smartImportResult) {
      return;
    }
    const result = smartImportResult;
    const lines = [
      "Campo,Valor",
      `Total procesados,${result.total_procesados}`,
      `Nuevos,${result.nuevos}`,
      `Actualizados,${result.actualizados}`,
      `Registros incompletos,${result.registros_incompletos}`,
      `Tiendas nuevas,${result.tiendas_nuevas.join(" | ") || "Ninguna"}`,
    ];
    if (result.columnas_faltantes.length > 0) {
      lines.push(
        `Columnas faltantes,"${result.columnas_faltantes.join(" | ").replace(/"/g, '""')}"`,
      );
    } else {
      lines.push("Columnas faltantes,N/A");
    }
    if (result.advertencias.length > 0) {
      result.advertencias.forEach((warning, index) => {
        lines.push(`Advertencia ${index + 1},"${warning.replace(/"/g, '""')}"`);
      });
    } else {
      lines.push("Advertencias,Ninguna");
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "importacion_inteligente_resumen.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [smartImportResult]);

  const downloadSmartResultPdf = useCallback(() => {
    if (!smartImportResult) {
      return;
    }
    const blob = buildSmartSummaryPdf(smartImportResult.resumen);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "importacion_inteligente_resumen.pdf";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [smartImportResult]);

  return {
    smartImportFile,
    setSmartImportFile,
    smartImportPreviewState,
    smartImportResult,
    smartImportOverrides,
    smartImportHeaders,
    smartImportLoading,
    smartImportHistory,
    smartImportHistoryLoading,
    refreshSmartImportHistory,
    pendingDevices,
    pendingDevicesLoading,
    refreshPendingDevices,
    smartPreviewDirty,
    setSmartPreviewDirty,
    smartFileInputRef,
    handleSmartOverrideChange,
    handleSmartPreview,
    handleSmartCommit,
    resetSmartImportContext,
    vendorTemplates,
    applyVendorTemplate,
    smartImportGuideUrl: SMART_IMPORT_GUIDE_URL,
    downloadSmartResultCsv,
    downloadSmartResultPdf,
  };
}
