import PageHeader from "../../../components/layout/PageHeader";
import { useInventoryLayout } from "./context/InventoryLayoutContext";
import InventorySuppliersSection from "./components/InventorySuppliersSection";

function InventorySuppliersPage() {
  const {
    module: { selectedStore },
  } = useInventoryLayout();

  return (
    <div className="inventory-suppliers-page">
      <PageHeader
        title="Seguimiento de proveedores"
        subtitle={
          selectedStore
            ? `Compras recientes para ${selectedStore.name}`
            : "Selecciona una sucursal para consultar lotes asociados."
        }
      />

      <InventorySuppliersSection />
    </div>
  );
}

export default InventorySuppliersPage;
