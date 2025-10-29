import React from "react";
import {
  ProductsBulkActions,
  ProductsExportModal,
  ProductsFiltersPanel,
  ProductsImportModal,
  ProductsSidePanel,
  ProductsStockAdjustModal,
  ProductsSummaryCards,
  ProductsTable,
} from "../components/products";
import type { ProductFilters, ProductRow } from "../components/products";

export default function InventoryProducts() {
  const [filters, setFilters] = React.useState<ProductFilters>({});
  const [selectedIds, setSelectedIds] = React.useState<string[]>([]);
  const [selectedRow, setSelectedRow] = React.useState<ProductRow | null>(null);
  const [openImport, setOpenImport] = React.useState(false);
  const [openExport, setOpenExport] = React.useState(false);
  const [openAdjust, setOpenAdjust] = React.useState(false);

  const rows = React.useMemo<ProductRow[]>(() => [], []);
  const isLoading = false;

  const summaryItems = React.useMemo(
    () => [
      { label: "Productos", value: rows.length, hint: "Registros activos" },
      {
        label: "Stock total",
        value: rows.reduce((acc, item) => acc + item.stock, 0),
        hint: "Unidades disponibles",
      },
      {
        label: "Valor inventario",
        value: rows.reduce((acc, item) => acc + item.stock * item.price, 0).toLocaleString("es-MX", {
          style: "currency",
          currency: "MXN",
          minimumFractionDigits: 2,
        }),
      },
      { label: "Filtros activos", value: Object.values(filters).filter(Boolean).length },
    ],
    [filters, rows],
  );

  const toggleSelect = React.useCallback((id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }, []);

  const toggleSelectAll = React.useCallback(() => {
    setSelectedIds((prev) => {
      if (rows.length === 0) return [];
      return prev.length === rows.length ? [] : rows.map((item) => item.id);
    });
  }, [rows]);

  const handleDeleteSelected = React.useCallback(() => {
    setSelectedIds([]);
    setSelectedRow(null);
  }, []);

  const handleAdjustStock = React.useCallback(() => {
    if (selectedRow || selectedIds.length > 0) {
      setOpenAdjust(true);
    }
  }, [selectedIds.length, selectedRow]);

  const handleAdjustConfirm = React.useCallback((_delta: number) => {
    setOpenAdjust(false);
  }, []);

  const handleExportSelected = React.useCallback(() => {
    setOpenExport(true);
  }, []);

  const handleRowClick = React.useCallback((row: ProductRow) => {
    setSelectedRow(row);
    setSelectedIds((prev) => (prev.includes(row.id) ? prev : [...prev, row.id]));
  }, []);

  const rowForAdjust = React.useMemo(() => {
    if (selectedRow) return selectedRow;
    const firstSelectedId = selectedIds[0];
    return rows.find((item) => item.id === firstSelectedId) ?? null;
  }, [rows, selectedIds, selectedRow]);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h2 style={{ margin: 0 }}>Productos</h2>
      <p style={{ margin: 0, color: "#9ca3af" }}>
        Lista y gestión de dispositivos por modelo, color, capacidad y IMEI.
      </p>

      <ProductsFiltersPanel value={filters} onChange={setFilters} />
      <ProductsSummaryCards items={summaryItems} />

      <ProductsBulkActions
        selectedCount={selectedIds.length}
        onExport={handleExportSelected}
        onAdjustStock={handleAdjustStock}
        onDelete={handleDeleteSelected}
      />

      <ProductsTable
        rows={rows}
        loading={isLoading}
        selectedIds={selectedIds}
        onToggleSelect={toggleSelect}
        onToggleSelectAll={toggleSelectAll}
        onRowClick={handleRowClick}
      />

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button
          onClick={() => setOpenImport(true)}
          style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.08)", color: "#e5e7eb", border: 0 }}
        >
          Importar
        </button>
        <button
          onClick={() => setOpenExport(true)}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
        >
          Exportar
        </button>
      </div>

      <ProductsSidePanel row={selectedRow} onClose={() => setSelectedRow(null)} />
      <ProductsImportModal open={openImport} onClose={() => setOpenImport(false)} />
      <ProductsExportModal open={openExport} onClose={() => setOpenExport(false)} />
      <ProductsStockAdjustModal
        open={openAdjust}
        row={rowForAdjust}
        onClose={() => setOpenAdjust(false)}
        onConfirm={handleAdjustConfirm}
      />
    </div>
  );
}
