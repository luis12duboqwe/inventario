import PageHeader from "../../../components/layout/PageHeader";
import { useInventoryLayout } from "./context/InventoryLayoutContext";
import PriceLists from "../../catalog/components/PriceLists";

function InventoryPriceListsPage(): JSX.Element {
  const { module } = useInventoryLayout();
  const subtitle = module.selectedStore
    ? `Define precios corporativos personalizados para ${module.selectedStore.name}.`
    : "Selecciona una sucursal para filtrar listas específicas o administra listas globales.";

  return (
    <div className="inventory-price-lists-page">
      <PageHeader
        title="Listas de precios"
        subtitle={subtitle}
      />
      <PriceLists />
    </div>
  );
}

export default InventoryPriceListsPage;
