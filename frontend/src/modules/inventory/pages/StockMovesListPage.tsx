import React from "react";
import {
  MoveApproveModal,
  MoveBulkActions,
  MoveCancelModal,
  MoveExportModal,
  MoveFiltersPanel,
  MoveImportModal,
  MoveSidePanel,
  MoveSummaryCards,
  MovesTable,
} from "../components/moves-list";
import type { MoveFilters, MoveRow } from "../components/moves-list";

export default function StockMovesListPage() {
  const [filters, setFilters] = React.useState<MoveFilters>({ status: "ALL", type: "ALL" });
  const [selectedIds, setSelectedIds] = React.useState<string[]>([]);
  const [selectedRow, setSelectedRow] = React.useState<MoveRow | null>(null);
  const [openImport, setOpenImport] = React.useState(false);
  const [openExport, setOpenExport] = React.useState(false);
  const [openApprove, setOpenApprove] = React.useState(false);
  const [openCancel, setOpenCancel] = React.useState(false);

  // TODO: conectar con servicio real en packs posteriores
  const data = React.useMemo<{ rows: MoveRow[] }>(() => ({ rows: [] }), []);
  const rows = Array.isArray(data?.rows) ? data.rows : [];
  const isLoading = false;

  const summaryItems = React.useMemo(() => {
    const totalsByType = rows.reduce(
      (acc, row) => {
        acc[row.type] = (acc[row.type] || 0) + 1;
        return acc;
      },
      { IN: 0, OUT: 0, TRANSFER: 0, ADJUST: 0 } as Record<MoveRow["type"], number>,
    );
    const totalUnits = rows.reduce((acc, row) => acc + row.itemsCount, 0);
    const activeFilters = Object.values(filters || {}).filter(Boolean).length;

    return [
      {
        label: "Movimientos",
        value: rows.length,
        hint: `${totalUnits} unidades registradas · ${activeFilters} filtros activos`,
      },
      { label: "Entradas", value: totalsByType.IN },
      { label: "Salidas", value: totalsByType.OUT },
      { label: "Transferencias", value: totalsByType.TRANSFER },
    ];
  }, [filters, rows]);

  const toggleSelect = React.useCallback((id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  }, []);

  const toggleSelectAll = React.useCallback(() => {
    setSelectedIds((prev) => {
      if (rows.length === 0) {
        return [];
      }
      return prev.length === rows.length ? [] : rows.map((item) => item.id);
    });
  }, [rows]);

  const handleApproveMany = React.useCallback(() => {
    setOpenApprove(false);
    setSelectedIds([]);
  }, []);

  const handleCancelMany = React.useCallback(() => {
    setOpenCancel(false);
    setSelectedIds([]);
  }, []);

  const handlePrintMany = React.useCallback(() => {
    // TODO: conectar con impresión masiva
  }, []);

  const handleRowClick = React.useCallback((row: MoveRow) => {
    setSelectedRow(row);
  }, []);

  React.useEffect(() => {
    if (!selectedRow) {
      return;
    }
    if (!selectedIds.includes(selectedRow.id)) {
      setSelectedIds((prev) => [...prev, selectedRow.id]);
    }
  }, [selectedIds, selectedRow]);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0 }}>Movimientos</h2>
          <p style={{ margin: 0, color: "#9ca3af" }}>
            Entradas, salidas, ajustes y transferencias entre tiendas.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => setOpenImport(true)}
            style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.08)", color: "#e5e7eb", border: 0 }}
            type="button"
          >
            Importar
          </button>
          <button
            onClick={() => setOpenExport(true)}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
            type="button"
          >
            Exportar
          </button>
        </div>
      </header>

      <MoveFiltersPanel value={filters} onChange={setFilters} />
      <MoveSummaryCards items={summaryItems} />

      <MoveBulkActions
        selectedCount={selectedIds.length}
        onApprove={() => setOpenApprove(true)}
        onCancel={() => setOpenCancel(true)}
        onExport={() => setOpenExport(true)}
        onPrint={handlePrintMany}
        onImport={() => setOpenImport(true)}
      />

      <MovesTable
        rows={rows}
        loading={isLoading}
        selectedIds={selectedIds}
        onToggleSelect={toggleSelect}
        onToggleSelectAll={toggleSelectAll}
        onRowClick={handleRowClick}
      />

      <MoveSidePanel row={selectedRow || undefined} onClose={() => setSelectedRow(null)} />

      <MoveImportModal open={openImport} onClose={() => setOpenImport(false)} />
      <MoveExportModal open={openExport} onClose={() => setOpenExport(false)} />
      <MoveApproveModal
        open={openApprove}
        onClose={() => setOpenApprove(false)}
        onConfirm={handleApproveMany}
      />
      <MoveCancelModal
        open={openCancel}
        onClose={() => setOpenCancel(false)}
        onConfirm={handleCancelMany}
      />
    </div>
  );
}
