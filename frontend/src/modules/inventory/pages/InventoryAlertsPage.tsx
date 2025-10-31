import PageHeader from "../../../components/layout/PageHeader";
import { useInventoryLayout } from "./context/InventoryLayoutContext";
import InventoryAlertsSection from "./components/InventoryAlertsSection";

function InventoryAlertsPage() {
  const {
    module: { selectedStore },
  } = useInventoryLayout();

  return (
    <div className="inventory-alerts-page">
      <PageHeader
        title="Alertas de inventario"
        subtitle={
          selectedStore
            ? `Configuración y seguimiento para ${selectedStore.name}`
            : "Selecciona una sucursal para ajustar el umbral de alertas."
        }
      />

      <InventoryAlertsSection />
    </div>
  );
}

export default InventoryAlertsPage;
