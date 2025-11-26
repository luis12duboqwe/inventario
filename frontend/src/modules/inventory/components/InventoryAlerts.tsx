import { useMemo } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import type {
  InventoryAlertItem,
  InventoryAlertSettings,
  InventoryAlertSummary,
} from "../../../api";
import Button from "../../../shared/components/ui/Button";

type InventoryAlertsProps = {
  items: InventoryAlertItem[];
  summary: InventoryAlertSummary;
  settings: InventoryAlertSettings;
  thresholdDraft: number;
  onThresholdChange: (value: number) => void;
  onSaveThreshold: () => void;
  isSaving: boolean;
  formatCurrency: (value: number) => string;
  isLoading?: boolean;
};

const severityLabels: Record<InventoryAlertItem["severity"], string> = {
  critical: "Crítica",
  warning: "Advertencia",
  notice: "Seguimiento",
};

const pillTone: Record<InventoryAlertItem["severity"], string> = {
  critical: "pill danger",
  warning: "pill warning",
  notice: "pill neutral",
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function InventoryAlerts({
  items,
  summary,
  settings,
  thresholdDraft,
  onThresholdChange,
  onSaveThreshold,
  isSaving,
  formatCurrency,
  isLoading = false,
}: InventoryAlertsProps) {
  const safeMetric = (value: number | null | undefined): number =>
    Number.isFinite(value) ? (value as number) : 0;

  const safeSummary = useMemo(
    () => ({
      total: safeMetric(summary?.total),
      critical: safeMetric(summary?.critical),
      warning: safeMetric(summary?.warning),
      notice: safeMetric(summary?.notice),
    }),
    [summary],
  );

  const minThreshold = settings.minimum_threshold;
  const maxThreshold = settings.maximum_threshold;

  const sortedItems = useMemo(
    () =>
      [...items].sort((a, b) => {
        if (a.severity === b.severity) {
          return a.quantity - b.quantity;
        }
        if (a.severity === "critical") {
          return -1;
        }
        if (b.severity === "critical") {
          return 1;
        }
        if (a.severity === "warning") {
          return -1;
        }
        if (b.severity === "warning") {
          return 1;
        }
        return a.quantity - b.quantity;
      }),
    [items],
  );

  const handleChange = (value: number) => {
    const next = clamp(value, minThreshold, maxThreshold);
    onThresholdChange(next);
  };

  const handleInputChange: React.ChangeEventHandler<HTMLInputElement> = (event) => {
    const parsed = Number(event.target.value);
    if (Number.isNaN(parsed)) {
      return;
    }
    handleChange(parsed);
  };

  return (
    <section className="card inventory-alerts">
      <header className="card-header">
        <div>
          <h2>Alertas de inventario</h2>
          <p className="card-subtitle">
            Configura el umbral corporativo y revisa dispositivos en riesgo por sucursal.
          </p>
        </div>
        <div className="alert-summary" aria-live="polite">
          <span className="pill accent">Total: {safeSummary.total}</span>
          <span className={pillTone.critical}>Críticas: {safeSummary.critical}</span>
          <span className={pillTone.warning}>Advertencias: {safeSummary.warning}</span>
          <span className={pillTone.notice}>Seguimiento: {safeSummary.notice}</span>
        </div>
      </header>

      <div className="threshold-settings">
        <label htmlFor="inventory-threshold">
          Umbral general ({thresholdDraft} unidad{thresholdDraft === 1 ? "" : "es"})
        </label>
        <div className="threshold-inputs">
          <input
            id="inventory-threshold"
            type="range"
            min={minThreshold}
            max={maxThreshold}
            value={thresholdDraft}
            onChange={(event) => handleChange(Number(event.target.value))}
          />
          <input
            type="number"
            min={minThreshold}
            max={maxThreshold}
            value={thresholdDraft}
            onChange={handleInputChange}
          />
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() => {
              onSaveThreshold();
            }}
            disabled={isSaving || isLoading}
          >
            {isSaving ? "Guardando…" : "Guardar umbral"}
          </Button>
        </div>
        <p className="muted-text">
          Crítica ≤ {settings.critical_cutoff} uds · Advertencia ≤ {settings.warning_cutoff} uds ·
          Ajustes manuales ≥ {settings.adjustment_variance_threshold} uds registran auditoría.
        </p>
      </div>

      {isLoading ? (
        <div className="muted-text" role="status" aria-live="polite">
          <Loader2 className="spinner" aria-hidden="true" /> Cargando alertas…
        </div>
      ) : sortedItems.length === 0 ? (
        <p className="muted-text">No hay alertas con el umbral configurado.</p>
      ) : (
        <ul className="low-stock-list" aria-live="polite">
          {sortedItems.map((item) => (
            <li key={item.device_id} className={`low-stock-item ${item.severity}`}>
              <span className="low-stock-icon" aria-hidden="true">
                <AlertTriangle size={18} />
              </span>
              <div className="low-stock-body">
                <strong>{item.sku}</strong>
                <span>
                  {item.name} · {item.store_name}
                </span>
                <span className="muted-text">Severidad: {severityLabels[item.severity]}</span>
                <div className="low-stock-tags" aria-label="Indicadores de reposición">
                  <span className="stock-tag tag-minimum">Mínimo {item.minimum_stock} uds</span>
                  <span className="stock-tag tag-reorder">Reorden {item.reorder_point} uds</span>
                  {item.reorder_gap > 0 ? (
                    <span className="stock-tag tag-gap">Faltan {item.reorder_gap} uds</span>
                  ) : (
                    <span className="stock-tag tag-gap safe">En rango</span>
                  )}
                  {item.projected_days !== null ? (
                    <span
                      className={`stock-tag tag-forecast ${
                        item.projected_days <= 3
                          ? "critical"
                          : item.projected_days <= 7
                            ? "warning"
                            : "notice"
                      }`}
                    >
                      Pronóstico {item.projected_days}d
                    </span>
                  ) : (
                    <span className="stock-tag tag-forecast notice">Sin pronóstico</span>
                  )}
                  {Number.isFinite(item.average_daily_sales) ? (
                    <span className="stock-tag tag-avg">
                      Venta diaria {(item.average_daily_sales as number).toFixed(1)} uds
                    </span>
                  ) : null}
                  {item.insights.map((insight, index) => (
                    <span key={`${item.device_id}-insight-${index}`} className="stock-tag tag-insight">
                      {insight}
                    </span>
                  ))}
                </div>
              </div>
              <div className="low-stock-meta">
                <span className="low-stock-quantity">{item.quantity} uds</span>
                <span>{formatCurrency(item.inventory_value)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default InventoryAlerts;
