import { Suspense, lazy } from "react";

import Loader from "../../../../components/common/Loader";
import PageHeader from "../../../../components/layout/PageHeader";
import PageToolbar from "../../../../components/layout/PageToolbar";
import FlowAuditCard, { type FlowAuditFlow } from "../../../../shared/components/FlowAuditCard";
import { useOperationsModule } from "../../hooks/useOperationsModule";

const SalesPanel = lazy(() => import("../../components/Sales"));
const ReturnsPanel = lazy(() => import("../../components/Returns"));

function FacturacionPage() {
  const { token, stores, selectedStoreId, enablePurchasesSales, refreshInventoryAfterTransfer } =
    useOperationsModule();

  const auditFlows: FlowAuditFlow[] = [
    {
      id: "facturacion",
      title: "Facturación en menos pasos",
      summary: "Selecciona sucursal, agrega artículos y confirma con motivo válido (≥5 caracteres).",
      steps: [
        "Verifica la sucursal activa y reutiliza el motivo corporativo sugerido.",
        "Busca por IMEI/SKU desde la barra lateral y agrega artículos con un clic.",
        "Confirma el método de pago, revisa impuestos y descarga la factura al cierre.",
      ],
      actions: [
        {
          id: "scroll-ventas",
          label: "Ir a ventas",
          tooltip: "Saltar directo al formulario de venta",
          onClick: () =>
            document.getElementById("ventas-facturacion-panel")?.scrollIntoView({ behavior: "smooth" }),
        },
      ],
    },
    {
      id: "devoluciones",
      title: "Devoluciones guiadas",
      summary: "Valida ticket, ingresa motivo y confirma el ajuste de inventario sin salir del tablero.",
      steps: [
        "Filtra por sucursal y cliente para recuperar la venta original.",
        "Captura el motivo de devolución y verifica los lotes antes de confirmar.",
        "Genera el comprobante y marca la reposición para disparar la sincronización de inventario.",
      ],
      actions: [
        {
          id: "scroll-devoluciones",
          label: "Ir a devoluciones",
          tooltip: "Saltar a la bandeja de devoluciones",
          onClick: () =>
            document.getElementById("ventas-devoluciones-panel")?.scrollIntoView({ behavior: "smooth" }),
        },
      ],
    },
  ];

  if (!enablePurchasesSales) {
    return (
      <div className="operations-subpage">
        <PageHeader
          title="Facturación"
          subtitle="Genera facturas, notas de venta y devoluciones con motivo corporativo"
        />
        <section className="card">
          <p className="muted-text">
            Activa el flag corporativo <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para utilizar facturación y devoluciones.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="operations-subpage">
      <PageHeader
        title="Facturación"
        subtitle="Controla ventas, devoluciones y notas fiscales sincronizadas"
      />
      <FlowAuditCard
        title="Flujos de facturación auditados"
        subtitle="Reducimos clics y mantenemos tabs, acordeones y grillas sin alterar la estructura base"
        flows={auditFlows}
      />
      <PageToolbar />
      <div className="operations-subpage__grid">
        <div id="ventas-facturacion-panel">
          <Suspense fallback={<Loader message="Cargando ventas…" />}>
            <SalesPanel
              token={token}
              stores={stores}
              defaultStoreId={selectedStoreId}
              onInventoryRefresh={refreshInventoryAfterTransfer}
            />
          </Suspense>
        </div>
        <div id="ventas-devoluciones-panel">
          <Suspense fallback={<Loader message="Cargando devoluciones…" />}>
            <ReturnsPanel
              token={token}
              stores={stores}
              defaultStoreId={selectedStoreId}
              onInventoryRefresh={refreshInventoryAfterTransfer}
            />
          </Suspense>
        </div>
      </div>
    </div>
  );
}

export default FacturacionPage;
