import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import { useInventoryLayout } from "./context/InventoryLayoutContext";
import InventoryStatusSection from "./components/InventoryStatusSection";
import InventoryProductsTableSection from "./components/InventoryProductsTableSection";
import InventoryCatalogToolsSection from "./components/InventoryCatalogToolsSection";
import InventorySmartImportSection from "./components/InventorySmartImportSection";
import InventoryCorrectionsSection from "./components/InventoryCorrectionsSection";
import InventoryProductsFilters from "./components/InventoryProductsFilters";
import InventoryReportsPanel from "../components/InventoryReportsPanel";

function InventoryProductsPage() {
  const {
    module: inventoryModule,
    downloads: {
      triggerDownloadReport,
      triggerDownloadCsv,
      triggerRefreshSummary,
      requestDownloadWithReason,
    },
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
            variant: "ghost",
          },
        ]}
      >
        <InventoryProductsFilters />
      </PageToolbar>

      <InventoryStatusSection />

      <InventoryProductsTableSection />

      <InventoryCatalogToolsSection />

      <InventoryReportsPanel
        stores={inventoryModule.stores}
        selectedStoreId={inventoryModule.selectedStoreId}
        formatCurrency={inventoryModule.formatCurrency}
        fetchInventoryCurrentReport={inventoryModule.fetchInventoryCurrentReport}
        downloadInventoryCurrentCsv={inventoryModule.downloadInventoryCurrentCsv}
        downloadInventoryCurrentPdf={inventoryModule.downloadInventoryCurrentPdf}
        downloadInventoryCurrentXlsx={inventoryModule.downloadInventoryCurrentXlsx}
        fetchInventoryValueReport={inventoryModule.fetchInventoryValueReport}
        fetchInventoryMovementsReport={inventoryModule.fetchInventoryMovementsReport}
        fetchTopProductsReport={inventoryModule.fetchTopProductsReport}
        requestDownloadWithReason={requestDownloadWithReason}
        downloadInventoryValueCsv={inventoryModule.downloadInventoryValueCsv}
        downloadInventoryValuePdf={inventoryModule.downloadInventoryValuePdf}
        downloadInventoryValueXlsx={inventoryModule.downloadInventoryValueXlsx}
        downloadInventoryMovementsCsv={inventoryModule.downloadInventoryMovementsCsv}
        downloadInventoryMovementsPdf={inventoryModule.downloadInventoryMovementsPdf}
        downloadInventoryMovementsXlsx={inventoryModule.downloadInventoryMovementsXlsx}
        downloadTopProductsCsv={inventoryModule.downloadTopProductsCsv}
        downloadTopProductsPdf={inventoryModule.downloadTopProductsPdf}
        downloadTopProductsXlsx={inventoryModule.downloadTopProductsXlsx}
      />

      <InventorySmartImportSection />

      <InventoryCorrectionsSection />
    </div>
  );
}

export default InventoryProductsPage;
