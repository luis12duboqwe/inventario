import React from "react";
// [PACK23-QUOTES-DETAIL-IMPORTS-START]
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { SalesQuotes } from "../../../services/sales";
import type { Quote, QuoteCreate } from "../../../services/sales";
import { linesToTable } from "../utils/adapters";
// [PACK23-QUOTES-DETAIL-IMPORTS-END]
import { QuoteEditor } from "../components/quotes";
import { Table } from "../components/common";
// [PACK26-QUOTES-PERMS-START]
import { useAuthz, PERMS, RequirePerm } from "../../../auth/useAuthz";
import { logUI } from "../../../services/audit";
// [PACK26-QUOTES-PERMS-END]

type QuoteValue = {
  customer?: string;
  note?: string;
  lines: { id: string; name: string; qty: number; price: number }[];
};

const lineColumns = [
  { key: "name", label: "Producto" },
  { key: "qty", label: "Cantidad", align: "center" as const },
  { key: "price", label: "Precio", align: "right" as const },
  { key: "discount", label: "Descuento", align: "center" as const },
  { key: "total", label: "Total", align: "right" as const },
];

function formatCurrency(value?: number) {
  if (typeof value !== "number") return "—";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(value);
}

export function QuoteDetailPage() {
  const { can, user } = useAuthz();
  // [PACK26-QUOTES-DETAIL-GUARD-START]
  if (!can(PERMS.QUOTE_LIST)) {
    return <div>No autorizado</div>;
  }
  // [PACK26-QUOTES-DETAIL-GUARD-END]
  // [PACK23-QUOTES-DETAIL-STATE-START]
  const { id } = useParams();
  const [data, setData] = useState<Quote | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  // [PACK23-QUOTES-DETAIL-STATE-END]
  const [converting, setConverting] = useState(false);
  const [value, setValue] = useState<QuoteValue>({ lines: [] });

  // [PACK23-QUOTES-DETAIL-FETCH-START]
  async function load() {
    if (!id) return;
    setLoading(true);
    try { setData(await SalesQuotes.getQuote(id)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [id]);
  // [PACK23-QUOTES-DETAIL-FETCH-END]

  useEffect(() => {
    if (!data) return;
    setValue({
      customer: data.customerName ?? "",
      note: data.note ?? "",
      lines: (data.lines || []).map((line) => ({
        id: String(line.productId),
        name: line.name ?? String(line.productId),
        qty: line.qty,
        price: line.price,
      })),
    });
  }, [data]);

  // [PACK23-QUOTES-DETAIL-ACTIONS-START]
  async function onSave(partial: Partial<QuoteCreate>) {
    if (!id) return;
    if (!can(PERMS.QUOTE_EDIT)) return;
    setSaving(true);
    try { const updated = await SalesQuotes.updateQuote(id, partial); setData(updated); }
    finally { setSaving(false); }
  }

  async function onConvert() {
    if (!id) return;
    if (!can(PERMS.QUOTE_CONVERT)) return;
    setConverting(true);
    try {
      const r = await SalesQuotes.convertQuoteToSale(id);
      await logUI({ ts: Date.now(), userId: user?.id, module: "QUOTES", action: "convert", entityId: id });
      // Opcional: abrir ticket r.printable o navegar a ventas
      // window.open(r.printable?.pdfUrl ?? "", "_blank");
      // [PACK23-PRINT-START]
      // if (r.printable?.pdfUrl) window.open(r.printable.pdfUrl, "_blank");
      // else if (r.printable?.html) openPrintablePreview(r.printable.html); // TODO implementar modal
      // [PACK23-PRINT-END]
      await load();
      return r;
    } finally {
      setConverting(false);
    }
  }
  // [PACK23-QUOTES-DETAIL-ACTIONS-END]

  const canSave = !loading && !saving && Boolean(data);
  const lineRows = linesToTable(data?.lines || []);
  const totals = data?.totals;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "grid", gap: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>Cotización #{data?.number ?? "—"}</h2>
          <span style={{ color: "#9ca3af" }}>{data ? new Date(data.date).toLocaleString() : loading ? "Cargando…" : "—"}</span>
        </div>
        <QuoteEditor value={value} onChange={setValue} />
      </div>
      <div>
        <h3 style={{ marginBottom: 8 }}>Líneas</h3>
        <Table cols={lineColumns} rows={lineRows} />
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, alignItems: "center" }}>
        <div style={{ marginRight: "auto", color: "#9ca3af" }}>
          Total: <strong>{formatCurrency(totals?.grand)}</strong>
        </div>
        <RequirePerm perm={PERMS.QUOTE_EDIT} fallback={null}>
          <button
            style={{ padding: "8px 12px", borderRadius: 8 }}
            disabled={!canSave}
            onClick={async () => {
              if (!data) return;
              const mappedLines = (data.lines || []).map((line) => {
                const updated = value.lines.find((item) => item.id === String(line.productId));
                if (!updated) return line;
                return {
                  ...line,
                  name: updated.name,
                  qty: updated.qty,
                  price: updated.price,
                };
              });
              await onSave({
                note: value.note,
                customerName: value.customer,
                lines: mappedLines,
              });
            }}
          >
            {saving ? "Guardando…" : "Guardar"}
          </button>
        </RequirePerm>
        <RequirePerm perm={PERMS.QUOTE_CONVERT} fallback={null}>
          <button
            style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
            disabled={loading || converting}
            onClick={onConvert}
          >
            {converting ? "Convirtiendo…" : "Convertir a venta"}
          </button>
        </RequirePerm>
      </div>
    </div>
  );
}
