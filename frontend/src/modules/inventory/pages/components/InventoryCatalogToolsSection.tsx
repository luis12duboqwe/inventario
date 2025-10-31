import { Suspense, lazy } from "react";

import Button from "../../../../shared/components/ui/Button";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

const AdvancedSearch = lazy(() => import("../../components/AdvancedSearch"));

function InventoryCatalogToolsSection() {
  const {
    module: { enableCatalogPro, token, selectedStore },
    catalog: { catalogFile, setCatalogFile, importingCatalog, exportingCatalog, lastImportSummary, fileInputRef },
    downloads: { triggerExportCatalog, triggerImportCatalog },
  } = useInventoryLayout();

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Herramientas de catálogo</h2>
          <p className="card-subtitle">Importa o exporta productos con campos extendidos.</p>
        </div>
      </header>
      <div className="catalog-tools">
        <div className="catalog-actions">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={triggerExportCatalog}
            disabled={exportingCatalog}
          >
            {exportingCatalog ? "Exportando…" : "Exportar catálogo CSV"}
          </Button>
        </div>
        <div className="catalog-import">
          <label className="file-input">
            <span>Archivo CSV</span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => {
                const file = event.target.files?.[0] ?? null;
                setCatalogFile(file);
              }}
            />
            <small className="muted-text">
              {catalogFile
                ? `Seleccionado: ${catalogFile.name}`
                : "Incluye encabezados sku, name, categoria, condicion, estado, costo_compra, precio_venta, ubicacion, fecha_ingreso, descripcion"}
            </small>
          </label>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={triggerImportCatalog}
            disabled={importingCatalog || !catalogFile}
          >
            {importingCatalog ? "Importando…" : "Importar catálogo"}
          </Button>
        </div>
        {lastImportSummary ? (
          <div className="catalog-summary">
            <p className="muted-text">
              Creados: {lastImportSummary.created} · Actualizados: {lastImportSummary.updated} · Omitidos: {lastImportSummary.skipped}
            </p>
            {lastImportSummary.errors.length > 0 ? (
              <ul className="error-list">
                {lastImportSummary.errors.slice(0, 5).map((error) => (
                  <li key={`${error.row}-${error.message}`}>
                    Fila {error.row}: {error.message}
                  </li>
                ))}
                {lastImportSummary.errors.length > 5 ? (
                  <li className="muted-text">Se omitieron {lastImportSummary.errors.length - 5} errores adicionales.</li>
                ) : null}
              </ul>
            ) : (
              <p className="muted-text">No se registraron errores en la última importación.</p>
            )}
          </div>
        ) : (
          <p className="muted-text">
            Descarga la plantilla actual para conservar todos los campos: SKU, categoría, condición, estado, costo_compra, precio_venta,
            ubicación, fechas y descripción.
          </p>
        )}
      </div>
      {enableCatalogPro ? (
        <div className="section-grid">
          <Suspense fallback={<div className="card catalog-card"><p className="muted-text">Cargando búsqueda avanzada…</p></div>}>
            <AdvancedSearch token={token} storeName={selectedStore?.name ?? undefined} />
          </Suspense>
        </div>
      ) : null}
    </section>
  );
}

export default InventoryCatalogToolsSection;
