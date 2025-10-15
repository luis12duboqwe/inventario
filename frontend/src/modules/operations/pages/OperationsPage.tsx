import { useMemo } from "react";
import { Cog } from "lucide-react";

import Customers from "../components/Customers";
import InternalMovementsPanel from "../components/InternalMovementsPanel";
import OperationsHistoryPanel from "../components/OperationsHistoryPanel";
import POSDashboard from "../components/POS/POSDashboard";
import Purchases from "../components/Purchases";
import Returns from "../components/Returns";
import Sales from "../components/Sales";
import Suppliers from "../components/Suppliers";
import TransferOrders from "../components/TransferOrders";
import ModuleHeader, { type ModuleStatus } from "../../../components/ModuleHeader";
import Accordion, { type AccordionItem } from "../../../components/ui/Accordion/Accordion";
import { useOperationsModule } from "../hooks/useOperationsModule";

type OperationsAccordionId =
  | "sales"
  | "internal"
  | "transfers"
  | "history";

type OperationsAccordionItem = AccordionItem<OperationsAccordionId>;

function OperationsPage() {
  const {
    token,
    stores,
    selectedStoreId,
    enablePurchasesSales,
    enableTransfers,
    refreshInventoryAfterTransfer,
  } = useOperationsModule();

  let moduleStatus: ModuleStatus = "ok";
  let moduleStatusLabel = "Flujos de operaciones activos";

  if (!enablePurchasesSales && !enableTransfers) {
    moduleStatus = "critical";
    moduleStatusLabel = "Operaciones deshabilitadas. Activa los flags corporativos";
  } else if (!enablePurchasesSales || !enableTransfers) {
    moduleStatus = "warning";
    moduleStatusLabel = "Revisa las funciones pendientes por activar";
  }

  const accordionItems = useMemo<OperationsAccordionItem[]>(
    () => [
      {
        id: "sales",
        title: "Ventas / Compras",
        description: "POS táctil, compras, devoluciones y catálogos corporativos.",
        defaultOpen: true,
        content: (
          <div className="section-grid">
            {enablePurchasesSales ? (
              <>
                <Customers token={token} />
                <Suppliers token={token} stores={stores} />
                <POSDashboard
                  token={token}
                  stores={stores}
                  defaultStoreId={selectedStoreId}
                  onInventoryRefresh={refreshInventoryAfterTransfer}
                />
                <Purchases
                  token={token}
                  stores={stores}
                  defaultStoreId={selectedStoreId}
                  onInventoryRefresh={refreshInventoryAfterTransfer}
                />
                <Sales
                  token={token}
                  stores={stores}
                  defaultStoreId={selectedStoreId}
                  onInventoryRefresh={refreshInventoryAfterTransfer}
                />
                <Returns
                  token={token}
                  stores={stores}
                  defaultStoreId={selectedStoreId}
                  onInventoryRefresh={refreshInventoryAfterTransfer}
                />
              </>
            ) : (
              <section className="card">
                <h2>Compras y ventas</h2>
                <p className="muted-text">
                  Activa el flag corporativo <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para operar compras, ventas y
                  devoluciones.
                </p>
              </section>
            )}
          </div>
        ),
      },
      {
        id: "internal",
        title: "Movimientos internos",
        description: "Ajustes, recepciones y conteos internos con bitácora instantánea.",
        content: (
          <div className="section-grid">
            <InternalMovementsPanel stores={stores} defaultStoreId={selectedStoreId} />
          </div>
        ),
      },
      {
        id: "transfers",
        title: "Transferencias entre tiendas",
        description: "Flujo SOLICITADA → EN_TRANSITO → RECIBIDA con permisos por sucursal.",
        content: (
          <div className="section-grid">
            {enableTransfers ? (
              <TransferOrders
                token={token}
                stores={stores}
                defaultOriginId={selectedStoreId}
                onRefreshInventory={refreshInventoryAfterTransfer}
              />
            ) : (
              <section className="card">
                <h2>Transferencias entre tiendas</h2>
                <p className="muted-text">
                  Para habilitar transferencias activa el flag <code>SOFTMOBILE_ENABLE_TRANSFERS</code>.
                </p>
              </section>
            )}
          </div>
        ),
      },
      {
        id: "history",
        title: "Historial de operaciones",
        description: "Consulta unificado de movimientos recientes por tienda.",
        content: (
          <div className="section-grid">
            <OperationsHistoryPanel stores={stores} />
          </div>
        ),
      },
    ],
    [
      enablePurchasesSales,
      enableTransfers,
      refreshInventoryAfterTransfer,
      selectedStoreId,
      stores,
      token,
    ],
  );

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<Cog aria-hidden="true" />}
        title="Operaciones"
        subtitle="Compras, ventas, devoluciones y transferencias sincronizadas con inventario"
        status={moduleStatus}
        statusLabel={moduleStatusLabel}
      />
      <Accordion items={accordionItems} />
    </div>
  );
}

export default OperationsPage;
