import React from "react";
// [PACK23-QUOTES-LIST-IMPORTS-START]
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { SalesQuotes } from "../../../services/sales";
import type { Quote, QuoteListParams } from "../../../services/sales";
// [PACK23-QUOTES-LIST-IMPORTS-END]
import { FiltersBar, SidePanel, SummaryCards, Table } from "../components/common";
// [PACK25-SKELETON-USE-START]
import { Skeleton } from "@/ui/Skeleton";
// [PACK25-SKELETON-USE-END]
import { readQueue } from "@/services/offline";
import { flushOffline } from "../utils/offline";

const columns = [
  { key: "date", label: "Fecha" },
  { key: "number", label: "#Q" },
  { key: "customer", label: "Cliente" },
  { key: "items", label: "Ítems", align: "center" as const },
  { key: "total", label: "Total", align: "right" as const },
  { key: "status", label: "Estado" },
];
// [PACK23-QUOTES-LIST-COLUMNS-START]
columns.push({ key: "actions", label: "Acciones", align: "center" as const });
// [PACK23-QUOTES-LIST-COLUMNS-END]

type QuoteRow = {
  id: string;
  date: string;
  number: string;
  customer: string;
  items: number;
  total: string;
  status: string;
  actions: React.ReactNode;
};

const statusLabels: Record<Quote["status"], string> = {
  OPEN: "Abierta",
  APPROVED: "Aprobada",
  EXPIRED: "Expirada",
  CONVERTED: "Convertida",
};

function formatCurrency(value?: number) {
  if (typeof value !== "number") return "—";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(value);
}

function formatDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
}

export function QuotesListPage() {
  // [PACK23-QUOTES-LIST-STATE-START]
  const [items, setItems] = useState<Quote[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<Quote["status"] | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  // [PACK23-QUOTES-LIST-STATE-END]
  const [selectedRow, setSelectedRow] = useState<Quote | null>(null);
  const [pendingOffline, setPendingOffline] = useState(0);
  const [flushing, setFlushing] = useState(false);
  const [flushMessage, setFlushMessage] = useState<string | null>(null);

  // [PACK23-QUOTES-LIST-FETCH-START]
  async function fetchQuotes(extra?: Partial<QuoteListParams>) {
    setLoading(true);
    try {
      const res = await SalesQuotes.listQuotes({ page, pageSize, q, status, ...extra });
      setItems(res.items || []);
      setTotal(res.total || 0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchQuotes(); }, [page, pageSize, status]);
  // [PACK23-QUOTES-LIST-FETCH-END]

  useEffect(() => {
    if (typeof window === "undefined") return;
    setPendingOffline(readQueue().length);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setPendingOffline(readQueue().length);
  }, [items]);

  // [PACK23-QUOTES-LIST-UI-START]
  function onSearch(e: React.FormEvent) { e.preventDefault(); setPage(1); fetchQuotes({ page: 1 }); }
  function onStatusChange(s: Quote["status"] | undefined) { setStatus(s); setPage(1); fetchQuotes({ page: 1, status: s }); }
  // [PACK23-QUOTES-LIST-UI-END]

  const rows: QuoteRow[] = useMemo(
    () =>
      items.map((quote) => ({
        id: String(quote.id),
        date: formatDate(quote.date),
        number: quote.number,
        customer: quote.customerName ?? "—",
        items: quote.lines?.length ?? 0,
        total: formatCurrency(quote.totals?.grand),
        status: statusLabels[quote.status] ?? quote.status,
        actions: <Link to={`/sales/quotes/${quote.id}`} style={{ color: "#38bdf8" }}>Ver</Link>,
      })),
    [items],
  );

  const handleRowSelect = useCallback(
    (row: QuoteRow | Record<string, unknown>) => {
      const rowId = String((row as QuoteRow).id ?? "");
      const found = items.find((item) => String(item.id) === rowId);
      setSelectedRow(found ?? null);
    },
    [items],
  );

  const pages = Math.max(1, Math.ceil(total / pageSize) || 1);
  const statusOptions: Array<{ value: Quote["status"] | undefined; label: string }> = [
    { value: undefined, label: "Todos" },
    { value: "OPEN", label: statusLabels.OPEN },
    { value: "APPROVED", label: statusLabels.APPROVED },
    { value: "EXPIRED", label: statusLabels.EXPIRED },
    { value: "CONVERTED", label: statusLabels.CONVERTED },
  ];

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <SummaryCards
        items={[
          { label: "Cotizaciones", value: loading ? "Cargando…" : total.toString() },
          { label: "Abiertas", value: items.filter((item) => item.status === "OPEN").length.toString() },
          { label: "Convertidas", value: items.filter((item) => item.status === "CONVERTED").length.toString() },
        ]}
      />
      <form onSubmit={onSearch}>
        <FiltersBar>
          <input
            placeholder="#Q/Cliente"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
          />
          <select
            value={status ?? ""}
            onChange={(event) => onStatusChange(event.target.value ? (event.target.value as Quote["status"]) : undefined)}
            style={{ padding: 8, borderRadius: 8 }}
          >
            {statusOptions.map((option) => (
              <option key={option.label} value={option.value ?? ""}>
                {option.label}
              </option>
            ))}
          </select>
          <button
            type="submit"
            style={{ padding: "8px 16px", borderRadius: 8, background: "#38bdf8", color: "#0f172a", border: "none" }}
            disabled={loading}
          >
            Buscar
          </button>
        </FiltersBar>
      </form>
      {pendingOffline > 0 ? (
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ color: "#fbbf24" }}>Pendientes offline: {pendingOffline}</span>
          <button
            type="button"
            onClick={async () => {
              setFlushing(true);
              try {
                const result = await flushOffline();
                setPendingOffline(result.pending);
                setFlushMessage(`Reintentadas: ${result.flushed}. Pendientes: ${result.pending}.`);
              } catch {
                setFlushMessage("No fue posible sincronizar. Intenta nuevamente.");
              } finally {
                setFlushing(false);
              }
            }}
            disabled={flushing}
            style={{ padding: "6px 12px", borderRadius: 8, border: "none", background: "rgba(56,189,248,0.16)", color: "#e0f2fe" }}
          >
            {flushing ? "Reintentando…" : "Reintentar pendientes"}
          </button>
        </div>
      ) : null}
      {flushMessage ? <div style={{ color: "#9ca3af", fontSize: 12 }}>{flushMessage}</div> : null}
      {loading ? (
        <Skeleton lines={10} />
      ) : (
        <Table
          cols={columns}
          rows={rows}
          onRowClick={handleRowSelect}
        />
      )}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ color: "#9ca3af" }}>
          Página {page} de {pages}
        </span>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={loading || page <= 1}
            style={{ padding: "6px 12px", borderRadius: 8, background: "rgba(56,189,248,0.12)", color: "#e0f2fe", border: "none" }}
          >
            Anterior
          </button>
          <button
            type="button"
            onClick={() => setPage((current) => (current < pages ? current + 1 : current))}
            disabled={loading || page >= pages}
            style={{ padding: "6px 12px", borderRadius: 8, background: "rgba(56,189,248,0.12)", color: "#e0f2fe", border: "none" }}
          >
            Siguiente
          </button>
        </div>
      </div>
      <SidePanel
        title="Cotización"
        rows={
          selectedRow
            ? [
                ["Fecha", formatDate(selectedRow.date)],
                ["#Q", selectedRow.number],
                ["Cliente", selectedRow.customerName ?? "—"],
                ["Estado", statusLabels[selectedRow.status] ?? selectedRow.status],
                ["Total", formatCurrency(selectedRow.totals?.grand)],
                ["Nota", selectedRow.note ?? "—"],
              ]
            : []
        }
        onClose={() => setSelectedRow(null)}
      />
    </div>
  );
}
