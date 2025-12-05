import { useCallback, useEffect, useMemo, useState } from "react";

import {
  AlertTriangle,
  BarChart3,
  Download,
  FileSpreadsheet,
  FileText,
  Filter,
  RefreshCcw,
  TrendingUp,
  Clock,
} from "lucide-react";
import { Skeleton } from "@components/ui/Skeleton"; // [PACK36-inventory-reports]
import { safeArray, safeNumber } from "@/utils/safeValues"; // [PACK36-inventory-reports]
import { FILTER_ALL_VALUE } from "@/config/constants";

import type {
  InventoryCurrentFilters,
  InventoryCurrentReport,
  InventoryMovementsFilters,
  InventoryMovementsReport,
  InventoryTopProductsFilters,
  InventoryValueFilters,
  InventoryValueReport,
  InactiveProductsFilters,
  InactiveProductsReport,
  SyncDiscrepancyLog,
  SyncDiscrepancyFilters,
  SyncDiscrepancyReport,
  TopProductsReport,
} from "@api/inventory";
import type { Store } from "@api/types";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import "./InventoryReportsPanel.css";

// Tipos locales para evitar "any" implícito en mapeos y mantener compatibilidad con respuestas de API.
type CurrentStoreRow = {
  store_id: number;
  store_name: string;
  total_units?: number | null;
  total_value?: number | null;
};

type ValueStoreRow = {
  store_id: number;
  store_name: string;
  valor_total?: number | null;
  margen_total?: number | null;
};

type MovementByTypeRow = {
  tipo_movimiento: string;
  total_cantidad?: number | null;
  total_valor?: number | null;
};

type TopProductItemRow = {
  store_id: number;
  device_id: number;
  nombre: string;
  unidades_vendidas?: number | null;
  store_name: string;
};

type InactiveProductRow = {
  store_id: number;
  store_name: string;
  device_id: number;
  sku: string;
  device_name: string;
  categoria: string;
  quantity: number;
  valor_total_producto: number;
  ultima_venta: string | null;
  ultima_compra: string | null;
  ultimo_movimiento: string | null;
  dias_sin_movimiento: number | null;
  ventas_30_dias: number;
  ventas_90_dias: number;
  rotacion_30_dias: number;
  rotacion_90_dias: number;
  rotacion_total: number;
};

type SyncSeverityFilter = "todas" | SyncDiscrepancyLog["severity"];

const severityLabels: Record<SyncDiscrepancyLog["severity"], string> = {
  alerta: "Alerta",
  critica: "Crítica",
  operativa: "Operativa",
  sin_registros: "Sin registros",
};

const formatDateTime = (value: string | null): string => {
  if (!value) {
    return "Sin registro";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Sin registro";
  }
  return date.toLocaleString("es-HN", {
    dateStyle: "short",
    timeStyle: "short",
  });
};

const formatDateInput = (date: Date): string => date.toISOString().slice(0, 10);

const createDefaultDateRange = () => {
  const today = new Date();
  const start = new Date();
  start.setDate(today.getDate() - 30);
  return {
    from: formatDateInput(start),
    to: formatDateInput(today),
  };
};

type InventoryReportsPanelProps = {
  stores: Store[];
  selectedStoreId: number | null;
  formatCurrency: (value: number) => string;
  fetchInventoryCurrentReport: (
    filters: InventoryCurrentFilters,
  ) => Promise<InventoryCurrentReport>;
  downloadInventoryCurrentCsv: (reason: string, filters: InventoryCurrentFilters) => Promise<void>;
  downloadInventoryCurrentPdf: (reason: string, filters: InventoryCurrentFilters) => Promise<void>;
  downloadInventoryCurrentXlsx: (reason: string, filters: InventoryCurrentFilters) => Promise<void>;
  fetchInventoryValueReport: (filters: InventoryValueFilters) => Promise<InventoryValueReport>;
  fetchInventoryMovementsReport: (
    filters: InventoryMovementsFilters,
  ) => Promise<InventoryMovementsReport>;
  fetchTopProductsReport: (filters: InventoryTopProductsFilters) => Promise<TopProductsReport>;
  fetchInactiveProductsReport: (
    filters: InactiveProductsFilters,
  ) => Promise<InactiveProductsReport>;
  fetchSyncDiscrepancyReport: (filters: SyncDiscrepancyFilters) => Promise<SyncDiscrepancyReport>;
  requestDownloadWithReason: (
    downloader: (reason: string) => Promise<void>,
    successMessage: string,
  ) => Promise<void>;
  downloadInventoryValueCsv: (reason: string, filters: InventoryValueFilters) => Promise<void>;
  downloadInventoryValuePdf: (reason: string, filters: InventoryValueFilters) => Promise<void>;
  downloadInventoryValueXlsx: (reason: string, filters: InventoryValueFilters) => Promise<void>;
  downloadInventoryMovementsCsv: (
    reason: string,
    filters: InventoryMovementsFilters,
  ) => Promise<void>;
  downloadInventoryMovementsPdf: (
    reason: string,
    filters: InventoryMovementsFilters,
  ) => Promise<void>;
  downloadInventoryMovementsXlsx: (
    reason: string,
    filters: InventoryMovementsFilters,
  ) => Promise<void>;
  downloadTopProductsCsv: (reason: string, filters: InventoryTopProductsFilters) => Promise<void>;
  downloadTopProductsPdf: (reason: string, filters: InventoryTopProductsFilters) => Promise<void>;
  downloadTopProductsXlsx: (reason: string, filters: InventoryTopProductsFilters) => Promise<void>;
};

function InventoryReportsPanel({
  stores,
  selectedStoreId,
  formatCurrency,
  fetchInventoryCurrentReport,
  downloadInventoryCurrentCsv,
  downloadInventoryCurrentPdf,
  downloadInventoryCurrentXlsx,
  fetchInventoryValueReport,
  fetchInventoryMovementsReport,
  fetchTopProductsReport,
  fetchInactiveProductsReport,
  fetchSyncDiscrepancyReport,
  requestDownloadWithReason,
  downloadInventoryValueCsv,
  downloadInventoryValuePdf,
  downloadInventoryValueXlsx,
  downloadInventoryMovementsCsv,
  downloadInventoryMovementsPdf,
  downloadInventoryMovementsXlsx,
  downloadTopProductsCsv,
  downloadTopProductsPdf,
  downloadTopProductsXlsx,
}: InventoryReportsPanelProps) {
  const dashboard = useDashboard();
  const normalizedStores = useMemo<Store[]>(() => safeArray(stores) as Store[], [stores]); // [PACK36-inventory-reports]

  // Permite que el usuario seleccione una sucursal, pero sin setState en efectos: se deriva del prop cuando el usuario no ha elegido.
  const [userSelectedStoreFilter, setUserSelectedStoreFilter] = useState<
    number | typeof FILTER_ALL_VALUE | null
  >(null);
  const storeFilter: number | typeof FILTER_ALL_VALUE = useMemo(
    () => userSelectedStoreFilter ?? selectedStoreId ?? FILTER_ALL_VALUE,
    [userSelectedStoreFilter, selectedStoreId],
  );
  const [{ from: dateFrom, to: dateTo }, setDateRange] = useState(createDefaultDateRange);
  const [loading, setLoading] = useState(false);
  const [currentReport, setCurrentReport] = useState<InventoryCurrentReport | null>(null);
  const [valueReport, setValueReport] = useState<InventoryValueReport | null>(null);
  const [movementsReport, setMovementsReport] = useState<InventoryMovementsReport | null>(null);
  const [topProductsReport, setTopProductsReport] = useState<TopProductsReport | null>(null);
  const [inactiveReport, setInactiveReport] = useState<InactiveProductsReport | null>(null);
  const [syncDiscrepancyReport, setSyncDiscrepancyReport] = useState<SyncDiscrepancyReport | null>(
    null,
  );
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [pendingCategory, setPendingCategory] = useState("");
  const [minInactivityDays, setMinInactivityDays] = useState(30);
  const [minSyncDifference, setMinSyncDifference] = useState(5);
  const [selectedSeverity, setSelectedSeverity] = useState<SyncSeverityFilter>("todas");

  const handleAddCategory = useCallback(() => {
    const normalized = pendingCategory.trim();
    if (!normalized) {
      return;
    }
    setSelectedCategories((current) =>
      current.includes(normalized) ? current : [...current, normalized],
    );
    setPendingCategory("");
  }, [pendingCategory]);

  const handleRemoveCategory = useCallback((category: string) => {
    setSelectedCategories((current) => current.filter((item) => item !== category));
  }, []);

  const filters = useMemo<InventoryCurrentFilters>(() => {
    if (storeFilter === FILTER_ALL_VALUE) {
      return {};
    }
    return { storeIds: [storeFilter] };
  }, [storeFilter]);

  const valueFilters = useMemo<InventoryValueFilters>(() => {
    const base: InventoryValueFilters =
      storeFilter === FILTER_ALL_VALUE ? {} : { storeIds: [storeFilter] };
    if (selectedCategories.length > 0) {
      return { ...base, categories: selectedCategories };
    }
    return base;
  }, [selectedCategories, storeFilter]);

  const movementsFilters = useMemo<InventoryMovementsFilters>(
    () => ({
      ...filters,
      dateFrom,
      dateTo,
    }),
    [filters, dateFrom, dateTo],
  );

  const topProductsFilters = useMemo<InventoryTopProductsFilters>(
    () => ({
      ...filters,
      dateFrom,
      dateTo,
      limit: 5,
    }),
    [filters, dateFrom, dateTo],
  );

  const inactiveFilters = useMemo<InactiveProductsFilters>(
    () => ({
      ...valueFilters,
      minDaysWithoutMovement: minInactivityDays,
      limit: 50,
    }),
    [minInactivityDays, valueFilters],
  );

  const syncFilters = useMemo<SyncDiscrepancyFilters>(
    () => ({
      ...(storeFilter !== FILTER_ALL_VALUE ? { storeIds: [storeFilter] } : {}),
      dateFrom,
      dateTo,
      ...(selectedSeverity !== "todas" ? { severity: selectedSeverity } : {}),
      minDifference: minSyncDifference,
      limit: 50,
    }),
    [dateFrom, dateTo, minSyncDifference, selectedSeverity, storeFilter],
  );
  const currentStores = useMemo<CurrentStoreRow[]>( // [PACK36-inventory-reports]
    () => safeArray(currentReport?.stores) as CurrentStoreRow[],
    [currentReport],
  );
  const valueStores = useMemo<ValueStoreRow[]>( // [PACK36-inventory-reports]
    () => safeArray(valueReport?.stores) as ValueStoreRow[],
    [valueReport],
  );
  const movementByType = useMemo<MovementByTypeRow[]>( // [PACK36-inventory-reports]
    () => safeArray(movementsReport?.resumen?.por_tipo) as MovementByTypeRow[],
    [movementsReport],
  );
  const topProductItems = useMemo<TopProductItemRow[]>( // [PACK36-inventory-reports]
    () => safeArray(topProductsReport?.items) as TopProductItemRow[],
    [topProductsReport],
  );
  const currentTotals = {
    // [PACK36-inventory-reports]
    total_units: safeNumber(currentReport?.totals?.total_units),
    total_value: safeNumber(currentReport?.totals?.total_value),
    devices: safeNumber(currentReport?.totals?.devices),
  };
  const valueTotals = {
    // [PACK36-inventory-reports]
    valor_total: safeNumber(valueReport?.totals?.valor_total),
    valor_costo: safeNumber(valueReport?.totals?.valor_costo),
    margen_total: safeNumber(valueReport?.totals?.margen_total),
  };
  const movementSummary = {
    // [PACK36-inventory-reports]
    total_movimientos: safeNumber(movementsReport?.resumen?.total_movimientos),
    total_unidades: safeNumber(movementsReport?.resumen?.total_unidades),
  };
  const topProductsTotals = {
    // [PACK36-inventory-reports]
    total_unidades: safeNumber(topProductsReport?.total_unidades),
    total_ingresos: safeNumber(topProductsReport?.total_ingresos),
  };
  const hasTopProducts = topProductsReport !== null && topProductItems.length > 0; // [PACK36-inventory-reports]
  const inactiveItems = useMemo<InactiveProductRow[]>(
    () => safeArray(inactiveReport?.items) as InactiveProductRow[],
    [inactiveReport],
  );
  const syncItems = useMemo<SyncDiscrepancyLog[]>(
    () => safeArray(syncDiscrepancyReport?.items) as SyncDiscrepancyLog[],
    [syncDiscrepancyReport],
  );
  const inactiveTotals = {
    total_products: safeNumber(inactiveReport?.totals?.total_products),
    total_units: safeNumber(inactiveReport?.totals?.total_units),
    total_value: safeNumber(inactiveReport?.totals?.total_value),
    average_days: inactiveReport?.totals?.average_days_without_movement ?? null,
    max_days: inactiveReport?.totals?.max_days_without_movement ?? null,
  };
  const syncTotals = {
    total_conflicts: safeNumber(syncDiscrepancyReport?.totals?.total_conflicts),
    warnings: safeNumber(syncDiscrepancyReport?.totals?.warnings),
    critical: safeNumber(syncDiscrepancyReport?.totals?.critical),
    max_difference: syncDiscrepancyReport?.totals?.max_difference ?? null,
    affected_skus: safeNumber(syncDiscrepancyReport?.totals?.affected_skus),
  };
  const hasInactiveProducts = inactiveReport !== null && inactiveItems.length > 0;
  const hasSyncConflicts = syncDiscrepancyReport !== null && syncItems.length > 0;

  useEffect(() => {
    let active = true;
    // Evitar setState sincrono dentro del efecto: deferimos la señal de carga.
    Promise.resolve().then(() => {
      if (active) setLoading(true);
    });
    void Promise.all([
      fetchInventoryCurrentReport(filters),
      fetchInventoryValueReport(valueFilters),
      fetchInventoryMovementsReport(movementsFilters),
      fetchTopProductsReport(topProductsFilters),
      fetchInactiveProductsReport(inactiveFilters),
      fetchSyncDiscrepancyReport(syncFilters),
    ])
      .then(([current, value, movements, top, inactive, sync]) => {
        if (!active) {
          return;
        }
        setCurrentReport(current);
        setValueReport(value);
        setMovementsReport(movements);
        setTopProductsReport(top);
        setInactiveReport(inactive);
        setSyncDiscrepancyReport(sync);
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible obtener los reportes de inventario.";
        dashboard.setError(message);
        dashboard.pushToast({ message, variant: "error" });
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [
    dashboard,
    fetchInventoryCurrentReport,
    fetchInventoryValueReport,
    fetchInventoryMovementsReport,
    fetchTopProductsReport,
    fetchInactiveProductsReport,
    fetchSyncDiscrepancyReport,
    filters,
    valueFilters,
    movementsFilters,
    topProductsFilters,
    inactiveFilters,
    syncFilters,
  ]);

  const handleValueDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryValueCsv(reason, valueFilters),
      "CSV de valoración descargado",
    );
  };

  const handleValuePdfDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryValuePdf(reason, valueFilters),
      "PDF de valoración descargado",
    );
  };

  const handleValueExcelDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryValueXlsx(reason, valueFilters),
      "Excel de valoración descargado",
    );
  };

  const handleCurrentDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryCurrentCsv(reason, filters),
      "CSV de existencias descargado",
    );
  };

  const handleCurrentPdfDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryCurrentPdf(reason, filters),
      "PDF de existencias descargado",
    );
  };

  const handleCurrentExcelDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryCurrentXlsx(reason, filters),
      "Excel de existencias descargado",
    );
  };

  const handleMovementsDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryMovementsCsv(reason, movementsFilters),
      "CSV de movimientos descargado",
    );
  };

  const handleMovementsPdfDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryMovementsPdf(reason, movementsFilters),
      "PDF de movimientos descargado",
    );
  };

  const handleMovementsExcelDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryMovementsXlsx(reason, movementsFilters),
      "Excel de movimientos descargado",
    );
  };

  const handleTopProductsDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadTopProductsCsv(reason, topProductsFilters),
      "CSV de productos más vendidos descargado",
    );
  };

  const handleTopProductsPdfDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadTopProductsPdf(reason, topProductsFilters),
      "PDF de productos más vendidos descargado",
    );
  };

  const handleTopProductsExcelDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadTopProductsXlsx(reason, topProductsFilters),
      "Excel de productos más vendidos descargado",
    );
  };

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Reportes y estadísticas</h2>
          <p className="card-subtitle">
            Visualiza existencias consolidadas, movimientos recientes y los productos con mejor
            desempeño.
          </p>
        </div>
        <div className="report-filters">
          <label className="form-field">
            <span>Sucursal</span>
            <select
              value={storeFilter === FILTER_ALL_VALUE ? FILTER_ALL_VALUE : String(storeFilter)}
              onChange={(event) => {
                const value =
                  event.target.value === FILTER_ALL_VALUE
                    ? FILTER_ALL_VALUE
                    : Number.parseInt(event.target.value, 10);
                setUserSelectedStoreFilter(value);
              }}
            >
              <option value={FILTER_ALL_VALUE}>Todas las sucursales</option>
              {normalizedStores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Desde</span>
            <input
              type="date"
              value={dateFrom}
              max={dateTo}
              onChange={(event) =>
                setDateRange((current) => ({ ...current, from: event.target.value }))
              }
            />
          </label>
          <label className="form-field">
            <span>Hasta</span>
            <input
              type="date"
              value={dateTo}
              min={dateFrom}
              onChange={(event) =>
                setDateRange((current) => ({ ...current, to: event.target.value }))
              }
            />
          </label>
          <button
            type="button"
            className="btn btn--ghost"
            aria-pressed={advancedFiltersOpen}
            onClick={() => setAdvancedFiltersOpen((current) => !current)}
          >
            <Filter size={16} aria-hidden />
            {advancedFiltersOpen ? "Ocultar filtros" : "Filtros avanzados"}
          </button>
        </div>
      </header>
      {advancedFiltersOpen ? (
        <div
          className="advanced-report-filters"
          role="region"
          aria-label="Filtros avanzados de reportes"
        >
          <div className="advanced-filter-group">
            <h3>Categorías analizadas</h3>
            <form
              className="advanced-filter-row"
              onSubmit={(event) => {
                event.preventDefault();
                handleAddCategory();
              }}
            >
              <label className="form-field">
                <span>Nueva categoría</span>
                <input
                  type="text"
                  value={pendingCategory}
                  onChange={(event) => setPendingCategory(event.target.value)}
                  placeholder="Ej. Smartphones"
                />
              </label>
              <button type="submit" className="btn btn--ghost">
                <TrendingUp size={16} aria-hidden />
                Agregar
              </button>
            </form>
            {selectedCategories.length > 0 ? (
              <ul className="chip-list">
                {selectedCategories.map((category) => (
                  <li key={category} className="chip-item">
                    <span>{category}</span>
                    <button
                      type="button"
                      className="chip-remove"
                      onClick={() => handleRemoveCategory(category)}
                      aria-label={`Quitar categoría ${category}`}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted-text">Sin categorías adicionales seleccionadas.</p>
            )}
          </div>
          <div className="advanced-filter-group">
            <label className="form-field">
              <span>Días sin movimiento</span>
              <input
                type="number"
                min={0}
                max={365}
                value={minInactivityDays}
                onChange={(event) =>
                  setMinInactivityDays(Math.max(0, Number.parseInt(event.target.value, 10) || 0))
                }
              />
            </label>
            <label className="form-field">
              <span>Severidad</span>
              <select
                value={selectedSeverity}
                onChange={(event) => setSelectedSeverity(event.target.value as SyncSeverityFilter)}
              >
                <option value="todas">Todas</option>
                <option value="alerta">Alertas</option>
                <option value="critica">Críticas</option>
              </select>
            </label>
            <label className="form-field">
              <span>Diferencia mínima</span>
              <input
                type="number"
                min={0}
                value={minSyncDifference}
                onChange={(event) =>
                  setMinSyncDifference(Math.max(0, Number.parseInt(event.target.value, 10) || 0))
                }
              />
            </label>
          </div>
        </div>
      ) : null}
      {loading ? (
        <div className="reports-loading" role="status" aria-busy="true">
          <p className="muted-text">
            <RefreshCcw className="spin" size={18} aria-hidden /> Cargando reportes…
          </p>
          <div className="section-grid reports-grid" aria-hidden>
            {Array.from({ length: 6 }).map((_, index) => (
              <section key={`report-skeleton-${index}`} className="card report-card">
                <header className="card-header">
                  <Skeleton lines={2} />
                </header>
                <div className="card-content">
                  <Skeleton lines={5} />
                </div>
              </section>
            ))}
          </div>
        </div>
      ) : (
        <div className="section-grid reports-grid">
          <section className="card report-card">
            <header className="card-header">
              <div>
                <h3>Existencias actuales</h3>
                <p className="card-subtitle">Resumen por sucursal y total consolidado.</p>
              </div>
              <div className="report-actions">
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleCurrentDownload()}
                >
                  <Download size={16} aria-hidden />
                  CSV
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleCurrentPdfDownload()}
                >
                  <FileText size={16} aria-hidden />
                  PDF
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleCurrentExcelDownload()}
                >
                  <FileSpreadsheet size={16} aria-hidden />
                  Excel
                </button>
                <span className="report-icon" aria-hidden>
                  <BarChart3 size={18} />
                </span>
              </div>
            </header>
            {currentReport ? (
              <div className="card-content">
                <p className="report-highlight">
                  {currentTotals.total_units.toLocaleString("es-HN")}
                  <small>unidades</small>
                </p>
                <p className="muted-text">
                  Valor corporativo: {formatCurrency(currentTotals.total_value)} · Dispositivos
                  catalogados: {currentTotals.devices}
                </p>
                <ul className="report-list">
                  {currentStores.slice(0, 4).map((store) => {
                    const totalUnits = safeNumber(store?.total_units); // [PACK36-inventory-reports]
                    const totalValue = safeNumber(store?.total_value); // [PACK36-inventory-reports]
                    return (
                      <li key={store.store_id}>
                        <strong>{store.store_name}</strong>
                        <span>
                          {totalUnits.toLocaleString("es-HN")}
                          <small> unidades</small>
                        </span>
                        <span className="muted-text">{formatCurrency(totalValue)}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : (
              <p className="muted-text">
                Aún no hay existencias registradas con los filtros seleccionados.
              </p>
            )}
          </section>

          <section className="card report-card">
            <header className="card-header">
              <div>
                <h3>Valor total del inventario</h3>
                <p className="card-subtitle">
                  Comparativo entre costo registrado y margen proyectado.
                </p>
              </div>
              <div className="report-actions">
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleValueDownload()}
                >
                  <Download size={16} aria-hidden />
                  CSV
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleValuePdfDownload()}
                >
                  <FileText size={16} aria-hidden />
                  PDF
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleValueExcelDownload()}
                >
                  <FileSpreadsheet size={16} aria-hidden />
                  Excel
                </button>
              </div>
            </header>
            {valueReport ? (
              <div className="card-content">
                <p className="report-highlight">{formatCurrency(valueTotals.valor_total)}</p>
                <p className="muted-text">
                  Costo estimado: {formatCurrency(valueTotals.valor_costo)} · Margen proyectado:{" "}
                  {formatCurrency(valueTotals.margen_total)}
                </p>
                <ul className="report-list">
                  {valueStores.slice(0, 4).map((store) => {
                    const totalValue = safeNumber(store?.valor_total); // [PACK36-inventory-reports]
                    const totalMargin = safeNumber(store?.margen_total); // [PACK36-inventory-reports]
                    return (
                      <li key={store.store_id}>
                        <strong>{store.store_name}</strong>
                        <span>{formatCurrency(totalValue)}</span>
                        <span className="muted-text">Margen: {formatCurrency(totalMargin)}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : (
              <p className="muted-text">No se encontraron datos de valoración.</p>
            )}
          </section>

          <section className="card report-card">
            <header className="card-header">
              <div>
                <h3>Movimientos por periodo</h3>
                <p className="card-subtitle">Entradas, salidas y ajustes filtrados por fechas.</p>
              </div>
              <div className="report-actions">
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleMovementsDownload()}
                >
                  <Download size={16} aria-hidden />
                  CSV
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleMovementsPdfDownload()}
                >
                  <FileText size={16} aria-hidden />
                  PDF
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleMovementsExcelDownload()}
                >
                  <FileSpreadsheet size={16} aria-hidden />
                  Excel
                </button>
              </div>
            </header>
            {movementsReport ? (
              <div className="card-content">
                <p className="report-highlight">
                  {movementSummary.total_movimientos.toLocaleString("es-HN")}
                  <small>registros</small>
                </p>
                <p className="muted-text">
                  Unidades movilizadas: {movementSummary.total_unidades.toLocaleString("es-HN")}
                </p>
                <ul className="report-list">
                  {movementByType.map((entry) => {
                    const totalQuantity = safeNumber(entry?.total_cantidad); // [PACK36-inventory-reports]
                    const totalValue = safeNumber(entry?.total_valor); // [PACK36-inventory-reports]
                    return (
                      <li key={entry.tipo_movimiento}>
                        <strong>{entry.tipo_movimiento.toUpperCase()}</strong>
                        <span>{totalQuantity.toLocaleString("es-HN")}</span>
                        <span className="muted-text">{formatCurrency(totalValue)}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : (
              <p className="muted-text">No hay movimientos registrados en el periodo indicado.</p>
            )}
          </section>

          <section className="card report-card">
            <header className="card-header">
              <div>
                <h3>Productos más vendidos</h3>
                <p className="card-subtitle">Conoce el desempeño de tus dispositivos destacados.</p>
              </div>
              <div className="report-actions">
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleTopProductsDownload()}
                >
                  <Download size={16} aria-hidden />
                  CSV
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleTopProductsPdfDownload()}
                >
                  <FileText size={16} aria-hidden />
                  PDF
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleTopProductsExcelDownload()}
                >
                  <FileSpreadsheet size={16} aria-hidden />
                  Excel
                </button>
              </div>
            </header>
            {hasTopProducts ? (
              <div className="card-content">
                <p className="report-highlight">
                  {topProductsTotals.total_unidades.toLocaleString("es-HN")}
                  <small>unidades</small>
                </p>
                <p className="muted-text">
                  Ingresos estimados: {formatCurrency(topProductsTotals.total_ingresos)}
                </p>
                <ul className="report-list">
                  {topProductItems.slice(0, 5).map((item) => {
                    const soldUnits = safeNumber(item?.unidades_vendidas); // [PACK36-inventory-reports]
                    return (
                      <li key={`${item.store_id}-${item.device_id}`}>
                        <strong>{item.nombre}</strong>
                        <span>{soldUnits.toLocaleString("es-HN")} unidades</span>
                        <span className="muted-text">{item.store_name}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : (
              <p className="muted-text">No se registran ventas en el periodo seleccionado.</p>
            )}
          </section>

          <section className="card report-card">
            <header className="card-header">
              <div>
                <h3>Productos sin movimiento</h3>
                <p className="card-subtitle">
                  Detecta unidades inmovilizadas y su última actividad.
                </p>
              </div>
              <span className="report-icon" aria-hidden>
                <Clock size={18} />
              </span>
            </header>
            {hasInactiveProducts ? (
              <div className="card-content">
                <p className="report-highlight">
                  {inactiveTotals.total_products.toLocaleString("es-HN")}
                  <small>productos</small>
                </p>
                <p className="muted-text">
                  Unidades detenidas: {inactiveTotals.total_units.toLocaleString("es-HN")} · Valor
                  inmovilizado: {formatCurrency(inactiveTotals.total_value)}
                </p>
                {inactiveTotals.average_days !== null ? (
                  <p className="muted-text">
                    Promedio inactivo: {inactiveTotals.average_days.toLocaleString("es-HN")} días
                    {inactiveTotals.max_days !== null
                      ? ` · Máximo: ${inactiveTotals.max_days.toLocaleString("es-HN")} días`
                      : null}
                  </p>
                ) : (
                  <p className="muted-text">Sin historial suficiente para calcular promedios.</p>
                )}
                <ul className="report-list">
                  {inactiveItems.slice(0, 5).map((item) => {
                    const inactivityLabel =
                      item.dias_sin_movimiento !== null
                        ? `${item.dias_sin_movimiento.toLocaleString("es-HN")} días`
                        : "Sin datos";
                    const lastActivity = formatDateTime(
                      item.ultimo_movimiento ?? item.ultima_venta ?? item.ultima_compra,
                    );
                    return (
                      <li key={`${item.store_id}-${item.device_id}`}>
                        <strong>{item.device_name}</strong>
                        <span>{inactivityLabel}</span>
                        <span className="muted-text">
                          {item.store_name} · {lastActivity}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : (
              <p className="muted-text">
                No se detectaron productos inactivos con los filtros seleccionados.
              </p>
            )}
          </section>

          <section className="card report-card">
            <header className="card-header">
              <div>
                <h3>Discrepancias de sincronización</h3>
                <p className="card-subtitle">
                  Conflictos detectados entre sucursales y diferencias de inventario.
                </p>
              </div>
              <span className="report-icon" aria-hidden>
                <AlertTriangle size={18} />
              </span>
            </header>
            {hasSyncConflicts ? (
              <div className="card-content">
                <p className="report-highlight">
                  {syncTotals.total_conflicts.toLocaleString("es-HN")}
                  <small>conflictos</small>
                </p>
                <p className="muted-text">
                  SKUs afectados: {syncTotals.affected_skus.toLocaleString("es-HN")} · Máxima
                  diferencia:{" "}
                  {syncTotals.max_difference !== null
                    ? syncTotals.max_difference.toLocaleString("es-HN")
                    : "s/d"}
                </p>
                <ul className="report-list">
                  {syncItems.slice(0, 5).map((conflict) => {
                    const storeNames = Array.from(
                      new Set(
                        [...conflict.stores_max, ...conflict.stores_min]
                          .map((detail) => detail.store_name)
                          .filter(Boolean),
                      ),
                    );
                    return (
                      <li key={conflict.id}>
                        <strong>{conflict.product_name ?? conflict.sku}</strong>
                        <span>{conflict.difference.toLocaleString("es-HN")} unidades</span>
                        <span className="muted-text">
                          {severityLabels[conflict.severity]} ·{" "}
                          {formatDateTime(conflict.detected_at)}
                        </span>
                        <span className="muted-text">
                          {storeNames.join(" · ") || "Sucursales no identificadas"}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : (
              <p className="muted-text">Sin discrepancias registradas con los filtros actuales.</p>
            )}
          </section>
        </div>
      )}
    </section>
  );
}

export default InventoryReportsPanel;
