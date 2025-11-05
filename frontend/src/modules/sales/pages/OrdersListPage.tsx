import React, { useMemo, useState } from "react";

import {
  OrdersCancelModal,
  OrdersEmailInvoiceModal,
  OrdersPaymentCaptureModal,
  OrdersReturnModal,
} from "../components/orders";
import {
  OrdersBulkActions as OrdersListBulkActions,
  OrdersExportModal,
  OrdersFiltersBar,
  OrdersImportModal,
  OrdersPagination,
  OrdersSidePanel,
  OrdersSummaryCards,
  OrdersTable,
  type OrderFilters,
  type OrderRow,
} from "../components/orders-list";

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
    paid: 25999,
    status: "COMPLETED",
    paymentStatus: "PAID",
    channel: "POS",
    storeId: "MX-001",
  },
  {
    id: "ord-1002",
    number: "F-2025-0002",
    date: "2025-02-16",
    customer: "Corporativo Atlan",
    itemsCount: 8,
    total: 112499,
    paid: 56249,
    status: "OPEN",
    paymentStatus: "PARTIAL",
    channel: "WEB",
    storeId: "MX-002",
  },
  {
    id: "ord-1003",
    number: "F-2025-0003",
    date: "2025-02-16",
    customer: "Luis Hernández",
    itemsCount: 1,
    total: 7899,
    paid: 0,
    status: "OPEN",
    paymentStatus: "UNPAID",
    channel: "POS",
    storeId: "MX-001",
  },
  {
    id: "ord-1004",
    number: "F-2025-0004",
    date: "2025-02-17",
    customer: "Ferretería Norte",
    itemsCount: 5,
    total: 34999,
    paid: 34999,
    status: "CANCELLED",
    paymentStatus: "REFUNDED",
    channel: "MANUAL",
    storeId: "MX-003",
  },
  {
    id: "ord-1005",
    number: "F-2025-0005",
    date: "2025-02-17",
    customer: "Sofía Ramírez",
    itemsCount: 2,
    total: 14599,
    paid: 0,
    status: "DRAFT",
    paymentStatus: "UNPAID",
    channel: "WEB",
    storeId: "MX-002",
  },
  {
    id: "ord-1006",
    number: "F-2025-0006",
    date: "2025-02-18",
    customer: "Consultores Delta",
    itemsCount: 6,
    total: 68500,
    paid: 68500,
    status: "COMPLETED",
    paymentStatus: "PAID",
    channel: "MANUAL",
    storeId: "MX-001",
  },
  {
    id: "ord-1007",
    number: "F-2025-0007",
    date: "2025-02-18",
    customer: "Laura Ponce",
    itemsCount: 4,
    total: 18999,
    paid: 12000,
    status: "OPEN",
    paymentStatus: "PARTIAL",
    channel: "POS",
    storeId: "MX-002",
  },
];

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function OrdersListPage() {
  const [filters, setFilters] = useState<OrderFilters>({ status: "ALL", payment: "ALL", channel: "ALL" });
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeRow, setActiveRow] = useState<OrderRow | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [importOpen, setImportOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [returnOpen, setReturnOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 5;

  const filteredRows = useMemo(() => {
    const normalizedQuery = filters.query?.trim().toLowerCase() ?? "";
    return ORDERS_DATA.filter((order) => {
      if (filters.status && filters.status !== "ALL" && order.status !== filters.status) {
        return false;
      }
      if (filters.payment && filters.payment !== "ALL" && order.paymentStatus !== filters.payment) {
        return false;
      }
      if (filters.channel && filters.channel !== "ALL" && order.channel !== filters.channel) {
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
  }, [filters.channel, filters.dateFrom, filters.dateTo, filters.payment, filters.query, filters.status]);

  const summaryCards = useMemo(() => {
    const count = filteredRows.length;
    const totalAmount = filteredRows.reduce((sum, order) => sum + order.total, 0);
    const paidCount = filteredRows.filter((order) => order.paymentStatus === "PAID").length;
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
      filteredRows.map(({ id, number, date, customer, itemsCount, total, paid, status, paymentStatus, channel }) => ({
        id,
        number,
        date,
        customer,
        itemsCount,
        total,
        paid,
        status,
        paymentStatus,
        channel,
      })),
    [filteredRows],
  );

  const pages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(Math.max(1, page), pages);
  const paginatedRows = rows.slice((safePage - 1) * pageSize, safePage * pageSize);

  const toggleSelect = (id: string) => {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
  };

  const toggleSelectAll = () => {
    setSelectedIds((current) => {
      const currentPageIds = paginatedRows.map((row) => row.id);
      if (currentPageIds.every((identifier) => current.includes(identifier))) {
        return current.filter((identifier) => !currentPageIds.includes(identifier));
      }
      const unique = new Set([...current, ...currentPageIds]);
      return Array.from(unique);
    });
  };

  const handleFiltersChange = (next: OrderFilters) => {
    setFilters(next);
    setSelectedIds([]);
    setPage(1);
  };

  const handleMarkPaidMany = () => {
    setMessage(`Se marcaron como pagadas ${selectedIds.length} órdenes.`);
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

  const handlePrintSelected = () => {
    setMessage(`Se enviaron ${selectedIds.length} órdenes a impresión.`);
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <OrdersFiltersBar value={filters} onChange={handleFiltersChange} />
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

      <OrdersListBulkActions
        selectedCount={selectedIds.length}
        onMarkPaid={handleMarkPaidMany}
        onCancel={() => setCancelOpen(true)}
        onExport={() => setExportOpen(true)}
        onPrint={handlePrintSelected}
        onImport={() => setImportOpen(true)}
      />

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
        <button onClick={() => setEmailOpen(true)} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Enviar recibo
        </button>
        <button onClick={() => setReturnOpen(true)} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Procesar devolución
        </button>
        <button
          onClick={() => setCaptureOpen(true)}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
        >
          Registrar pago manual
        </button>
      </div>

      <OrdersTable
        rows={paginatedRows}
        loading={false}
        selectedIds={selectedIds}
        onToggleSelect={toggleSelect}
        onToggleSelectAll={toggleSelectAll}
        onRowClick={(row) => setActiveRow(row)}
      />

      <OrdersSidePanel row={activeRow} onClose={() => setActiveRow(null)} />

      <OrdersPagination page={page} pages={pages} onPage={setPage} />

      <OrdersImportModal open={importOpen} onClose={() => setImportOpen(false)} />
      <OrdersExportModal open={exportOpen} onClose={() => setExportOpen(false)} />
      <OrdersEmailInvoiceModal open={emailOpen} onClose={() => setEmailOpen(false)} />
      <OrdersCancelModal open={cancelOpen} onClose={() => setCancelOpen(false)} onConfirm={handleBulkCancel} />
      <OrdersReturnModal open={returnOpen} onClose={() => setReturnOpen(false)} onSubmit={handleBulkRefund} />
      <OrdersPaymentCaptureModal open={captureOpen} onClose={() => setCaptureOpen(false)} onSubmit={handleCapturePayment} />
    </div>
  );
}

export default OrdersListPage;
