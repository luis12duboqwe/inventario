import { Suspense, lazy, memo, useMemo } from "react";
import { Cog } from "lucide-react";

import ModuleHeader, { type ModuleStatus } from "../../../shared/components/ModuleHeader";
import Accordion, { type AccordionItem } from "../../../shared/components/ui/Accordion/Accordion";
import { useOperationsModule } from "../hooks/useOperationsModule";

const CustomersPanel = lazy(() => import("../components/Customers"));
const SuppliersPanel = lazy(() => import("../components/Suppliers"));
const POSDashboard = lazy(() => import("../components/POS/POSDashboard"));
const PurchasesPanel = lazy(() => import("../components/Purchases"));
const SalesPanel = lazy(() => import("../components/Sales"));
const ReturnsPanel = lazy(() => import("../components/Returns"));
const TransferOrdersPanel = lazy(() => import("../components/TransferOrders"));
const InternalMovementsPanel = lazy(() => import("../components/InternalMovementsPanel"));
const OperationsHistoryPanel = lazy(() => import("../components/OperationsHistoryPanel"));

const SectionLoader = memo(function SectionLoader({ label }: { label: string }) {
  return (
    <section className="card" role="status" aria-live="polite">
      <div className="loading-overlay compact">
        <span className="spinner" aria-hidden="true" />
        <span>Cargando {label}…</span>
      </div>
    </section>
  );
});

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
        content: enablePurchasesSales ? (
          <Suspense fallback={<SectionLoader label="panel de ventas y compras" />}>
            <div className="section-grid">
              <CustomersPanel token={token} />
              <SuppliersPanel token={token} stores={stores} />
              <POSDashboard
                token={token}
                stores={stores}
                defaultStoreId={selectedStoreId}
                onInventoryRefresh={refreshInventoryAfterTransfer}
              />
              <PurchasesPanel
                token={token}
                stores={stores}
                defaultStoreId={selectedStoreId}
                onInventoryRefresh={refreshInventoryAfterTransfer}
              />
              <SalesPanel
                token={token}
                stores={stores}
                defaultStoreId={selectedStoreId}
                onInventoryRefresh={refreshInventoryAfterTransfer}
              />
              <ReturnsPanel
                token={token}
                stores={stores}
                defaultStoreId={selectedStoreId}
                onInventoryRefresh={refreshInventoryAfterTransfer}
              />
            </div>
          </Suspense>
        ) : (
          <section className="card">
            <h2>Compras y ventas</h2>
            <p className="muted-text">
              Activa el flag corporativo <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para operar compras, ventas y devoluciones.
            </p>
          </section>
        ),
      },
      {
        id: "internal",
        title: "Movimientos internos",
        description: "Ajustes, recepciones y conteos internos con bitácora instantánea.",
        content: (
          <Suspense fallback={<SectionLoader label="movimientos internos" />}>
            <div className="section-grid">
              <InternalMovementsPanel stores={stores} defaultStoreId={selectedStoreId} />
            </div>
          </Suspense>
        ),
      },
      {
        id: "transfers",
        title: "Transferencias entre tiendas",
        description: "Flujo SOLICITADA → EN_TRANSITO → RECIBIDA con permisos por sucursal.",
        content: enableTransfers ? (
          <Suspense fallback={<SectionLoader label="transferencias entre tiendas" />}>
            <div className="section-grid">
              <TransferOrdersPanel
                token={token}
                stores={stores}
                defaultOriginId={selectedStoreId}
                onRefreshInventory={refreshInventoryAfterTransfer}
              />
            </div>
          </Suspense>
        ) : (
          <section className="card">
            <h2>Transferencias entre tiendas</h2>
            <p className="muted-text">
              Para habilitar transferencias activa el flag <code>SOFTMOBILE_ENABLE_TRANSFERS</code>.
            </p>
          </section>
        ),
      },
      {
        id: "history",
        title: "Historial de operaciones",
        description: "Consulta unificado de movimientos recientes por tienda.",
        content: (
          <Suspense fallback={<SectionLoader label="historial de operaciones" />}>
            <div className="section-grid">
              <OperationsHistoryPanel token={token} stores={stores} />
            </div>
          </Suspense>
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
