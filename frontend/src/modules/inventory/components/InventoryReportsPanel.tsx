import { useEffect, useMemo, useState } from "react";

import { BarChart3, Download, FileSpreadsheet, FileText, RefreshCcw } from "lucide-react";
import { Skeleton } from "@/ui/Skeleton"; // [PACK36-inventory-reports]
import { safeArray, safeNumber } from "@/utils/safeValues"; // [PACK36-inventory-reports]

import type {
  InventoryCurrentFilters,
  InventoryCurrentReport,
  InventoryMovementsFilters,
  InventoryMovementsReport,
  InventoryTopProductsFilters,
  InventoryValueFilters,
  InventoryValueReport,
  Store,
  TopProductsReport,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";

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
  fetchInventoryCurrentReport: (filters: InventoryCurrentFilters) => Promise<InventoryCurrentReport>;
  downloadInventoryCurrentCsv: (
    reason: string,
    filters: InventoryCurrentFilters,
  ) => Promise<void>;
  downloadInventoryCurrentPdf: (
    reason: string,
    filters: InventoryCurrentFilters,
  ) => Promise<void>;
  downloadInventoryCurrentXlsx: (
    reason: string,
    filters: InventoryCurrentFilters,
  ) => Promise<void>;
  fetchInventoryValueReport: (filters: InventoryValueFilters) => Promise<InventoryValueReport>;
  fetchInventoryMovementsReport: (filters: InventoryMovementsFilters) => Promise<InventoryMovementsReport>;
  fetchTopProductsReport: (filters: InventoryTopProductsFilters) => Promise<TopProductsReport>;
  requestDownloadWithReason: (
    downloader: (reason: string) => Promise<void>,
    successMessage: string,
  ) => Promise<void>;
  downloadInventoryValueCsv: (reason: string, filters: InventoryValueFilters) => Promise<void>;
  downloadInventoryValuePdf: (reason: string, filters: InventoryValueFilters) => Promise<void>;
  downloadInventoryValueXlsx: (reason: string, filters: InventoryValueFilters) => Promise<void>;
  downloadInventoryMovementsCsv: (reason: string, filters: InventoryMovementsFilters) => Promise<void>;
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
  const [userSelectedStoreFilter, setUserSelectedStoreFilter] = useState<number | "ALL" | null>(null);
  const storeFilter: number | "ALL" = useMemo(
    () => userSelectedStoreFilter ?? (selectedStoreId ?? "ALL"),
    [userSelectedStoreFilter, selectedStoreId],
  );
  const [{ from: dateFrom, to: dateTo }, setDateRange] = useState(createDefaultDateRange);
  const [loading, setLoading] = useState(false);
  const [currentReport, setCurrentReport] = useState<InventoryCurrentReport | null>(null);
  const [valueReport, setValueReport] = useState<InventoryValueReport | null>(null);
  const [movementsReport, setMovementsReport] = useState<InventoryMovementsReport | null>(null);
  const [topProductsReport, setTopProductsReport] = useState<TopProductsReport | null>(null);

  const filters = useMemo<InventoryCurrentFilters>(() => {
    if (storeFilter === "ALL") {
      return {};
    }
    return { storeIds: [storeFilter] };
  }, [storeFilter]);

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
  const currentTotals = { // [PACK36-inventory-reports]
    total_units: safeNumber(currentReport?.totals?.total_units),
    total_value: safeNumber(currentReport?.totals?.total_value),
    devices: safeNumber(currentReport?.totals?.devices),
  };
  const valueTotals = { // [PACK36-inventory-reports]
    valor_total: safeNumber(valueReport?.totals?.valor_total),
    valor_costo: safeNumber(valueReport?.totals?.valor_costo),
    margen_total: safeNumber(valueReport?.totals?.margen_total),
  };
  const movementSummary = { // [PACK36-inventory-reports]
    total_movimientos: safeNumber(movementsReport?.resumen?.total_movimientos),
    total_unidades: safeNumber(movementsReport?.resumen?.total_unidades),
  };
  const topProductsTotals = { // [PACK36-inventory-reports]
    total_unidades: safeNumber(topProductsReport?.total_unidades),
    total_ingresos: safeNumber(topProductsReport?.total_ingresos),
  };
  const hasTopProducts = topProductsReport !== null && topProductItems.length > 0; // [PACK36-inventory-reports]

  useEffect(() => {
    let active = true;
    // Evitar setState sincrono dentro del efecto: deferimos la señal de carga.
    Promise.resolve().then(() => {
      if (active) setLoading(true);
    });
    void Promise.all([
      fetchInventoryCurrentReport(filters),
      fetchInventoryValueReport(filters),
      fetchInventoryMovementsReport(movementsFilters),
      fetchTopProductsReport(topProductsFilters),
    ])
      .then(([current, value, movements, top]) => {
        if (!active) {
          return;
        }
        setCurrentReport(current);
        setValueReport(value);
        setMovementsReport(movements);
        setTopProductsReport(top);
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
    filters,
    movementsFilters,
    topProductsFilters,
  ]);

  const handleValueDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryValueCsv(reason, filters),
      "CSV de valoración descargado",
    );
  };

  const handleValuePdfDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryValuePdf(reason, filters),
      "PDF de valoración descargado",
    );
  };

  const handleValueExcelDownload = async () => {
    await requestDownloadWithReason(
      (reason) => downloadInventoryValueXlsx(reason, filters),
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
            Visualiza existencias consolidadas, movimientos recientes y los productos con mejor desempeño.
          </p>
        </div>
        <div className="report-filters">
          <label className="form-field">
            <span>Sucursal</span>
            <select
              value={storeFilter === "ALL" ? "ALL" : String(storeFilter)}
              onChange={(event) => {
                const value = event.target.value === "ALL" ? "ALL" : Number.parseInt(event.target.value, 10);
                setUserSelectedStoreFilter(value);
              }}
            >
              <option value="ALL">Todas las sucursales</option>
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
              onChange={(event) => setDateRange((current) => ({ ...current, from: event.target.value }))}
            />
          </label>
          <label className="form-field">
            <span>Hasta</span>
            <input
              type="date"
              value={dateTo}
              min={dateFrom}
              onChange={(event) => setDateRange((current) => ({ ...current, to: event.target.value }))}
            />
          </label>
        </div>
      </header>
      {loading ? (
        <div className="reports-loading" role="status" aria-busy="true">
          <p className="muted-text">
            <RefreshCcw className="spin" size={18} aria-hidden /> Cargando reportes…
          </p>
          <div className="section-grid reports-grid" aria-hidden>
            {Array.from({ length: 4 }).map((_, index) => (
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
              <button type="button" className="btn btn--ghost" onClick={() => void handleCurrentDownload()}>
                <Download size={16} aria-hidden />
                CSV
              </button>
              <button type="button" className="btn btn--ghost" onClick={() => void handleCurrentPdfDownload()}>
                <FileText size={16} aria-hidden />
                PDF
              </button>
              <button type="button" className="btn btn--ghost" onClick={() => void handleCurrentExcelDownload()}>
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
                {currentTotals.total_units.toLocaleString("es-MX")}
                <small>unidades</small>
              </p>
              <p className="muted-text">
                Valor corporativo: {formatCurrency(currentTotals.total_value)} · Dispositivos catalogados: {currentTotals.devices}
              </p>
              <ul className="report-list">
                {currentStores.slice(0, 4).map((store) => {
                  const totalUnits = safeNumber(store?.total_units); // [PACK36-inventory-reports]
                  const totalValue = safeNumber(store?.total_value); // [PACK36-inventory-reports]
                  return (
                    <li key={store.store_id}>
                      <strong>{store.store_name}</strong>
                      <span>
                        {totalUnits.toLocaleString("es-MX")}
                        <small> unidades</small>
                      </span>
                      <span className="muted-text">{formatCurrency(totalValue)}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : (
            <p className="muted-text">Aún no hay existencias registradas con los filtros seleccionados.</p>
          )}
          </section>

          <section className="card report-card">
            <header className="card-header">
              <div>
                <h3>Valor total del inventario</h3>
                <p className="card-subtitle">Comparativo entre costo registrado y margen proyectado.</p>
              </div>
              <div className="report-actions">
                <button type="button" className="btn btn--ghost" onClick={() => void handleValueDownload()}>
                  <Download size={16} aria-hidden />
                  CSV
                </button>
                <button type="button" className="btn btn--ghost" onClick={() => void handleValuePdfDownload()}>
                  <FileText size={16} aria-hidden />
                  PDF
                </button>
                <button type="button" className="btn btn--ghost" onClick={() => void handleValueExcelDownload()}>
                  <FileSpreadsheet size={16} aria-hidden />
                  Excel
                </button>
              </div>
            </header>
            {valueReport ? (
              <div className="card-content">
                <p className="report-highlight">{formatCurrency(valueTotals.valor_total)}</p>
                <p className="muted-text">
                  Costo estimado: {formatCurrency(valueTotals.valor_costo)} · Margen proyectado: {formatCurrency(valueTotals.margen_total)}
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
                <button type="button" className="btn btn--ghost" onClick={() => void handleMovementsDownload()}>
                  <Download size={16} aria-hidden />
                  CSV
                </button>
                <button type="button" className="btn btn--ghost" onClick={() => void handleMovementsPdfDownload()}>
                  <FileText size={16} aria-hidden />
                  PDF
                </button>
                <button type="button" className="btn btn--ghost" onClick={() => void handleMovementsExcelDownload()}>
                  <FileSpreadsheet size={16} aria-hidden />
                  Excel
                </button>
              </div>
            </header>
            {movementsReport ? (
              <div className="card-content">
                <p className="report-highlight">
                  {movementSummary.total_movimientos.toLocaleString("es-MX")}
                  <small>registros</small>
                </p>
                <p className="muted-text">
                  Unidades movilizadas: {movementSummary.total_unidades.toLocaleString("es-MX")}
                </p>
                <ul className="report-list">
                  {movementByType.map((entry) => {
                    const totalQuantity = safeNumber(entry?.total_cantidad); // [PACK36-inventory-reports]
                    const totalValue = safeNumber(entry?.total_valor); // [PACK36-inventory-reports]
                    return (
                      <li key={entry.tipo_movimiento}>
                        <strong>{entry.tipo_movimiento.toUpperCase()}</strong>
                        <span>{totalQuantity.toLocaleString("es-MX")}</span>
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
                <button type="button" className="btn btn--ghost" onClick={() => void handleTopProductsDownload()}>
                  <Download size={16} aria-hidden />
                  CSV
                </button>
                <button type="button" className="btn btn--ghost" onClick={() => void handleTopProductsPdfDownload()}>
                  <FileText size={16} aria-hidden />
                  PDF
                </button>
                <button type="button" className="btn btn--ghost" onClick={() => void handleTopProductsExcelDownload()}>
                  <FileSpreadsheet size={16} aria-hidden />
                  Excel
                </button>
              </div>
            </header>
            {hasTopProducts ? (
              <div className="card-content">
                <p className="report-highlight">
                  {topProductsTotals.total_unidades.toLocaleString("es-MX")}
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
                        <span>{soldUnits.toLocaleString("es-MX")} unidades</span>
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
        </div>
      )}
    </section>
  );
}

export default InventoryReportsPanel;
