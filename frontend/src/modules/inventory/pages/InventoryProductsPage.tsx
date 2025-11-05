import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import { useInventoryLayout } from "./context/InventoryLayoutContext";
import InventoryStatusSection from "./components/InventoryStatusSection";
import InventoryProductsTableSection from "./components/InventoryProductsTableSection";
import InventoryCatalogToolsSection from "./components/InventoryCatalogToolsSection";
import InventorySmartImportSection from "./components/InventorySmartImportSection";
import InventoryCorrectionsSection from "./components/InventoryCorrectionsSection";
import InventoryProductsFilters from "./components/InventoryProductsFilters";

function InventoryProductsPage() {
  const {
    downloads: { triggerDownloadReport, triggerDownloadCsv, triggerRefreshSummary },
  } = useInventoryLayout();

  return (
    <div className="inventory-products-page">
      <PageHeader
        title="Inventario de productos"
        subtitle="Consulta y administra el catálogo consolidado de dispositivos."
        actions={[
          {
            label: "Descargar PDF",
            onClick: triggerDownloadReport,
            variant: "secondary",
          },
          {
            label: "Descargar CSV",
            onClick: triggerDownloadCsv,
            variant: "secondary",
          },
        ]}
      />

      <PageToolbar
        actions={[
          {
            label: "Actualizar métricas",
            onClick: triggerRefreshSummary,
          },
        ]}
      >
        <InventoryProductsFilters />
      </PageToolbar>

      <InventoryStatusSection />

      <InventoryProductsTableSection />

      <InventoryCatalogToolsSection />

      <InventorySmartImportSection />

      <InventoryCorrectionsSection />
    </div>
  );
}

export default InventoryProductsPage;
