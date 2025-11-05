import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  POExportModal,
  POFiltersBar,
  POImportModal,
  POPagination,
  POSidePanel,
  POSummaryCards,
  POTable,
  type PurchaseOrderFilters,
  type PurchaseOrderListRow,
} from "../components/po-list";
import { importPurchaseOrdersCsv, listPurchaseOrders, type PurchaseOrder } from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";

const PAGE_SIZE = 10;

const STATUS_LABELS: Record<PurchaseOrder["status"], string> = {
  PENDIENTE: "Pendiente",
  PARCIAL: "Recepción parcial",
  COMPLETADA: "Completada",
  CANCELADA: "Cancelada",
};

const currencyFormatter = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
});

type EnrichedRow = PurchaseOrderListRow & { statusCode: PurchaseOrder["status"] };

type SummaryCard = { label: string; value: string | number; hint?: string };

type DatePredicate = (value: string) => boolean;

function parseDateFilter(value?: string): DatePredicate | null {
  if (!value) {
    return null;
  }
  const target = new Date(value);
  if (Number.isNaN(target.getTime())) {
    return null;
  }
  target.setHours(0, 0, 0, 0);
  return (candidate) => {
    const date = new Date(candidate);
    if (Number.isNaN(date.getTime())) {
      return false;
    }
    date.setHours(0, 0, 0, 0);
    return date >= target;
  };
}

function parseDateUpperBound(value?: string): DatePredicate | null {
  if (!value) {
    return null;
  }
  const target = new Date(value);
  if (Number.isNaN(target.getTime())) {
    return null;
  }
  target.setHours(23, 59, 59, 999);
  return (candidate) => {
    const date = new Date(candidate);
    if (Number.isNaN(date.getTime())) {
      return false;
    }
    return date <= target;
  };
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString("es-MX");
}

function mapOrderToRow(order: PurchaseOrder, deviceLookup: Map<number, { sku: string; name: string }>): EnrichedRow {
  const itemsCount = order.items.reduce((total, item) => total + item.quantity_ordered, 0);
  const totalAmount = order.items.reduce(
    (sum, item) => sum + item.quantity_ordered * item.unit_cost,
    0,
  );
  const receivedValue = order.items.reduce(
    (sum, item) => sum + item.quantity_received * item.unit_cost,
    0,
  );

  const statusLabel = STATUS_LABELS[order.status] ?? order.status;
  const firstItem = order.items[0];
  const device = firstItem ? deviceLookup.get(firstItem.device_id) : undefined;

  return {
    id: String(order.id),
    date: formatDate(order.created_at),
    number: `PO-${order.id.toString().padStart(5, "0")}`,
    supplier: order.supplier || device?.name || "—",
    itemsCount,
    total: totalAmount,
    received: receivedValue,
    status: order.status,
    statusLabel,
    statusCode: order.status,
  };
}

function buildSummaryCards(rows: EnrichedRow[]): SummaryCard[] {
  if (rows.length === 0) {
    return [
      { label: "Órdenes", value: 0, hint: "Sin registros" },
      { label: "Monto total", value: currencyFormatter.format(0), hint: "Recibido $0" },
      { label: "Parciales", value: 0, hint: "0%" },
      { label: "Promedio", value: currencyFormatter.format(0), hint: "Sin datos" },
    ];
  }

  const totalAmount = rows.reduce((sum, row) => sum + row.total, 0);
  const receivedAmount = rows.reduce((sum, row) => sum + row.received, 0);
  const partialCount = rows.filter((row) => row.statusCode === "PARCIAL").length;
  const pendingCount = rows.filter((row) => row.statusCode === "PENDIENTE").length;
  const percentagePartial = ((partialCount / rows.length) * 100).toFixed(0);
  const average = rows.length > 0 ? totalAmount / rows.length : 0;

  return [
    {
      label: "Órdenes",
      value: rows.length,
      hint: `${pendingCount} pendientes`,
    },
    {
      label: "Monto total",
      value: currencyFormatter.format(totalAmount),
      hint: `Recibido ${currencyFormatter.format(receivedAmount)}`,
    },
    {
      label: "Parciales",
      value: partialCount,
      hint: `${percentagePartial}%`,
    },
    {
      label: "Promedio",
      value: currencyFormatter.format(average),
      hint: "Monto medio por orden",
    },
  ];
}

const errorBoxStyle: React.CSSProperties = {
  padding: 12,
  borderRadius: 12,
  border: "1px solid rgba(248, 113, 113, 0.5)",
  background: "rgba(248, 113, 113, 0.12)",
  color: "#fecaca",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const messageBoxStyle: React.CSSProperties = {
  padding: 12,
  borderRadius: 12,
  border: "1px solid rgba(37, 211, 102, 0.4)",
  background: "rgba(37, 211, 102, 0.12)",
  color: "#bbf7d0",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

function PurchaseListPage() {
  const { devices, selectedStoreId, token, setError: setDashError, pushToast } = useDashboard();
  const [filters, setFilters] = useState<PurchaseOrderFilters>({ status: "ALL" });
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [activeRow, setActiveRow] = useState<EnrichedRow | null>(null);
  const [page, setPage] = useState(1);

  const deviceLookup = useMemo(
    () =>
      new Map(devices.map((device) => [device.id, { sku: device.sku, name: device.name }])),
    [devices],
  );

  const loadOrders = useCallback(async () => {
    if (!selectedStoreId) {
      setOrders([]);
      return;
    }
    try {
      setLoading(true);
      const data = await listPurchaseOrders(token, selectedStoreId, 200);
      setOrders(data);
      setError(null);
    } catch (err) {
      const friendly =
        err instanceof Error
          ? err.message
          : "No fue posible cargar las órdenes de compra.";
      setError(friendly);
      setDashError(friendly);
    } finally {
      setLoading(false);
    }
  }, [selectedStoreId, token, setDashError]);

  useEffect(() => {
    void loadOrders();
  }, [loadOrders]);

  const filteredOrders = useMemo(() => {
    const lowerQuery = filters.query?.trim().toLowerCase() ?? "";
    const supplierFilter = filters.supplier?.trim().toLowerCase() ?? "";
    const statusFilter = filters.status && filters.status !== "ALL" ? filters.status : null;
    const fromPredicate = parseDateFilter(filters.dateFrom);
    const toPredicate = parseDateUpperBound(filters.dateTo);

    return orders.filter((order) => {
      if (statusFilter && order.status !== statusFilter) {
        return false;
      }
      if (fromPredicate && !fromPredicate(order.created_at)) {
        return false;
      }
      if (toPredicate && !toPredicate(order.created_at)) {
        return false;
      }
      if (supplierFilter && !order.supplier.toLowerCase().includes(supplierFilter)) {
        return false;
      }
      if (!lowerQuery) {
        return true;
      }
      const haystack = [
        order.supplier,
        order.notes ?? "",
        order.id.toString(),
        ...order.items.map((item) => deviceLookup.get(item.device_id)?.sku ?? ""),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(lowerQuery);
    });
  }, [deviceLookup, filters.dateFrom, filters.dateTo, filters.query, filters.status, filters.supplier, orders]);

  const rows = useMemo<EnrichedRow[]>(
    () => filteredOrders.map((order) => mapOrderToRow(order, deviceLookup)),
    [deviceLookup, filteredOrders],
  );

  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));

  useEffect(() => {
    setPage((current) => Math.min(current, pages));
  }, [pages]);

  const paginatedRows = useMemo(
    () => rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [rows, page],
  );

  const summaryItems = useMemo<SummaryCard[]>(() => buildSummaryCards(rows), [rows]);

  const handleFiltersChange = (next: PurchaseOrderFilters) => {
    setFilters(next);
    setPage(1);
  };

  const handleImportSubmit = async (file: File) => {
    if (!selectedStoreId) {
      setError("Selecciona una sucursal para importar órdenes de compra.");
      return;
    }
    const reason = window.prompt(
      "Motivo corporativo para importar órdenes (mínimo 5 caracteres)",
      "Importación masiva de órdenes",
    );
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo válido.");
      return;
    }
    try {
      setImporting(true);
      setMessage(null);
      setError(null);
      const response = await importPurchaseOrdersCsv(token, file, reason.trim());
      setMessage(`Importación completada: ${response.imported} orden(es).`);
      if (response.errors.length > 0) {
        setError(response.errors.join(" · "));
      }
      pushToast?.({ message: "Importación de órdenes completada", variant: "success" });
      await loadOrders();
    } catch (err) {
      const friendly =
        err instanceof Error ? err.message : "No fue posible importar las órdenes de compra.";
      setError(friendly);
      setDashError(friendly);
    } finally {
      setImporting(false);
      setImportOpen(false);
    }
  };

  const handleExport = useCallback(() => {
    setError(null);
    setMessage(null);
    try {
      setExporting(true);
      const header = "id,fecha,proveedor,estado,articulos,monto_total,monto_recibido";
      const csvRows = rows.map((row) =>
        [
          row.id,
          row.date,
          row.supplier?.replace(/\s+/g, " ") ?? "",
          row.statusLabel,
          String(row.itemsCount),
          row.total.toFixed(2),
          row.received.toFixed(2),
        ].join(","),
      );
      const csvContent = [header, ...csvRows].join("\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      const stamp = new Date().toISOString().slice(0, 10);
      anchor.download = `ordenes_compra_${stamp}.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 2000);
      setMessage("Archivo de órdenes exportado correctamente.");
      pushToast?.({ message: "Exportación generada", variant: "success" });
    } catch (err) {
      const friendly =
        err instanceof Error
          ? err.message
          : "No fue posible generar el archivo de exportación.";
      setError(friendly);
      setDashError(friendly);
    } finally {
      setExporting(false);
      setExportOpen(false);
    }
  }, [rows, pushToast, setDashError]);

  const handleRowClick = (row: PurchaseOrderListRow) => {
    const match = rows.find((candidate) => candidate.id === row.id);
    if (match) {
      setActiveRow(match);
    }
  };

  const handleCloseMessage = () => setMessage(null);
  const handleDismissError = () => setError(null);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {error ? (
        <div role="alert" style={errorBoxStyle}>
          <span>{error}</span>
          <button
            type="button"
            onClick={handleDismissError}
            style={{ padding: "6px 10px", borderRadius: 8 }}
          >
            Cerrar
          </button>
        </div>
      ) : null}

      {message ? (
        <div role="status" style={messageBoxStyle}>
          <span>{message}</span>
          <button
            type="button"
            onClick={handleCloseMessage}
            style={{ padding: "6px 10px", borderRadius: 8 }}
          >
            Cerrar
          </button>
        </div>
      ) : null}

      <POSummaryCards items={summaryItems} />

      <POFiltersBar value={filters} onChange={handleFiltersChange} />

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
        <button
          type="button"
          onClick={() => setImportOpen(true)}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid rgba(59, 130, 246, 0.4)",
            background: "rgba(37, 99, 235, 0.14)",
            color: "#bfdbfe",
          }}
        >
          Importar
        </button>
        <button
          type="button"
          onClick={() => setExportOpen(true)}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid rgba(148, 163, 184, 0.4)",
            background: "rgba(148, 163, 184, 0.14)",
            color: "#e5e7eb",
          }}
        >
          Exportar
        </button>
      </div>

      <POTable
        rows={paginatedRows}
        loading={loading}
        onRowClick={handleRowClick}
      />

      <POSidePanel
        row={activeRow ? { ...activeRow, statusLabel: activeRow.statusLabel } : null}
        onClose={() => setActiveRow(null)}
      />

      <POPagination page={page} pages={pages} onPage={setPage} />

      <POImportModal
        open={importOpen}
        loading={importing}
        onClose={() => setImportOpen(false)}
        onSubmit={handleImportSubmit}
      />

      <POExportModal
        open={exportOpen}
        loading={exporting}
        onClose={() => setExportOpen(false)}
        onExport={handleExport}
      />
    </div>
  );
}

export default PurchaseListPage;
