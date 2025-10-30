import React from "react";
// [PACK23-RETURNS-LIST-IMPORTS-START]
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { SalesReturns } from "../../../services/sales";
import type { ReturnDoc, ReturnListParams } from "../../../services/sales";
// [PACK23-RETURNS-LIST-IMPORTS-END]
import { FiltersBar, SidePanel, SummaryCards, Table } from "../components/common";
// [PACK26-RETURNS-PERMS-START]
import { useAuthz, PERMS } from "../../../auth/useAuthz";
// [PACK26-RETURNS-PERMS-END]

type ReturnRow = {
  id: string;
  date: string;
  number: string;
  reason: string;
  items: number;
  total: string;
  actions: React.ReactNode;
};

const columns = [
  { key: "date", label: "Fecha" },
  { key: "number", label: "#RET" },
  { key: "reason", label: "Motivo" },
  { key: "items", label: "Ítems", align: "center" as const },
  { key: "total", label: "Crédito", align: "right" as const },
  { key: "actions", label: "Acciones", align: "center" as const },
];

const reasonLabels: Record<ReturnDoc["reason"], string> = {
  DEFECT: "Defecto",
  BUYER_REMORSE: "Remordimiento",
  WARRANTY: "Garantía",
  OTHER: "Otro",
};

function formatCurrency(value?: number) {
  if (typeof value !== "number") return "—";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(value);
}

function formatDate(value?: string) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString();
}

export function ReturnsListPage() {
  const { can } = useAuthz();
  const canList = can(PERMS.RETURN_LIST);
  // [PACK23-RETURNS-LIST-STATE-START]
  const [items, setItems] = useState<ReturnDoc[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [q, setQ] = useState("");
  const [reason, setReason] = useState<ReturnDoc["reason"] | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  // [PACK23-RETURNS-LIST-STATE-END]
  const [selectedRow, setSelectedRow] = useState<ReturnDoc | null>(null);

  // [PACK23-RETURNS-LIST-FETCH-START]
  async function fetchReturns(extra?: Partial<ReturnListParams>) {
    if (!canList) {
      setItems([]);
      setTotal(0);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await SalesReturns.listReturns({ page, pageSize, q, reason, ...extra });
      setItems(res.items || []);
      setTotal(res.total || 0);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { fetchReturns(); }, [page, pageSize, reason, canList]);
  // [PACK23-RETURNS-LIST-FETCH-END]

  const rows: ReturnRow[] = items.map((doc) => ({
    id: String(doc.id),
    date: formatDate(doc.date),
    number: doc.number,
    reason: reasonLabels[doc.reason] ?? doc.reason,
    items: doc.lines?.length ?? 0,
    total: formatCurrency(doc.totalCredit),
    actions: <Link to={`/sales/returns/${doc.id}`} style={{ color: "#38bdf8" }}>Ver</Link>,
  }));

  const creditTotal = items.reduce((sum, item) => sum + (item.totalCredit || 0), 0);
  const pages = Math.max(1, Math.ceil(total / pageSize) || 1);

  // [PACK26-RETURNS-GUARD-START]
  if (!canList) {
    return <div>No autorizado</div>;
  }
  // [PACK26-RETURNS-GUARD-END]

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <SummaryCards
        items={[
          { label: "Devoluciones", value: loading ? "Cargando…" : total.toString() },
          { label: "Crédito listado", value: formatCurrency(creditTotal) },
        ]}
      />
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          fetchReturns({ page: 1 });
        }}
      >
        <FiltersBar>
          <input
            placeholder="#RET/Cliente/IMEI"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
          />
          <select
            value={reason ?? ""}
            onChange={(event) => {
              const value = event.target.value as ReturnDoc["reason"] | "";
              setPage(1);
              setReason(value ? (value as ReturnDoc["reason"]) : undefined);
            }}
            style={{ padding: 8, borderRadius: 8 }}
          >
            <option value="">Todos los motivos</option>
            {Object.entries(reasonLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
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
      <Table
        cols={columns}
        rows={rows}
        onRowClick={(row) => {
          const rowId = String((row as ReturnRow).id ?? "");
          const found = items.find((item) => String(item.id) === rowId);
          setSelectedRow(found ?? null);
        }}
      />
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
        title="Devolución"
        rows={
          selectedRow
            ? [
                ["Fecha", formatDate(selectedRow.date)],
                ["#RET", selectedRow.number],
                ["Motivo", reasonLabels[selectedRow.reason] ?? selectedRow.reason],
                ["Crédito", formatCurrency(selectedRow.totalCredit)],
              ]
            : []
        }
        onClose={() => setSelectedRow(null)}
      />
    </div>
  );
}
