import { Suspense, lazy } from "react";

import { FileSpreadsheet, RefreshCcw } from "lucide-react";

import Button from "../../../../shared/components/ui/Button";
import Loader from "../../../../components/common/Loader";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

const MovementForm = lazy(() => import("../../components/MovementForm"));

function InventoryMovementFormSection() {
  const {
    module: { devices, handleMovement },
    downloads: { triggerRefreshSummary, triggerDownloadReport, triggerDownloadCsv },
  } = useInventoryLayout();

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Registrar movimiento</h2>
          <p className="card-subtitle">Ajustes, entradas y salidas sincronizadas con inventario.</p>
        </div>
        <div className="card-actions">
          <Button variant="primary" size="sm" type="button" onClick={triggerRefreshSummary}>
            Actualizar métricas
          </Button>
          <Button
            variant="ghost"
            size="sm"
            type="button"
            onClick={triggerDownloadReport}
            leadingIcon={<FileSpreadsheet aria-hidden="true" size={16} />}
          >
            Descargar PDF
          </Button>
          <Button
            variant="ghost"
            size="sm"
            type="button"
            onClick={triggerDownloadCsv}
            leadingIcon={<FileSpreadsheet aria-hidden="true" size={16} />}
          >
            Descargar CSV
          </Button>
        </div>
      </header>
      <Suspense fallback={<Loader message="Cargando formulario de movimientos…" variant="compact" />}>
        <MovementForm devices={devices} onSubmit={handleMovement} />
      </Suspense>
    </section>
  );
}

export default InventoryMovementFormSection;
