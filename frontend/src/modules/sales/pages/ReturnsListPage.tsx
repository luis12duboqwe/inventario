import React from "react";
// [PACK23-RETURNS-LIST-IMPORTS-START]
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { SalesReturns } from "../../../services/sales";
import type { ReturnDoc, ReturnListParams } from "../../../services/sales";
// [PACK23-RETURNS-LIST-IMPORTS-END]
import { FiltersBar, SidePanel, Table } from "../components/common";
// [PACK26-RETURNS-PERMS-START]
import { useAuthz, PERMS } from "../../../auth/useAuthz";
// [PACK26-RETURNS-PERMS-END]
// [PACK27-INJECT-EXPORT-RETURNS-START]
import ExportDropdown from "@/components/ExportDropdown";
// [PACK27-INJECT-EXPORT-RETURNS-END]
import { Skeleton } from "@components/ui/Skeleton";

type ReturnRow = {
  id: string;
  date: string;
  number: string;
  reason: string;
  items: number;
  total: string;
  actions: React.ReactNode;
};

function ReturnsListPage() {
  const { can } = useAuthz();
  const canList = can(PERMS.RETURN_LIST);
  const [items, setItems] = useState<ReturnDoc[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [q, setQ] = useState("");
  const [reason, setReason] = useState<ReturnDoc["reason"] | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [selectedRow, setSelectedRow] = useState<ReturnDoc | null>(null);

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
    EXCHANGE: "Cambio",
    WARRANTY: "Garantía",
    OTHER: "Otro",
    BUYER_REMORSE: "Remordimiento",
  };

  const rows: ReturnRow[] = items.map((doc) => ({
    id: String(doc.id),
    date: formatDate(doc.date),
    number: doc.number,
    reason: reasonLabels[doc.reason] ?? doc.reason,
    items: doc.lines?.length ?? 0,
    total: formatCurrency(doc.totalCredit),
    actions: (
      <Link to={`/sales/returns/${doc.id}`} className="sales-link-action">
        Ver
      </Link>
    ),
  }));

  const pages = Math.max(1, Math.ceil(total / pageSize) || 1);

  const fetchReturns = useCallback(
    async (extra?: Partial<ReturnListParams>) => {
      if (!canList) {
        setItems([]);
        setTotal(0);
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const baseParams: ReturnListParams = {
          page,
          pageSize,
          q,
        };
        if (reason) {
          baseParams.reason = reason;
        }
        const mergedParams = { ...baseParams, ...extra };
        const res = await SalesReturns.listReturns(mergedParams);
        setItems(res.items || []);
        setTotal(res.total || 0);
      } finally {
        setLoading(false);
      }
    },
    [canList, page, pageSize, q, reason],
  );
  useEffect(() => {
    void fetchReturns();
  }, [fetchReturns]);

  function formatDate(date: string) {
    return date;
  }
  function formatCurrency(value: number) {
    return String(value);
  }
  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    fetchReturns();
  }

  if (!canList) {
    return <div>No autorizado</div>;
  }

  return (
    <div data-testid="returns-list">
      <form onSubmit={onSearch} className="returns-list-form">
        <FiltersBar>
          <input
            placeholder="#RET/Cliente/IMEI"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            className="returns-list-input"
          />
          <select
            value={reason ?? ""}
            onChange={(event) => {
              const value = event.target.value as ReturnDoc["reason"] | "";
              setPage(1);
              setReason(value ? (value as ReturnDoc["reason"]) : undefined);
            }}
            className="returns-list-input"
          >
            <option value="">Todos los motivos</option>
            {Object.entries(reasonLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
          <button type="submit" className="returns-list-btn-search" disabled={loading}>
            Buscar
          </button>
        </FiltersBar>
      </form>
      <ExportDropdown entity="returns" currentItems={items} />
      {loading ? (
        <Skeleton lines={10} />
      ) : (
        <Table
          cols={columns}
          rows={rows}
          onRowClick={(row) => {
            const rowId = String((row as ReturnRow).id ?? "");
            const found = items.find((item) => String(item.id) === rowId);
            setSelectedRow(found ?? null);
          }}
        />
      )}
      <div className="returns-list-pagination">
        <span className="returns-list-pagination-info">
          Página {page} de {pages}
        </span>
        <div className="returns-list-pagination-actions">
          <button
            type="button"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={loading || page <= 1}
            className="returns-list-btn-page"
          >
            Anterior
          </button>
          <button
            type="button"
            onClick={() => setPage((current) => (current < pages ? current + 1 : current))}
            disabled={loading || page >= pages}
            className="returns-list-btn-page"
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
export default ReturnsListPage;
