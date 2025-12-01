import { useState } from "react";
import { Boxes, Layers, Wrench } from "lucide-react";
import Tabs, { type TabOption } from "@components/ui/Tabs/Tabs";
import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import { useInventoryLayout } from "./context/InventoryLayoutContext";
import InventoryStatusSection from "./components/InventoryStatusSection";
import InventoryProductsTableSection from "./components/InventoryProductsTableSection";
import InventoryCatalogToolsSection from "./components/InventoryCatalogToolsSection";
import InventorySmartImportSection from "./components/InventorySmartImportSection";
import InventoryCorrectionsSection from "./components/InventoryCorrectionsSection";
import InventoryProductsFilters from "./components/InventoryProductsFilters";
import InventoryVariantsSection from "./components/InventoryVariantsSection";
import InventoryBundlesSection from "./components/InventoryBundlesSection";

function InventoryProductsPage() {
  const {
    downloads: { triggerDownloadReport, triggerDownloadCsv, triggerRefreshSummary },
  } = useInventoryLayout();

  const [activeTab, setActiveTab] = useState("catalog");

  const tabs: TabOption<string>[] = [
    {
      id: "catalog",
      label: "Catálogo",
      icon: <Boxes size={16} />,
      content: (
        <>
          <InventoryStatusSection />
          <InventoryProductsTableSection />
        </>
      ),
    },
    {
      id: "variants",
      label: "Variantes y Kits",
      icon: <Layers size={16} />,
      content: (
        <>
          <InventoryVariantsSection />
          <InventoryBundlesSection />
        </>
      ),
    },
    {
      id: "tools",
      label: "Herramientas",
      icon: <Wrench size={16} />,
      content: (
        <>
          <InventoryCatalogToolsSection />
          <InventorySmartImportSection />
          <InventoryCorrectionsSection />
        </>
      ),
    },
  ];

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

      <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  );
}

export default InventoryProductsPage;
