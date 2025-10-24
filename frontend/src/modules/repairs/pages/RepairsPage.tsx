import { useState } from "react";
import { Wrench } from "lucide-react";

import RepairOrders from "../components/RepairOrders";
import ModuleHeader, { type ModuleStatus } from "../../../shared/components/ModuleHeader";
import { useRepairsModule } from "../hooks/useRepairsModule";

function RepairsPage() {
  const { token, stores, selectedStoreId, refreshInventoryAfterTransfer, enablePurchasesSales } = useRepairsModule();
  const [status, setStatus] = useState<ModuleStatus>(enablePurchasesSales ? "ok" : "warning");
  const [statusLabel, setStatusLabel] = useState(
    enablePurchasesSales
      ? "Reparaciones al día"
      : "Activa SOFTMOBILE_ENABLE_PURCHASES_SALES para habilitar reparaciones",
  );

  const handleStatusChange = (nextStatus: ModuleStatus, label: string) => {
    setStatus(nextStatus);
    setStatusLabel(label);
  };

  if (!enablePurchasesSales) {
    return (
      <div className="module-content">
        <ModuleHeader
          icon={<Wrench aria-hidden="true" />}
          title="Reparaciones"
          subtitle="Seguimiento de órdenes y control de piezas vinculadas al inventario"
          status="warning"
          statusLabel="Activa SOFTMOBILE_ENABLE_PURCHASES_SALES para habilitar reparaciones"
        />
        <section className="card">
          <h2>Órdenes de reparación</h2>
          <p className="muted-text">
            Activa <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para habilitar el flujo de reparaciones y sus ajustes de
            inventario vinculados.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<Wrench aria-hidden="true" />}
        title="Reparaciones"
        subtitle="Seguimiento de órdenes y control de piezas vinculadas al inventario"
        status={status}
        statusLabel={statusLabel}
      />
      <div className="section-grid">
        <RepairOrders
          token={token}
          stores={stores}
          defaultStoreId={selectedStoreId}
          onInventoryRefresh={refreshInventoryAfterTransfer}
          onStatusChange={handleStatusChange}
        />
      </div>
    </div>
  );
}

export default RepairsPage;
