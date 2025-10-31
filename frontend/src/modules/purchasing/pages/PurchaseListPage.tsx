import React, { useMemo, useState } from "react";
import {
  POBulkActions,
  POExportModal,
  POFiltersBar,
  POImportModal,
  POSidePanel,
  POSummaryCards,
  POTable,
  POPagination,
} from "../components/po-list";

type Filters = {
  query?: string;
  status?: "ALL" | "DRAFT" | "SENT" | "PARTIAL" | "RECEIVED" | "CANCELLED";
  supplier?: string;
  dateFrom?: string;
  dateTo?: string;
};

type PurchaseRow = {
  id: string;
  date: string;
  number?: string;
  supplier?: string;
  itemsCount: number;
  total: number;
  received: number;
  status: "DRAFT" | "SENT" | "PARTIAL" | "RECEIVED" | "CANCELLED";
};

export default function PurchaseListPage() {
  const [filters, setFilters] = useState<Filters>({});
  const [rows] = useState<PurchaseRow[]>([]); // TODO(wire) cargar
  const [loading] = useState<boolean>(false);
  const [activeRow, setActiveRow] = useState<PurchaseRow | null>(null);
  const [showImport, setShowImport] = useState<boolean>(false);
  const [showExport, setShowExport] = useState<boolean>(false);
  const [page, setPage] = useState<number>(1);
  const [selectedIds] = useState<string[]>([]); // TODO(wire) selección por tabla

  const pages = 1; // TODO(wire) paginación real

  const summaryItems = useMemo(
    () => [
      { label: "Borradores", value: "—" },
      { label: "Enviadas", value: "—" },
      { label: "Parciales", value: "—" },
      { label: "Recibidas", value: "—" },
    ],
    [],
  );

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <POSummaryCards items={summaryItems} />
      <POFiltersBar
        value={filters}
        onChange={setFilters}
        onNew={() => {
          // TODO(wire) abrir modal crear PO
        }}
      />
      <POBulkActions
        selectedCount={selectedIds.length}
        onImport={() => setShowImport(true)}
        onExport={() => setShowExport(true)}
      />
      <POTable rows={rows} loading={loading} onRowClick={setActiveRow} />
      <POSidePanel row={activeRow} onClose={() => setActiveRow(null)} />
      <POImportModal open={showImport} onClose={() => setShowImport(false)} />
      <POExportModal open={showExport} onClose={() => setShowExport(false)} />
      <POPagination page={page} pages={pages} onPage={setPage} />
    </div>
  );
}
