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
// [PACK27-PRINT-IMPORT-START]
import { openPrintable } from "@/lib/print";
// [PACK27-PRINT-IMPORT-END]

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
    setSaving(true);
    try { const updated = await SalesQuotes.updateQuote(id, partial); setData(updated); }
    finally { setSaving(false); }
  }

  async function onConvert() {
    if (!id) return;
    setConverting(true);
    try {
      const r = await SalesQuotes.convertQuoteToSale(id);
      // [PACK27-PRINT-QUOTE-CONVERT-START]
      if (r.printable) {
        openPrintable(r.printable, "factura");
      }
      // [PACK27-PRINT-QUOTE-CONVERT-END]
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
        {/* [PACK27-PRINT-BUTTON-START] */}
        <button
          style={{ padding: "8px 12px", borderRadius: 8, background: "#1f2937", color: "#e0f2fe", border: "1px solid #334155" }}
          onClick={() => openPrintable(data?.printable, "documento")}
          disabled={!data?.printable}
        >
          Imprimir
        </button>
        {/* [PACK27-PRINT-BUTTON-END] */}
        <button
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
          disabled={loading || converting}
          onClick={onConvert}
        >
          {converting ? "Convirtiendo…" : "Convertir a venta"}
        </button>
      </div>
    </div>
  );
}
