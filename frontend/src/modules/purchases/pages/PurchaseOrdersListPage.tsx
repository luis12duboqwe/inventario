import React, { useMemo, useState } from "react";

import {
  POBulkActions,
  POCancelModal,
  POExportModal,
  POFiltersPanel,
  POImportModal,
  POReceiveModal,
  POSidePanel,
  POSummaryCards,
  POTable,
  type POFilters,
  type PORow,
} from "../components/po-list";

type PurchaseOrderRecord = PORow & {
  storeId: string;
};

const PURCHASE_ORDERS_SAMPLE: PurchaseOrderRecord[] = [
  {
    id: "po-1001",
    number: "PO-2025-0001",
    date: "2025-02-15",
    supplier: "Grupo Electra",
    itemsCount: 12,
    total: 185000,
    status: "OPEN",
    storeId: "CDMX-NTE",
  },
  {
    id: "po-1002",
    number: "PO-2025-0002",
    date: "2025-02-16",
    supplier: "Tecno Global",
    itemsCount: 5,
    total: 78999,
    status: "PARTIAL",
    storeId: "CDMX-CEN",
  },
  {
    id: "po-1003",
    number: "PO-2025-0003",
    date: "2025-02-17",
    supplier: "Distribuciones Norte",
    itemsCount: 8,
    total: 56450,
    status: "RECEIVED",
    storeId: "GDL-001",
  },
  {
    id: "po-1004",
    number: "PO-2025-0004",
    date: "2025-02-18",
    supplier: "Electro Mayoristas",
    itemsCount: 3,
    total: 32500,
    status: "CANCELLED",
    storeId: "MTY-001",
  },
  {
    id: "po-1005",
    number: "PO-2025-0005",
    date: "2025-02-18",
    supplier: "Atlan Components",
    itemsCount: 10,
    total: 125999,
    status: "OPEN",
    storeId: "CDMX-CEN",
  },
  {
    id: "po-1006",
    number: "PO-2025-0006",
    date: "2025-02-19",
    supplier: "Refacciones del Sur",
    itemsCount: 6,
    total: 38990,
    status: "PARTIAL",
    storeId: "MER-001",
  },
  {
    id: "po-1007",
    number: "PO-2025-0007",
    date: "2025-02-19",
    supplier: "Innovación Digital",
    itemsCount: 4,
    total: 45999,
    status: "DRAFT",
    storeId: "CDMX-NTE",
  },
];

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function PurchaseOrdersListPage() {
  const [filters, setFilters] = useState<POFilters>({ status: "ALL" });
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeRow, setActiveRow] = useState<PORow | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [importOpen, setImportOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [receiveOpen, setReceiveOpen] = useState(false);

  const filteredRecords = useMemo(() => {
    const normalizedQuery = filters.query?.trim().toLowerCase() ?? "";
    return PURCHASE_ORDERS_SAMPLE.filter((record) => {
      if (filters.status && filters.status !== "ALL" && record.status !== filters.status) {
        return false;
      }
      if (filters.storeId && record.storeId !== filters.storeId) {
        return false;
      }
      if (filters.dateFrom && record.date < filters.dateFrom) {
        return false;
      }
      if (filters.dateTo && record.date > filters.dateTo) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack = `${record.supplier} ${record.number ?? ""}`.toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [filters.dateFrom, filters.dateTo, filters.query, filters.status, filters.storeId]);

  const rows: PORow[] = useMemo(
    () =>
      filteredRecords.map(({ id, number, date, supplier, itemsCount, total, status }) => {
        const row: PORow = {
          id,
          date,
          supplier,
          itemsCount,
          total,
          status,
        };
        if (number) {
          row.number = number;
        }
        return row;
      }),
    [filteredRecords],
  );

  const summaryCards = useMemo(() => {
    const totalOrders = filteredRecords.length;
    const totalAmount = filteredRecords.reduce((sum, record) => sum + record.total, 0);
    const received = filteredRecords.filter((record) => record.status === "RECEIVED").length;
    const partial = filteredRecords.filter((record) => record.status === "PARTIAL").length;
    const average = totalOrders > 0 ? totalAmount / totalOrders : 0;

    return [
      { label: "Órdenes", value: totalOrders, hint: `${received} recibidas` },
      { label: "Monto total", value: currency.format(totalAmount), hint: `Promedio ${currency.format(average)}` },
      { label: "Parciales", value: partial, hint: `${((partial / Math.max(totalOrders, 1)) * 100).toFixed(0)}%` },
      {
        label: "Seleccionadas",
        value: selectedIds.length,
        hint: selectedIds.length ? "Listas para acción masiva" : "Selecciona filas",
      },
    ];
  }, [filteredRecords, selectedIds.length]);

  const handleToggleSelect = (id: string) => {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
  };

  const handleToggleSelectAll = () => {
    setSelectedIds((current) => {
      if (current.length === rows.length) {
        return [];
      }
      return rows.map((row) => row.id);
    });
  };

  const handleFiltersChange = (next: POFilters) => {
    setFilters(next);
    setSelectedIds([]);
  };

  const handleBulkCancel = () => {
    setMessage(`Se cancelaron ${selectedIds.length} órdenes de compra.`);
    setCancelOpen(false);
    setSelectedIds([]);
  };

  const handleQuickReceive = (payload: { qty: number }) => {
    setMessage(`Recepción rápida registrada por ${payload.qty} unidades.`);
    setReceiveOpen(false);
  };

  const closeMessage = () => setMessage(null);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <POFiltersPanel value={filters} onChange={handleFiltersChange} />
      <POSummaryCards items={summaryCards} />

      {message ? (
        <div
          role="status"
          style={{
            padding: 12,
            borderRadius: 12,
            border: "1px solid rgba(34, 197, 94, 0.4)",
            background: "rgba(34, 197, 94, 0.08)",
            color: "#bbf7d0",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{message}</span>
          <button onClick={closeMessage} style={{ padding: "6px 10px", borderRadius: 8 }}>
            Cerrar
          </button>
        </div>
      ) : null}

      <POBulkActions
        selectedCount={selectedIds.length}
        onImport={() => setImportOpen(true)}
        onExport={() => setExportOpen(true)}
        onCancel={() => setCancelOpen(true)}
        onReceive={() => setReceiveOpen(true)}
      />

      <POTable
        rows={rows}
        loading={false}
        selectedIds={selectedIds}
        onToggleSelect={handleToggleSelect}
        onToggleSelectAll={handleToggleSelectAll}
        onRowClick={setActiveRow}
      />

  <POSidePanel row={activeRow} onClose={() => setActiveRow(null)} />

      <POImportModal open={importOpen} onClose={() => setImportOpen(false)} />
      <POExportModal open={exportOpen} onClose={() => setExportOpen(false)} />
      <POCancelModal open={cancelOpen} onClose={() => setCancelOpen(false)} onConfirm={handleBulkCancel} />
      <POReceiveModal open={receiveOpen} onClose={() => setReceiveOpen(false)} onSubmit={handleQuickReceive} />
    </div>
  );
}

export default PurchaseOrdersListPage;
