import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";

import Button from "../../../../shared/components/ui/Button";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

function InventoryAlertsSection() {
  const {
    module: { lowStockDevices, formatCurrency },
    alerts: { thresholdDraft, setThresholdDraft, updateThresholdDraftValue, handleSaveThreshold, isSavingThreshold },
    helpers: { resolveLowStockSeverity },
  } = useInventoryLayout();

  return (
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
          />
          <input
            type="number"
            min={0}
            max={100}
            value={thresholdDraft}
            onChange={(event) => updateThresholdDraftValue(Number(event.target.value))}
          />
          <Button
            variant="secondary"
            size="sm"
            type="button"
            onClick={() => {
              void handleSaveThreshold();
            }}
            disabled={isSavingThreshold}
          >
            {isSavingThreshold ? "Guardando…" : "Guardar umbral"}
          </Button>
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
}

export default InventoryAlertsSection;
