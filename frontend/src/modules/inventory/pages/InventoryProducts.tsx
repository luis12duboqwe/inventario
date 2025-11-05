import React from "react";

import {
  ProductsBulkActions,
  ProductsExportModal,
  ProductsFiltersBar,
  ProductsGrid,
  ProductsImportModal,
  ProductsMoveCategoryModal,
  ProductsPagination,
  ProductsSidePanel,
  ProductsSummaryCards,
  ProductsTable,
  ProductsTagModal,
  ProductsViewSwitch,
} from "../components/products-list";
import type { ProductFilters, ProductCardData, ProductRow } from "../components/products-list";
import { useInventoryLayout } from "./context/InventoryLayoutContext"; // [PACK30-31-FRONTEND]

type MovePayload = { categoryId: string };
type TagPayload = { tags: string[] };

type SummaryCard = {
  label: string;
  value: string | number;
  hint?: string;
};

export default function InventoryProducts() {
  const {
    module: { stores },
  } = useInventoryLayout(); // [PACK30-31-FRONTEND]
  const [filters, setFilters] = React.useState<ProductFilters>({ status: "ALL", storeId: null });
  const [mode, setMode] = React.useState<"grid" | "table">("grid");
  const [selectedIds, setSelectedIds] = React.useState<string[]>([]);
  const [side, setSide] = React.useState<ProductRow | null>(null);
  const [mImport, setMImport] = React.useState(false);
  const [mExport, setMExport] = React.useState(false);
  const [mMove, setMMove] = React.useState(false);
  const [mTag, setMTag] = React.useState(false);
  const [page, setPage] = React.useState<number>(1);

  const rows = React.useMemo<ProductRow[]>(() => [], []);
  const isLoading = false;
  const pages = 1;

  const gridItems = React.useMemo<ProductCardData[]>(
    () =>
      rows.map((row) => {
        const card: ProductCardData = {
          id: row.id,
          name: row.name,
          price: row.price,
          status: row.status,
          stock: row.stock,
        };
        if (row.sku) {
          card.sku = row.sku;
        }
        return card;
      }),
    [rows],
  );

  const activeFilters = React.useMemo(() => {
    return Object.entries(filters).reduce((count, [key, value]) => {
      if (value == null) {
        return count;
      }
      if (typeof value === "boolean") {
        return value ? count + 1 : count;
      }
      if (typeof value === "number") {
        return Number.isFinite(value) ? count + 1 : count;
      }
      const normalized = value.toString().trim();
      if (normalized.length === 0) {
        return count;
      }
      if (key === "status" && normalized === "ALL") {
        return count;
      }
      return count + 1;
    }, 0);
  }, [filters]);

  const summaryItems = React.useMemo<SummaryCard[]>(() => {
    const totalStock = rows.reduce((acc, item) => acc + item.stock, 0);
    const inventoryValue = rows.reduce((acc, item) => acc + item.stock * item.price, 0);
    const currencyFormatter = new Intl.NumberFormat("es-MX", {
      style: "currency",
      currency: "MXN",
      minimumFractionDigits: 2,
    });

    return [
      { label: "Productos", value: rows.length, hint: "Registros activos" },
      { label: "Stock total", value: totalStock, hint: "Unidades disponibles" },
      { label: "Valor inventario", value: currencyFormatter.format(inventoryValue) },
      { label: "Filtros activos", value: activeFilters },
    ];
  }, [activeFilters, rows]);

  const toggleSelect = React.useCallback((id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
  }, []);

  const toggleSelectAll = React.useCallback(() => {
    setSelectedIds((prev) => {
      if (rows.length === 0) {
        return [];
      }
      return prev.length === rows.length ? [] : rows.map((item) => item.id);
    });
  }, [rows]);

  const handleRowClick = React.useCallback((row: ProductRow) => {
    setSide(row);
    setSelectedIds((prev) => (prev.includes(row.id) ? prev : [...prev, row.id]));
  }, []);

  const handleOpenSideFromGrid = React.useCallback(
    (id: string) => {
      const target = rows.find((row) => row.id === id) ?? null;
      setSide(target);
      if (target) {
        setSelectedIds((prev) => (prev.includes(target.id) ? prev : [...prev, target.id]));
      }
    },
    [rows],
  );

  const handleActivate = React.useCallback(() => {
    setSelectedIds([]);
  }, []);

  const handleDeactivate = React.useCallback(() => {
    setSelectedIds([]);
  }, []);

  const handleMoveCategory = React.useCallback(() => {
    setMMove(true);
  }, []);

  const handleImport = React.useCallback(() => {
    setMImport(true);
  }, []);

  const handleExport = React.useCallback(() => {
    setMExport(true);
  }, []);

  const handleTag = React.useCallback(() => {
    setMTag(true);
  }, []);

  const handleMoveCategorySubmit = React.useCallback((payload: MovePayload) => {
    console.info("Mover categoría", payload);
    setMMove(false);
    setSelectedIds([]);
  }, []);

  const handleTagSubmit = React.useCallback((payload: TagPayload) => {
    console.info("Etiquetar productos", payload);
    setMTag(false);
  }, []);

  const handlePageChange = React.useCallback((nextPage: number) => {
    setPage(nextPage);
  }, []);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div>
        <h2 style={{ margin: 0 }}>Productos</h2>
        <p style={{ margin: 0, color: "#9ca3af" }}>
          Lista y gestión de dispositivos por modelo, color, capacidad y IMEI.
        </p>
      </div>

      <ProductsFiltersBar value={filters} onChange={setFilters} stores={stores} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <ProductsSummaryCards items={summaryItems} />
        <ProductsViewSwitch mode={mode} onChange={setMode} />
      </div>

      <ProductsBulkActions
        selectedCount={selectedIds.length}
        onActivate={handleActivate}
        onDeactivate={handleDeactivate}
        onExport={handleExport}
        onImport={handleImport}
        onMoveCategory={handleMoveCategory}
        onTag={handleTag}
      />

      {mode === "grid" ? (
        <ProductsGrid items={gridItems} onClick={handleOpenSideFromGrid} />
      ) : (
        <ProductsTable
          rows={rows}
          loading={isLoading}
          selectedIds={selectedIds}
          onToggleSelect={toggleSelect}
          onToggleSelectAll={toggleSelectAll}
          onRowClick={handleRowClick}
        />
      )}

      <ProductsPagination page={page} pages={pages} onPage={handlePageChange} />

        {side ? (
          <ProductsSidePanel
            product={{
              name: side.name,
              price: side.price,
              status: side.status,
              stock: side.stock,
              ...(side.sku ? { sku: side.sku } : {}),
              ...(side.category ? { category: side.category } : {}),
            }}
            onClose={() => setSide(null)}
          />
        ) : null}
      <ProductsImportModal open={mImport} onClose={() => setMImport(false)} />
      <ProductsExportModal open={mExport} onClose={() => setMExport(false)} />
      <ProductsMoveCategoryModal open={mMove} onClose={() => setMMove(false)} onSubmit={handleMoveCategorySubmit} />
      <ProductsTagModal open={mTag} onClose={() => setMTag(false)} onSubmit={handleTagSubmit} />
    </div>
  );
}
