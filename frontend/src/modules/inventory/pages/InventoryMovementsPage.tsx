import PageHeader from "../../../components/layout/PageHeader";
import InventoryMovementFormSection from "./components/InventoryMovementFormSection";
import InventoryMovementsTimelineSection from "./components/InventoryMovementsTimelineSection";

function InventoryMovementsPage() {
  return (
    <div className="inventory-movements-page">
      <PageHeader
        title="Movimientos de inventario"
        subtitle="Registra ajustes y consulta la bitácora reciente de entradas y salidas."
      />

      <InventoryMovementFormSection />

      <InventoryMovementsTimelineSection />
    </div>
  );
}

export default InventoryMovementsPage;
