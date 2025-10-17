import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { motion } from "framer-motion";
import { useLocation } from "react-router-dom";
import {
  AlertTriangle,
  BarChart3,
  Boxes,
  Building2,
  Cog,
  DollarSign,
  FileSpreadsheet,
  RefreshCcw,
  Search,
  ShieldCheck,
  Smartphone,
  type LucideIcon,
} from "lucide-react";

import AdvancedSearch from "../components/AdvancedSearch";
import DeviceEditDialog from "../components/DeviceEditDialog";
import InventoryReportsPanel from "../components/InventoryReportsPanel";
import InventoryTable from "../components/InventoryTable";
import MovementForm from "../components/MovementForm";
import ModuleHeader, { type ModuleStatus } from "../../../components/ModuleHeader";
import LoadingOverlay from "../../../components/LoadingOverlay";
import Tabs, { type TabOption } from "../../../components/ui/Tabs/Tabs";
import type {
  Device,
  DeviceImportSummary,
  DeviceListFilters,
  DeviceUpdateInput,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { useInventoryModule } from "../hooks/useInventoryModule";
import { promptCorporateReason } from "../../../utils/corporateReason";

type StatusBadge = {
  tone: "warning" | "success";
  text: string;
};

type StatusCard = {
  id: string;
  icon: LucideIcon;
  title: string;
  value: string;
  caption: string;
  badge?: StatusBadge;
};

type InventoryTabId = "overview" | "movements" | "alerts" | "reports" | "advanced";

type TabContent = TabOption<InventoryTabId> & { content: ReactNode };

const estadoOptions: Device["estado_comercial"][] = ["nuevo", "A", "B", "C"];

const resolveLowStockSeverity = (quantity: number): "critical" | "warning" | "notice" => {
  if (quantity <= 1) {
    return "critical";
  }
  if (quantity <= 3) {
    return "warning";
  }
  return "notice";
};

function InventoryPage() {
  const location = useLocation();
  const { globalSearchTerm, setGlobalSearchTerm, pushToast, setError } = useDashboard();
  const {
    token,
    enableCatalogPro,
    stores,
    selectedStoreId,
    setSelectedStoreId,
    selectedStore,
    devices,
    loading,
    totalDevices,
    totalItems,
    totalValue,
    formatCurrency,
    topStores,
    lowStockDevices,
    handleMovement,
    handleDeviceUpdate,
    backupHistory,
    updateStatus,
    lastInventoryRefresh,
    downloadInventoryReport,
    downloadInventoryCsv,
    exportCatalogCsv,
    importCatalogCsv,
    supplierBatchOverview,
    supplierBatchLoading,
    refreshSupplierBatchOverview,
    lowStockThreshold,
    updateLowStockThreshold,
    refreshSummary,
    storeValuationSnapshot,
    fetchInventoryCurrentReport,
    downloadInventoryCurrentCsv,
    downloadInventoryCurrentPdf,
    downloadInventoryCurrentXlsx,
    fetchInventoryValueReport,
    fetchInventoryMovementsReport,
    fetchTopProductsReport,
    downloadInventoryValueCsv,
    downloadInventoryValuePdf,
    downloadInventoryValueXlsx,
    downloadInventoryMovementsCsv,
    downloadInventoryMovementsPdf,
    downloadInventoryMovementsXlsx,
    downloadTopProductsCsv,
    downloadTopProductsPdf,
    downloadTopProductsXlsx,
  } = useInventoryModule();

  const [inventoryQuery, setInventoryQuery] = useState("");
  const [estadoFilter, setEstadoFilter] = useState<Device["estado_comercial"] | "TODOS">("TODOS");
  const [activeTab, setActiveTab] = useState<InventoryTabId>("overview");
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [thresholdDraft, setThresholdDraft] = useState(lowStockThreshold);
  const [isSavingThreshold, setIsSavingThreshold] = useState(false);
  const [exportingCatalog, setExportingCatalog] = useState(false);
  const [importingCatalog, setImportingCatalog] = useState(false);
  const [catalogFile, setCatalogFile] = useState<File | null>(null);
  const [lastImportSummary, setLastImportSummary] = useState<DeviceImportSummary | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setInventoryQuery("");
    setEstadoFilter("TODOS");
    if (location.pathname.startsWith("/dashboard/inventory")) {
      setGlobalSearchTerm("");
    }
  }, [location.pathname, selectedStoreId, setGlobalSearchTerm]);

  useEffect(() => {
    if (location.pathname.startsWith("/dashboard/inventory")) {
      setInventoryQuery(globalSearchTerm);
    }
  }, [globalSearchTerm, location.pathname]);

  useEffect(() => {
    setThresholdDraft(lowStockThreshold);
  }, [lowStockThreshold]);

  const lastBackup = backupHistory.at(0) ?? null;
  const lastRefreshDisplay = lastInventoryRefresh
    ? lastInventoryRefresh.toLocaleString("es-MX")
    : "En espera de la primera actualización";

  const filteredDevices = useMemo(() => {
    const normalizedQuery = inventoryQuery.trim().toLowerCase();
    return devices.filter((device) => {
      if (estadoFilter !== "TODOS" && device.estado_comercial !== estadoFilter) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack: Array<string | null | undefined> = [
        device.sku,
        device.name,
        device.imei,
        device.serial,
        device.modelo,
        device.marca,
        device.color,
        device.estado_comercial,
        device.categoria,
        device.condicion,
        device.estado,
        device.ubicacion,
        device.descripcion,
        device.proveedor,
        device.capacidad,
      ];
      return haystack.some((value) => {
        if (!value) {
          return false;
        }
        return value.toLowerCase().includes(normalizedQuery);
      });
    });
  }, [devices, estadoFilter, inventoryQuery]);

  const deviceFilters = useMemo<DeviceListFilters>(() => {
    const filters: DeviceListFilters = {};
    const normalizedQuery = inventoryQuery.trim();
    if (normalizedQuery) {
      filters.search = normalizedQuery;
    }
    if (estadoFilter !== "TODOS") {
      filters.estado = estadoFilter;
    }
    return filters;
  }, [inventoryQuery, estadoFilter]);

  const highlightedDevices = useMemo(
    () => new Set(lowStockDevices.map((entry) => entry.device_id)),
    [lowStockDevices],
  );

  const refreshBadge: StatusBadge = lastInventoryRefresh
    ? { tone: "success", text: "Auto" }
    : { tone: "warning", text: "Sin datos" };

  const closeEditDialog = () => {
    setIsEditDialogOpen(false);
    setEditingDevice(null);
  };

  const requestSnapshotDownload = async (
    downloader: (reason: string) => Promise<void>,
    successMessage: string,
  ) => {
    const defaultReason = selectedStore
      ? `Descarga inventario ${selectedStore.name}`
      : "Descarga inventario corporativo";
    const reason = promptCorporateReason(defaultReason);
    if (reason === null) {
      pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
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
  };

  const handleDownloadReportClick = async () => {
    await requestSnapshotDownload(downloadInventoryReport, "PDF de inventario descargado");
  };

  const handleDownloadCsvClick = async () => {
    await requestSnapshotDownload(downloadInventoryCsv, "CSV de inventario descargado");
  };

  const handleExportCatalogClick = async () => {
    if (!selectedStoreId) {
      const message = "Selecciona una sucursal para exportar el catálogo.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    setExportingCatalog(true);
    try {
      await requestSnapshotDownload(
        (reason) => exportCatalogCsv(deviceFilters, reason),
        "Catálogo CSV exportado",
      );
    } finally {
      setExportingCatalog(false);
    }
  };

  const handleImportCatalogSubmit = async () => {
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
      setLastImportSummary(summary);
      pushToast({
        message: `Catálogo actualizado: ${summary.created} nuevos, ${summary.updated} modificados`,
        variant: "success",
      });
      setCatalogFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible importar el catálogo corporativo.";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setImportingCatalog(false);
    }
  };

  const updateThresholdDraftValue = (value: number) => {
    if (Number.isNaN(value)) {
      return;
    }
    const clamped = Math.max(0, Math.min(100, value));
    setThresholdDraft(clamped);
  };

  const handleSaveThreshold = async () => {
    if (!selectedStoreId) {
      const message = "Selecciona una sucursal para ajustar el umbral de alertas.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    setIsSavingThreshold(true);
    try {
      await updateLowStockThreshold(selectedStoreId, thresholdDraft);
      pushToast({ message: "Umbral de stock bajo actualizado", variant: "success" });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible guardar el nuevo umbral.";
      setError(message);
      pushToast({ message, variant: "error" });
      setThresholdDraft(lowStockThreshold);
    } finally {
      setIsSavingThreshold(false);
    }
  };

  const handleSubmitDeviceUpdates = async (updates: DeviceUpdateInput, reason: string) => {
    if (!editingDevice) {
      return;
    }
    try {
      await handleDeviceUpdate(editingDevice.id, updates, reason);
      closeEditDialog();
    } catch (error) {
      // La notificación de error ya se gestiona desde el contexto.
    }
  };

  const lowStockStats = useMemo(() => {
    let critical = 0;
    let warning = 0;
    for (const entry of lowStockDevices) {
      const severity = resolveLowStockSeverity(entry.quantity);
      if (severity === "critical") {
        critical += 1;
      } else if (severity === "warning") {
        warning += 1;
      }
    }
    return { critical, warning };
  }, [lowStockDevices]);

  let moduleStatus: ModuleStatus = "ok";
  let moduleStatusLabel = "Inventario estable";

  if (loading) {
    moduleStatus = "warning";
    moduleStatusLabel = "Actualizando inventario";
  } else if (lowStockStats.critical > 0) {
    moduleStatus = "critical";
    moduleStatusLabel = `${lowStockStats.critical} dispositivos en nivel crítico`;
  } else if (lowStockStats.warning > 0) {
    moduleStatus = "warning";
    moduleStatusLabel = `${lowStockStats.warning} dispositivos con stock bajo`;
  }

  const statusCards: StatusCard[] = [
    {
      id: "stores",
      icon: Building2,
      title: "Sucursales",
      value: `${stores.length}`,
      caption: "Configuradas",
    },
    {
      id: "devices",
      icon: Smartphone,
      title: "Dispositivos",
      value: `${totalDevices}`,
      caption: "Catalogados",
    },
    {
      id: "units",
      icon: Boxes,
      title: "Unidades",
      value: `${totalItems}`,
      caption: "En stock",
    },
    {
      id: "value",
      icon: DollarSign,
      title: "Valor total",
      value: formatCurrency(totalValue),
      caption: "Inventario consolidado",
    },
    {
      id: "backup",
      icon: ShieldCheck,
      title: "Último respaldo",
      value: lastBackup
        ? new Date(lastBackup.executed_at).toLocaleString("es-MX")
        : "Aún no se generan respaldos",
      caption: lastBackup ? lastBackup.mode : "Programado cada 12 h",
    },
    {
      id: "version",
      icon: Cog,
      title: "Versión",
      value: updateStatus?.current_version ?? "Desconocida",
      caption: updateStatus?.latest_version
        ? `Última publicada: ${updateStatus.latest_version}`
        : "Historial actualizado",
      badge: updateStatus?.is_update_available
        ? { tone: "warning", text: `Actualizar a ${updateStatus.latest_version}` }
        : { tone: "success", text: "Sistema al día" },
    },
    {
      id: "refresh",
      icon: RefreshCcw,
      title: "Actualización en vivo",
      value: lastInventoryRefresh
        ? lastInventoryRefresh.toLocaleTimeString("es-MX")
        : "Sincronizando…",
      caption: lastRefreshDisplay,
      badge: refreshBadge,
    },
  ];

  const overviewContent: ReactNode = (
    <div className="section-grid">
      <section className="card wide">
        <header className="card-header">
          <div>
            <h2>Salud de inventario</h2>
            <p className="card-subtitle">Indicadores clave de todas las tiendas.</p>
          </div>
          {loading ? <span className="pill neutral">Cargando datos…</span> : null}
        </header>
        <div className="status-grid">
          {statusCards.map((cardInfo) => {
            const Icon = cardInfo.icon;
            return (
              <motion.article
                key={cardInfo.id}
                className="status-card"
                whileHover={{ y: -6, scale: 1.01 }}
                transition={{ type: "spring", stiffness: 260, damping: 20 }}
              >
                <span className="status-card-icon" aria-hidden>
                  <Icon size={26} strokeWidth={1.6} />
                </span>
                <div className="status-card-body">
                  <h3>{cardInfo.title}</h3>
                  <p className="status-value">{cardInfo.value}</p>
                  <span className="status-caption">{cardInfo.caption}</span>
                </div>
                {cardInfo.badge ? (
                  <span className={`badge ${cardInfo.badge.tone}`}>{cardInfo.badge.text}</span>
                ) : null}
              </motion.article>
            );
          })}
        </div>
      </section>

      <section className="card">
        <header className="card-header">
          <h2>Seleccionar sucursal</h2>
        </header>
        <select
          value={selectedStoreId ?? ""}
          onChange={(event) => setSelectedStoreId(event.target.value ? Number(event.target.value) : null)}
        >
          {stores.map((store) => (
            <option key={store.id} value={store.id}>
              {store.name}
            </option>
          ))}
        </select>
        {selectedStore ? (
          <p className="muted-text">
            {selectedStore.location ? `${selectedStore.location} · ` : ""}
            Zona horaria: {selectedStore.timezone}
          </p>
        ) : null}
      </section>

      {storeValuationSnapshot ? (
        <section className="card">
          <header className="card-header">
            <div>
              <h2>Conciliación contable</h2>
              <p className="card-subtitle">
                Valor registrado vs. calculado en {storeValuationSnapshot.storeName}.
              </p>
            </div>
            <span
              className={`pill ${
                storeValuationSnapshot.hasRelevantDifference ? "warning" : "success"
              }`}
            >
              {storeValuationSnapshot.hasRelevantDifference
                ? "Revisión requerida"
                : "Sin diferencias"}
            </span>
          </header>
          <ul className="metrics-list">
            <li>
              <strong>Valor contable registrado</strong>
              <span>{formatCurrency(storeValuationSnapshot.registeredValue)}</span>
            </li>
            <li>
              <strong>Valor operativo calculado</strong>
              <span>{formatCurrency(storeValuationSnapshot.calculatedValue)}</span>
            </li>
            <li>
              <strong>Diferencia neta</strong>
              <span>{formatCurrency(storeValuationSnapshot.difference)}</span>
            </li>
            {storeValuationSnapshot.differencePercent !== null ? (
              <li>
                <strong>Variación porcentual</strong>
                <span>{`${Math.abs(storeValuationSnapshot.differencePercent).toFixed(2)} %`}</span>
              </li>
            ) : null}
          </ul>
          <p className="muted-text">
            {storeValuationSnapshot.hasRelevantDifference
              ? `El valor calculado es ${
                  storeValuationSnapshot.difference > 0 ? "mayor" : "menor"
                } que el contable por ${formatCurrency(
                  Math.abs(storeValuationSnapshot.difference),
                )}. Revisa la bitácora corporativa antes de cerrar el periodo.`
              : "Los valores coinciden con el registro contable corporativo."}
          </p>
        </section>
      ) : null}

      <section className="card">
        <h2>Top sucursales por valor</h2>
        {topStores.length === 0 ? (
          <p className="muted-text">No hay datos suficientes para calcular el ranking.</p>
        ) : (
          <ul className="metrics-list">
            {topStores.map((storeMetric) => (
              <li key={storeMetric.store_id}>
                <strong>{storeMetric.store_name}</strong> · {storeMetric.device_count} dispositivos · {storeMetric.total_units}
                unidades ·<span> {formatCurrency(storeMetric.total_value)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card wide">
        <header className="card-header">
          <div>
            <h2>Lotes recientes por proveedor</h2>
            <p className="card-subtitle">
              Seguimiento de compras asociadas a {selectedStore ? selectedStore.name : "cada sucursal"}.
            </p>
          </div>
          <div className="card-actions">
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => {
                void refreshSupplierBatchOverview();
              }}
              disabled={supplierBatchLoading}
            >
              {supplierBatchLoading ? "Actualizando…" : "Actualizar"}
            </button>
          </div>
        </header>
        {supplierBatchLoading ? (
          <p className="muted-text">Cargando lotes recientes…</p>
        ) : supplierBatchOverview.length === 0 ? (
          <p className="muted-text">
            {selectedStore
              ? "Aún no se registran lotes para esta sucursal."
              : "Selecciona una sucursal para consultar sus lotes recientes."}
          </p>
        ) : (
          <ul className="metrics-list">
            {supplierBatchOverview.map((item) => (
              <li key={item.supplier_id}>
                <strong>{item.supplier_name}</strong> · {item.batch_count} lote
                {item.batch_count === 1 ? "" : "s"}
                <div>
                  {item.total_quantity} unidades · {formatCurrency(item.total_value)}
                </div>
                <div className="muted-text">
                  Último lote {item.latest_batch_code ?? "N/D"} —
                  {" "}
                  {new Date(item.latest_purchase_date).toLocaleDateString("es-MX")}
                  {item.latest_unit_cost != null ? (
                    <span>
                      {" "}· Costo unitario reciente: {formatCurrency(item.latest_unit_cost)}
                    </span>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );

  const movementsContent: ReactNode = (
    <div className="section-grid">
      <section className="card wide">
        <header className="card-header">
          <div>
            <h2>Inventario actual</h2>
            <p className="card-subtitle">Consulta existencias y registra movimientos en la misma vista.</p>
          </div>
          <div className="inventory-meta">
            <span className="muted-text">
              Mostrando {filteredDevices.length} de {devices.length} dispositivos
            </span>
            <span className="inventory-last-update">Última actualización: {lastRefreshDisplay}</span>
          </div>
        </header>
        <div className="inventory-controls">
          <label className="input-with-icon" aria-label="Buscar en inventario">
            <Search size={16} aria-hidden />
            <input
              type="search"
              value={inventoryQuery}
              onChange={(event) => {
                const value = event.target.value;
                setInventoryQuery(value);
                if (location.pathname.startsWith("/dashboard/inventory")) {
                  setGlobalSearchTerm(value);
                }
              }}
              placeholder="Buscar por SKU, categoría o ubicación"
            />
          </label>
          <label className="select-inline">
            <span>Estado comercial</span>
            <select
              value={estadoFilter}
              onChange={(event) =>
                setEstadoFilter(event.target.value as Device["estado_comercial"] | "TODOS")
              }
            >
              <option value="TODOS">Todos</option>
              {estadoOptions.map((estado) => (
                <option key={estado} value={estado}>
                  {estado === "nuevo" ? "Nuevo" : `Grado ${estado}`}
                </option>
              ))}
            </select>
          </label>
        </div>
        <InventoryTable
          devices={filteredDevices}
          highlightedDeviceIds={highlightedDevices}
          emptyMessage={
            inventoryQuery.trim() || estadoFilter !== "TODOS"
              ? "No se encontraron dispositivos con los filtros actuales."
              : undefined
          }
          onEditDevice={(device) => {
            setEditingDevice(device);
            setIsEditDialogOpen(true);
          }}
        />
      </section>

      <section className="card">
        <header className="card-header">
          <div>
            <h2>Registrar movimiento</h2>
            <p className="card-subtitle">Ajustes, entradas y salidas sincronizadas con inventario.</p>
          </div>
          <div className="card-actions">
            <button className="btn btn--primary" type="button" onClick={() => void refreshSummary()}>
              Actualizar métricas
            </button>
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => {
                void handleDownloadReportClick();
              }}
            >
              <FileSpreadsheet aria-hidden size={18} />
              <span>Descargar PDF</span>
            </button>
            <button
              className="btn btn--ghost"
              type="button"
              onClick={() => {
                void handleDownloadCsvClick();
              }}
            >
              <FileSpreadsheet aria-hidden size={18} />
              <span>Descargar CSV</span>
            </button>
          </div>
        </header>
        <MovementForm devices={devices} onSubmit={handleMovement} />
      </section>
    </div>
  );

  const alertsContent: ReactNode = (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Alertas de inventario bajo</h2>
          <p className="card-subtitle">Seguimiento inmediato de piezas críticas.</p>
        </div>
        <span className={`pill ${lowStockDevices.length === 0 ? "success" : "warning"}`}>
          {lowStockDevices.length === 0
            ? "Sin alertas"
            : `${lowStockDevices.length} alerta${lowStockDevices.length === 1 ? "" : "s"}`}
        </span>
      </header>
      <div className="threshold-settings">
        <label htmlFor="low-stock-threshold">
          Umbral por sucursal ({thresholdDraft} unidad{thresholdDraft === 1 ? "" : "es"})
        </label>
        <div className="threshold-inputs">
          <input
            id="low-stock-threshold"
            type="range"
            min={0}
            max={100}
            value={thresholdDraft}
            onChange={(event) => updateThresholdDraftValue(Number(event.target.value))}
            disabled={!selectedStoreId || isSavingThreshold}
          />
          <input
            type="number"
            min={0}
            max={100}
            value={thresholdDraft}
            onChange={(event) => updateThresholdDraftValue(Number(event.target.value))}
            disabled={!selectedStoreId || isSavingThreshold}
          />
          <button
            className="btn btn--secondary"
            type="button"
            onClick={() => {
              void handleSaveThreshold();
            }}
            disabled={
              !selectedStoreId || isSavingThreshold || thresholdDraft === lowStockThreshold
            }
          >
            {isSavingThreshold ? "Guardando…" : "Guardar umbral"}
          </button>
        </div>
      </div>
      {lowStockDevices.length === 0 ? (
        <p className="muted-text">No hay alertas por ahora.</p>
      ) : (
        <ul className="low-stock-list">
          {lowStockDevices.map((device) => {
            const severity = resolveLowStockSeverity(device.quantity);
            return (
              <motion.li
                key={device.device_id}
                className={`low-stock-item ${severity}`}
                whileHover={{ x: 6 }}
                transition={{ type: "spring", stiffness: 300, damping: 24 }}
              >
                <span className="low-stock-icon">
                  <AlertTriangle size={18} />
                </span>
                <div className="low-stock-body">
                  <strong>{device.sku}</strong>
                  <span>
                    {device.name} · {device.store_name}
                  </span>
                </div>
                <div className="low-stock-meta">
                  <span className="low-stock-quantity">{device.quantity} uds</span>
                  <span>{formatCurrency(device.inventory_value)}</span>
                </div>
              </motion.li>
            );
          })}
        </ul>
      )}
    </section>
  );

  const reportsContent: ReactNode = (
    <InventoryReportsPanel
      stores={stores}
      selectedStoreId={selectedStoreId}
      formatCurrency={formatCurrency}
      fetchInventoryCurrentReport={fetchInventoryCurrentReport}
      downloadInventoryCurrentCsv={downloadInventoryCurrentCsv}
      downloadInventoryCurrentPdf={downloadInventoryCurrentPdf}
      downloadInventoryCurrentXlsx={downloadInventoryCurrentXlsx}
      fetchInventoryValueReport={fetchInventoryValueReport}
      fetchInventoryMovementsReport={fetchInventoryMovementsReport}
      fetchTopProductsReport={fetchTopProductsReport}
      requestDownloadWithReason={requestSnapshotDownload}
      downloadInventoryValueCsv={downloadInventoryValueCsv}
      downloadInventoryValuePdf={downloadInventoryValuePdf}
      downloadInventoryValueXlsx={downloadInventoryValueXlsx}
      downloadInventoryMovementsCsv={downloadInventoryMovementsCsv}
      downloadInventoryMovementsPdf={downloadInventoryMovementsPdf}
      downloadInventoryMovementsXlsx={downloadInventoryMovementsXlsx}
      downloadTopProductsCsv={downloadTopProductsCsv}
      downloadTopProductsPdf={downloadTopProductsPdf}
      downloadTopProductsXlsx={downloadTopProductsXlsx}
    />
  );

  const advancedContent: ReactNode = enableCatalogPro ? (
    <div className="section-grid">
      <AdvancedSearch token={token} />
      <section className="card">
        <header className="card-header">
          <div>
            <h2>Herramientas de catálogo</h2>
            <p className="card-subtitle">
              Importa o exporta productos con campos extendidos y mantén el inventario alineado.
            </p>
          </div>
        </header>
        <div className="catalog-tools">
          <div className="catalog-actions">
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => void handleExportCatalogClick()}
              disabled={exportingCatalog}
            >
              {exportingCatalog ? "Exportando…" : "Exportar catálogo CSV"}
            </button>
          </div>
          <div className="catalog-import">
            <label className="file-input">
              <span>Archivo CSV</span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setCatalogFile(file);
                }}
              />
              <small className="muted-text">
                {catalogFile
                  ? `Seleccionado: ${catalogFile.name}`
                  : "Incluye encabezados sku, name, categoria, condicion, estado, costo_compra, precio_venta, ubicacion, fecha_ingreso, descripcion"}
              </small>
            </label>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => void handleImportCatalogSubmit()}
              disabled={importingCatalog || !catalogFile}
            >
              {importingCatalog ? "Importando…" : "Importar catálogo"}
            </button>
          </div>
          {lastImportSummary ? (
            <div className="catalog-summary">
              <p className="muted-text">
                Creados: {lastImportSummary.created} · Actualizados: {lastImportSummary.updated} · Omitidos: {lastImportSummary.skipped}
              </p>
              {lastImportSummary.errors.length > 0 ? (
                <ul className="error-list">
                  {lastImportSummary.errors.slice(0, 5).map((error) => (
                    <li key={`${error.row}-${error.message}`}>
                      Fila {error.row}: {error.message}
                    </li>
                  ))}
                  {lastImportSummary.errors.length > 5 ? (
                    <li className="muted-text">Se omitieron {lastImportSummary.errors.length - 5} errores adicionales.</li>
                  ) : null}
                </ul>
              ) : (
                <p className="muted-text">No se registraron errores en la última importación.</p>
              )}
            </div>
          ) : (
            <p className="muted-text">
              Descarga la plantilla actual para conservar todos los campos: SKU, categoría, condición, estado, costo_compra, precio_venta,
              ubicación, fechas y descripción.
            </p>
          )}
        </div>
      </section>
    </div>
  ) : (
    <section className="card">
      <header className="card-header">
        <h2>Búsqueda avanzada</h2>
      </header>
      <p className="muted-text">
        Activa el flag corporativo <code>SOFTMOBILE_ENABLE_CATALOG_PRO</code> para habilitar el catálogo profesional.
      </p>
    </section>
  );

  const inventoryTabs: TabContent[] = [
    {
      id: "overview",
      label: "Vista general",
      icon: <Boxes size={16} aria-hidden />,
      content: overviewContent,
    },
    {
      id: "movements",
      label: "Movimientos",
      icon: <RefreshCcw size={16} aria-hidden />,
      content: movementsContent,
    },
    {
      id: "alerts",
      label: "Alertas",
      icon: <AlertTriangle size={16} aria-hidden />,
      content: alertsContent,
    },
    {
      id: "reports",
      label: "Reportes",
      icon: <BarChart3 size={16} aria-hidden />,
      content: reportsContent,
    },
    {
      id: "advanced",
      label: "Búsqueda avanzada",
      icon: <Search size={16} aria-hidden />,
      content: advancedContent,
    },
  ];

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<Boxes aria-hidden="true" />}
        title="Inventario corporativo"
        subtitle="Gestión de existencias, auditoría de movimientos y respaldos en tiempo real"
        status={moduleStatus}
        statusLabel={moduleStatusLabel}
      />
      <LoadingOverlay visible={loading} label="Sincronizando inventario..." />
      <Tabs tabs={inventoryTabs} activeTab={activeTab} onTabChange={setActiveTab} />
      <DeviceEditDialog
        device={editingDevice}
        open={isEditDialogOpen}
        onClose={closeEditDialog}
        onSubmit={handleSubmitDeviceUpdates}
      />
    </div>
  );
}

export default InventoryPage;
