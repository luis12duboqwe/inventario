import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

const InventoryTable = lazy(() => import("../../components/InventoryTable"));

function InventoryProductsTableSection() {
  const {
    module: { devices },
    metrics: { lastRefreshDisplay },
    search: { filteredDevices, highlightedDeviceIds },
    editing: { openEditDialog },
  } = useInventoryLayout();

  return (
    <section className="card wide">
      <header className="card-header">
        <div>
          <h2>Inventario actual</h2>
          <p className="card-subtitle">Consulta existencias y administra los productos catalogados.</p>
        </div>
        <div className="inventory-meta">
          <span className="muted-text">Mostrando {filteredDevices.length} de {devices.length} dispositivos</span>
          <span className="inventory-last-update">Última actualización: {lastRefreshDisplay}</span>
        </div>
      </header>
      <Suspense fallback={<Loader message="Cargando tabla de inventario…" variant="compact" />}>
        <InventoryTable
          devices={filteredDevices}
          highlightedDeviceIds={highlightedDeviceIds}
          onEditDevice={openEditDialog}
        />
      </Suspense>
    </section>
  );
}

export default InventoryProductsTableSection;
