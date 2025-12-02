import { useState, useCallback, useRef } from "react";
import type { DeviceImportSummary, DeviceListFilters } from "@api/inventory";
import type { Store } from "@api/types";
import { promptCorporateReason } from "../../../../utils/corporateReason";

type DownloadFn = (reason: string) => Promise<void>;
type ExportCatalogFn = (filters: DeviceListFilters, reason: string) => Promise<void>;
type ImportCatalogFn = (file: File, reason: string) => Promise<{ resultado?: { nuevos: number; actualizados: number } | null }>;

interface UseInventoryDownloadsProps {
  selectedStore: Store | null;
  selectedStoreId: number | null;
  inventoryQuery: string;
  estadoFilter: string | null | undefined;
  pushToast: (options: { message: string; variant: "success" | "error" | "info" }) => void;
  setError: (message: string | null) => void;
  downloadInventoryReport: DownloadFn;
  downloadInventoryCsv: DownloadFn;
  exportCatalogCsv: ExportCatalogFn;
  importCatalogCsv: ImportCatalogFn;
}

export function useInventoryDownloads({
  selectedStore,
  selectedStoreId,
  inventoryQuery,
  estadoFilter,
  pushToast,
  setError,
  downloadInventoryReport,
  downloadInventoryCsv,
  exportCatalogCsv,
  importCatalogCsv,
}: UseInventoryDownloadsProps) {
  const [exportingCatalog, setExportingCatalog] = useState(false);
  const [importingCatalog, setImportingCatalog] = useState(false);
  const [catalogFile, setCatalogFile] = useState<File | null>(null);
  const [lastImportSummary, setLastImportSummary] = useState<DeviceImportSummary | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const requestSnapshotDownload = useCallback(
    async (downloader: DownloadFn, successMessage: string) => {
      const defaultReason = selectedStore
        ? `Descarga inventario ${selectedStore.name}`
        : "Descarga inventario corporativo";
      const reason = promptCorporateReason(defaultReason);
      if (reason === null) {
        pushToast({
          message: "Acción cancelada: se requiere motivo corporativo.",
          variant: "info",
        });
        return;
      }
      if (reason.length < 5) {
        const message = "El motivo corporativo debe tener al menos 5 caracteres.";
        setError(message);
        pushToast({ message, variant: "error" });
        return;
      }
      try {
        await downloader(reason);
        pushToast({ message: successMessage, variant: "success" });
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible descargar el reporte de inventario.";
        setError(message);
        pushToast({ message, variant: "error" });
      }
    },
    [pushToast, selectedStore, setError]
  );

  const handleDownloadReportClick = useCallback(async () => {
    await requestSnapshotDownload(downloadInventoryReport, "PDF de inventario descargado");
  }, [downloadInventoryReport, requestSnapshotDownload]);

  const handleDownloadCsvClick = useCallback(async () => {
    await requestSnapshotDownload(downloadInventoryCsv, "CSV de inventario descargado");
  }, [downloadInventoryCsv, requestSnapshotDownload]);

  const handleExportCatalogClick = useCallback(async () => {
    if (!selectedStoreId) {
      const message = "Selecciona una sucursal para exportar el catálogo.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    setExportingCatalog(true);
    try {
      const deviceFilters: DeviceListFilters = {};
      const normalizedQuery = inventoryQuery.trim();
      if (normalizedQuery) {
        deviceFilters.search = normalizedQuery;
      }
      if (estadoFilter !== "TODOS") {
        deviceFilters.estado = estadoFilter as DeviceListFilters["estado"];
      }

      // We need to wrap the export function to match the signature expected by requestSnapshotDownload
      // But requestSnapshotDownload expects (reason) => Promise<void>
      // So we create a closure
      const downloader = (reason: string) => exportCatalogCsv(deviceFilters, reason);

      await requestSnapshotDownload(
        downloader,
        "Catálogo CSV exportado"
      );
    } finally {
      setExportingCatalog(false);
    }
  }, [
    estadoFilter,
    exportCatalogCsv,
    inventoryQuery,
    pushToast,
    requestSnapshotDownload,
    selectedStoreId,
    setError,
  ]);

  const handleImportCatalogSubmit = useCallback(async () => {
    if (!catalogFile) {
      const message = "Selecciona un archivo CSV antes de importar.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    const defaultReason = selectedStore
      ? `Importar catálogo ${selectedStore.name}`
      : "Importar catálogo corporativo";
    const reason = promptCorporateReason(defaultReason);
    if (reason === null) {
      pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
      return;
    }
    const normalizedReason = reason.trim();
    if (normalizedReason.length < 5) {
      const message = "Ingresa un motivo corporativo de al menos 5 caracteres.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    setImportingCatalog(true);
    try {
      const summary = await importCatalogCsv(catalogFile, normalizedReason);
      const mappedSummary: DeviceImportSummary = {
        created: summary.resultado?.nuevos ?? 0,
        updated: summary.resultado?.actualizados ?? 0,
        skipped: 0,
        errors: [],
      };
      setLastImportSummary(mappedSummary);
      pushToast({
        message: `Catálogo actualizado: ${mappedSummary.created} nuevos, ${mappedSummary.updated} modificados`,
        variant: "success",
      });
      setCatalogFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible importar el catálogo corporativo.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setImportingCatalog(false);
    }
  }, [catalogFile, importCatalogCsv, pushToast, selectedStore, setError]);

  return {
    exportingCatalog,
    importingCatalog,
    catalogFile,
    setCatalogFile,
    lastImportSummary,
    fileInputRef,
    handleDownloadReportClick,
    handleDownloadCsvClick,
    handleExportCatalogClick,
    handleImportCatalogSubmit,
  };
}
