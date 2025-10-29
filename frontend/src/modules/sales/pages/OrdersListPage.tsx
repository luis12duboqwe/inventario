import React, { useMemo, useState } from "react";

import {
  OrdersBulkActions,
  OrdersCancelModal,
  OrdersEmailInvoiceModal,
  OrdersExportModal,
  OrdersFiltersPanel,
  OrdersPaymentCaptureModal,
  OrdersReturnModal,
  OrdersSidePanel,
  OrdersSummaryCards,
  OrdersTable,
  type OrderFilters,
  type OrderRow,
} from "../components/orders";

type OrderRecord = OrderRow & {
  storeId: string;
};

const ORDERS_DATA: OrderRecord[] = [
  {
    id: "ord-1001",
    number: "F-2025-0001",
    date: "2025-02-15",
    customer: "Andrea Solís",
    itemsCount: 3,
    total: 25999,
    status: "PAID",
    storeId: "MX-001",
  },
  {
    id: "ord-1002",
    number: "F-2025-0002",
    date: "2025-02-16",
    customer: "Corporativo Atlan",
    itemsCount: 8,
    total: 112499,
    status: "OPEN",
    storeId: "MX-002",
  },
  {
    id: "ord-1003",
    number: "F-2025-0003",
    date: "2025-02-16",
    customer: "Luis Hernández",
    itemsCount: 1,
    total: 7899,
    status: "PAID",
    storeId: "MX-001",
  },
  {
    id: "ord-1004",
    number: "F-2025-0004",
    date: "2025-02-17",
    customer: "Ferretería Norte",
    itemsCount: 5,
    total: 34999,
    status: "CANCELLED",
    storeId: "MX-003",
  },
  {
    id: "ord-1005",
    number: "F-2025-0005",
    date: "2025-02-17",
    customer: "Sofía Ramírez",
    itemsCount: 2,
    total: 14599,
    status: "OPEN",
    storeId: "MX-002",
  },
  {
    id: "ord-1006",
    number: "F-2025-0006",
    date: "2025-02-18",
    customer: "Consultores Delta",
    itemsCount: 6,
    total: 68500,
    status: "REFUNDED",
    storeId: "MX-001",
  },
  {
    id: "ord-1007",
    number: "F-2025-0007",
    date: "2025-02-18",
    customer: "Laura Ponce",
    itemsCount: 4,
    total: 18999,
    status: "DRAFT",
    storeId: "MX-002",
  },
];

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function OrdersListPage() {
  const [filters, setFilters] = useState<OrderFilters>({ status: "ALL" });
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeRow, setActiveRow] = useState<OrderRow | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [exportOpen, setExportOpen] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [returnOpen, setReturnOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);

  const filteredRows = useMemo(() => {
    const normalizedQuery = filters.query?.trim().toLowerCase() ?? "";
    return ORDERS_DATA.filter((order) => {
      if (filters.status && filters.status !== "ALL" && order.status !== filters.status) {
        return false;
      }
      if (filters.storeId && order.storeId !== filters.storeId) {
        return false;
      }
      if (filters.dateFrom && order.date < filters.dateFrom) {
        return false;
      }
      if (filters.dateTo && order.date > filters.dateTo) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack = `${order.customer} ${order.number}`.toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [filters.dateFrom, filters.dateTo, filters.query, filters.status, filters.storeId]);

  const summaryCards = useMemo(() => {
    const count = filteredRows.length;
    const totalAmount = filteredRows.reduce((sum, order) => sum + order.total, 0);
    const paidCount = filteredRows.filter((order) => order.status === "PAID").length;
    const openCount = filteredRows.filter((order) => order.status === "OPEN").length;
    const average = count > 0 ? totalAmount / count : 0;

    return [
      { label: "Órdenes", value: count, hint: `${paidCount} pagadas` },
      { label: "Ingresos", value: currency.format(totalAmount), hint: `Promedio ${currency.format(average)}` },
      { label: "Pendientes", value: openCount, hint: `${((openCount / Math.max(count, 1)) * 100).toFixed(0)}%` },
      {
        label: "Seleccionadas",
        value: selectedIds.length,
        hint: selectedIds.length ? "Listas para acciones masivas" : "Selecciona filas para actuar",
      },
    ];
  }, [filteredRows, selectedIds.length]);

  const rows: OrderRow[] = useMemo(
    () =>
      filteredRows.map(({ id, number, date, customer, itemsCount, total, status }) => ({
        id,
        number,
        date,
        customer,
        itemsCount,
        total,
        status,
      })),
    [filteredRows],
  );

  const toggleSelect = (id: string) => {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
  };

  const toggleSelectAll = () => {
    setSelectedIds((current) => {
      if (current.length === rows.length) {
        return [];
      }
      return rows.map((row) => row.id);
    });
  };

  const handleFiltersChange = (next: OrderFilters) => {
    setFilters(next);
    setSelectedIds([]);
  };

  const handleBulkCancel = () => {
    setMessage(`Se cancelaron ${selectedIds.length} órdenes.`);
    setCancelOpen(false);
    setSelectedIds([]);
  };

  const handleBulkRefund = (payload: { amount: number }) => {
    setMessage(`Se registró la devolución por ${currency.format(payload.amount)}.`);
    setReturnOpen(false);
    setSelectedIds([]);
  };

  const handleCapturePayment = (payload: { amount: number }) => {
    setMessage(`Pago registrado por ${currency.format(payload.amount)}.`);
    setCaptureOpen(false);
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <OrdersFiltersPanel value={filters} onChange={handleFiltersChange} />
      <OrdersSummaryCards items={summaryCards} />

      {message ? (
        <div
          style={{
            padding: 12,
            borderRadius: 12,
            border: "1px solid rgba(56, 189, 248, 0.4)",
            background: "rgba(56, 189, 248, 0.08)",
            color: "#bae6fd",
          }}
        >
          {message}
        </div>
      ) : null}

      <OrdersBulkActions
        selectedCount={selectedIds.length}
        onExport={() => setExportOpen(true)}
        onEmail={() => setEmailOpen(true)}
        onCancel={() => setCancelOpen(true)}
        onRefund={() => setReturnOpen(true)}
      />

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          onClick={() => setCaptureOpen(true)}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
        >
          Registrar pago manual
        </button>
      </div>

      <OrdersTable
        rows={rows}
        loading={false}
        selectedIds={selectedIds}
        onToggleSelect={toggleSelect}
        onToggleSelectAll={toggleSelectAll}
        onRowClick={(row) => setActiveRow(row)}
      />

      <OrdersSidePanel row={activeRow} onClose={() => setActiveRow(null)} />

      <OrdersExportModal open={exportOpen} onClose={() => setExportOpen(false)} />
      <OrdersEmailInvoiceModal open={emailOpen} onClose={() => setEmailOpen(false)} />
      <OrdersCancelModal open={cancelOpen} onClose={() => setCancelOpen(false)} onConfirm={handleBulkCancel} />
      <OrdersReturnModal open={returnOpen} onClose={() => setReturnOpen(false)} onSubmit={handleBulkRefund} />
      <OrdersPaymentCaptureModal open={captureOpen} onClose={() => setCaptureOpen(false)} onSubmit={handleCapturePayment} />
    </div>
  );
}

export default OrdersListPage;
