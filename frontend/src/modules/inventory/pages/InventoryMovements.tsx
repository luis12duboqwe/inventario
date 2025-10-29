import React from "react";
import {
  MovementsBulkActions,
  MovementsCreateModal,
  MovementsFiltersPanel,
  MovementsImportModal,
  MovementsSidePanel,
  MovementsSummaryCards,
  MovementsTable,
} from "../components/movements";
import type {
  MovementCreatePayload,
  MovementFilters,
  MovementRow,
} from "../components/movements";
import {
  MOVEMENT_TYPE_OPTIONS,
  getMovementTypePluralLabel,
  type MovementType,
} from "../components/movements/constants";

export default function InventoryMovements() {
  const [filters, setFilters] = React.useState<MovementFilters>({ type: "ALL" });
  const [selectedIds, setSelectedIds] = React.useState<string[]>([]);
  const [selectedRow, setSelectedRow] = React.useState<MovementRow | null>(null);
  const [openCreate, setOpenCreate] = React.useState(false);
  const [openImport, setOpenImport] = React.useState(false);

  const data = React.useMemo<{ rows: MovementRow[] }>(
    () => ({ rows: [] }),
    [],
  );
  const rows = Array.isArray(data?.rows) ? data.rows : [];
  const isLoading = false;

  const activeFilters = React.useMemo(
    () => Object.values(filters || {}).filter(Boolean).length,
    [filters],
  );

  const summaryItems = React.useMemo(() => {
    const totalsByType = rows.reduce<Record<MovementType, number>>(
      (acc, row) => {
        acc[row.type] = (acc[row.type] ?? 0) + 1;
        return acc;
      },
      { entrada: 0, salida: 0, ajuste: 0 },
    );
    const totalUnits = rows.reduce((acc, row) => acc + row.qty, 0);
    const typeSummaries = MOVEMENT_TYPE_OPTIONS.map((option) => ({
      label: getMovementTypePluralLabel(option.value),
      value: totalsByType[option.value],
    }));
    return [
      {
        label: "Movimientos",
        value: rows.length,
        hint: `${totalUnits} unidades registradas · ${activeFilters} filtros activos`,
      },
      ...typeSummaries,
    ];
  }, [activeFilters, rows]);

  const toggleSelect = React.useCallback((id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
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

  const handleExportSelected = React.useCallback(() => {
    // TODO: conectar con exportación masiva en packs posteriores
  }, []);

  const handleRowClick = React.useCallback((row: MovementRow) => {
    setSelectedRow(row);
    setSelectedIds((prev) => (prev.includes(row.id) ? prev : [...prev, row.id]));
  }, []);

  const handleCreateMovement = React.useCallback((_: MovementCreatePayload) => {
    setOpenCreate(false);
  }, []);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h2 style={{ margin: 0 }}>Movimientos</h2>
      <p style={{ margin: 0, color: "#9ca3af" }}>Entradas, salidas y ajustes sincronizados con inventario.</p>

      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button
          onClick={() => setOpenImport(true)}
          style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.08)", color: "#e5e7eb", border: 0 }}
        >
          Importar
        </button>
        <button
          onClick={() => setOpenCreate(true)}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
        >
          Nuevo movimiento
        </button>
      </div>

      <MovementsFiltersPanel value={filters} onChange={setFilters} />
      <MovementsSummaryCards items={summaryItems} />

      <MovementsBulkActions
        selectedCount={selectedIds.length}
        onExport={handleExportSelected}
        onDelete={handleDeleteSelected}
      />

      <MovementsTable
        rows={rows}
        loading={isLoading}
        selectedIds={selectedIds}
        onToggleSelect={toggleSelect}
        onToggleSelectAll={toggleSelectAll}
        onRowClick={handleRowClick}
      />

      <MovementsSidePanel row={selectedRow} onClose={() => setSelectedRow(null)} />
      <MovementsCreateModal
        open={openCreate}
        onClose={() => setOpenCreate(false)}
        onCreate={handleCreateMovement}
      />
      <MovementsImportModal open={openImport} onClose={() => setOpenImport(false)} />
    </div>
  );
}
