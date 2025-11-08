import { ShieldAlert } from "lucide-react";

import PageHeader from "../../../components/layout/PageHeader";
import PriceLists from "../../catalog/components/PriceLists";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { useInventoryLayout } from "./context/InventoryLayoutContext";

function InventoryPriceListsPage(): JSX.Element {
  const { enablePriceLists } = useDashboard();
  const {
    module: { selectedStore },
  } = useInventoryLayout();

  if (!enablePriceLists) {
    return (
      <div className="inventory-price-lists-page">
        <PageHeader
          title="Listas de precios"
          subtitle="Activa la bandera corporativa para gestionar precios preferenciales."
        />

        <div className="inventory-price-lists-disabled" role="alert">
          <ShieldAlert size={24} aria-hidden="true" />
          <div>
            <p className="inventory-price-lists-disabled__title">
              Funcionalidad protegida por flag corporativa
            </p>
            <p className="inventory-price-lists-disabled__content">
              Define la variable <code>SOFTMOBILE_ENABLE_PRICE_LISTS=1</code> en tu entorno para habilitar
              la creación y asignación de listas. Mientras permanezca desactivada, los precios publicados
              seguirán calculándose con el catálogo base.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="inventory-price-lists-page">
      <PageHeader
        title="Listas de precios"
        subtitle={
          selectedStore
            ? `Gestiona ajustes de precios vinculados a ${selectedStore.name}.`
            : "Selecciona una sucursal para definir listas específicas."
        }
      />

      <PriceLists />
    </div>
  );
}

export default InventoryPriceListsPage;
