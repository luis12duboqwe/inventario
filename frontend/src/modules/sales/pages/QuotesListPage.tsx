import React from "react";
// [PACK23-QUOTES-LIST-IMPORTS-START]
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { SalesQuotes } from "../../../services/sales";
import type { Quote, QuoteListParams } from "../../../services/sales";
// [PACK23-QUOTES-LIST-IMPORTS-END]
import { FiltersBar, SidePanel, SummaryCards, Table } from "../components/common";
// [PACK26-LIST-PERMS-START]
import { useAuthz, PERMS } from "../../../auth/useAuthz";
// [PACK26-LIST-PERMS-END]
// [PACK27-INJECT-EXPORT-QUOTES-START]
import ExportDropdown from "@/components/ExportDropdown";
// [PACK27-INJECT-EXPORT-QUOTES-END]
// [PACK25-SKELETON-USE-START]
import { Skeleton } from "@components/ui/Skeleton";
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
  return new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" }).format(value);
}

function formatDate(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
}

export function QuotesListPage() {
  const { can } = useAuthz();
  const canList = can(PERMS.QUOTE_LIST);
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
  const fetchQuotes = useCallback(
    async (extra?: Partial<QuoteListParams>) => {
      if (!canList) {
        setItems([]);
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const baseParams: QuoteListParams = {
          page,
          pageSize,
          q,
        };
        if (status) {
          baseParams.status = status;
        }
        const mergedParams = { ...baseParams, ...extra };
        const res = await SalesQuotes.listQuotes(mergedParams);
        setItems(res.items || []);
        setTotal(res.total || 0);
      } finally {
        setLoading(false);
      }
    },
    [canList, page, pageSize, q, status],
  );

  useEffect(() => {
    void fetchQuotes();
  }, [fetchQuotes]);
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
  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    fetchQuotes({ page: 1 });
  }
  function onStatusChange(s: Quote["status"] | undefined) {
    setStatus(s);
    setPage(1);
    const params: Partial<QuoteListParams> = { page: 1 };
    if (s) {
      params.status = s;
    }
    fetchQuotes(params);
  }
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
        actions: (
          <Link to={`/sales/quotes/${quote.id}`} className="sales-link-action">
            Ver
          </Link>
        ),
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

  // [PACK26-QUOTES-GUARD-START]
  if (!canList) {
    return <div>No autorizado</div>;
  }
  // [PACK26-QUOTES-GUARD-END]

  return (
    <div data-testid="quotes-list" className="quotes-list-container">
      <SummaryCards
        items={[
          { label: "Cotizaciones", value: loading ? "Cargando…" : total.toString() },
          {
            label: "Abiertas",
            value: items.filter((item) => item.status === "OPEN").length.toString(),
          },
          {
            label: "Convertidas",
            value: items.filter((item) => item.status === "CONVERTED").length.toString(),
          },
        ]}
      />
      <div className="quotes-list-filters-container">
        <form onSubmit={onSearch} className="quotes-list-form">
          <FiltersBar>
            <input
              placeholder="#Q/Cliente"
              value={q}
              onChange={(event) => setQ(event.target.value)}
              className="quotes-list-input"
            />
            <select
              value={status ?? ""}
              onChange={(event) =>
                onStatusChange(
                  event.target.value ? (event.target.value as Quote["status"]) : undefined,
                )
              }
              className="quotes-list-input"
            >
              {statusOptions.map((option) => (
                <option key={option.label} value={option.value ?? ""}>
                  {option.label}
                </option>
              ))}
            </select>
            <button type="submit" className="quotes-list-btn-search" disabled={loading}>
              Buscar
            </button>
          </FiltersBar>
        </form>
        <ExportDropdown entity="quotes" currentItems={items} />
      </div>
      {pendingOffline > 0 ? (
        <div className="quotes-list-offline-bar">
          <span className="quotes-list-offline-text">Pendientes offline: {pendingOffline}</span>
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
            className="quotes-list-offline-btn"
          >
            {flushing ? "Reintentando…" : "Reintentar pendientes"}
          </button>
        </div>
      ) : null}
      {flushMessage ? <div className="quotes-list-flush-message">{flushMessage}</div> : null}
      {loading ? (
        <Skeleton lines={10} />
      ) : (
        <Table cols={columns} rows={rows} onRowClick={handleRowSelect} />
      )}
      <div className="quotes-list-pagination">
        <span className="quotes-list-pagination-info">
          Página {page} de {pages}
        </span>
        <div className="quotes-list-pagination-actions">
          <button
            type="button"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={loading || page <= 1}
            className="quotes-list-btn-page"
          >
            Anterior
          </button>
          <button
            type="button"
            onClick={() => setPage((current) => (current < pages ? current + 1 : current))}
            disabled={loading || page >= pages}
            className="quotes-list-btn-page"
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

export default QuotesListPage;
