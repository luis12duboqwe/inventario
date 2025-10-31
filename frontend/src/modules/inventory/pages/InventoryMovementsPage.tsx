import PageHeader from "../../../components/layout/PageHeader";
import InventoryMovementFormSection from "./components/InventoryMovementFormSection";
import InventoryMovementsTimelineSection from "./components/InventoryMovementsTimelineSection";
import InventoryTransferFormSection from "./components/InventoryTransferFormSection"; // [PACK30-31-FRONTEND]

function InventoryMovementsPage() {
  return (
    <div className="inventory-movements-page">
      <PageHeader
        title="Movimientos de inventario"
        subtitle="Registra ajustes y consulta la bitácora reciente de entradas y salidas."
      />

      <InventoryMovementFormSection />

      <InventoryTransferFormSection />

      <InventoryMovementsTimelineSection />
    </div>
  );
}

export default InventoryMovementsPage;
