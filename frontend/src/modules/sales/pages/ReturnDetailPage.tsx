import React from "react";
// [PACK23-RETURNS-DETAIL-IMPORTS-START]
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { SalesReturns } from "../../../services/sales";
import type { ReturnDoc, ReturnCreate } from "../../../services/sales";
import { linesToTable } from "../utils/adapters";
// [PACK23-RETURNS-DETAIL-IMPORTS-END]
import { ReturnEditor } from "../components/returns";
import { Table } from "../components/common";

const lineColumns = [
  { key: "name", label: "Producto" },
  { key: "qty", label: "Cantidad", align: "center" as const },
  { key: "price", label: "Precio", align: "right" as const },
  { key: "discount", label: "Descuento", align: "center" as const },
  { key: "total", label: "Total", align: "right" as const },
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
  return parsed.toLocaleString();
}

export function ReturnDetailPage() {
  // [PACK23-RETURNS-DETAIL-STATE-START]
  const { id } = useParams(); // si no hay id -> modo crear
  const [data, setData] = useState<ReturnDoc | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  // [PACK23-RETURNS-DETAIL-STATE-END]

  // [PACK23-RETURNS-DETAIL-FETCH-START]
  useEffect(() => {
    (async () => {
      if (!id) return;
      setLoading(true);
      try { setData(await SalesReturns.getReturn(id)); }
      finally { setLoading(false); }
    })();
  }, [id]);
  // [PACK23-RETURNS-DETAIL-FETCH-END]

  // [PACK23-RETURNS-DETAIL-SAVE-START]
  async function onCreate(payload: ReturnCreate) {
    setSaving(true);
    try {
      const r = await SalesReturns.createReturn(payload);
      setData(r);
      // TODO: navegar a detalle r.id si tu router lo soporta
    } finally {
      setSaving(false);
    }
  }
  // [PACK23-RETURNS-DETAIL-SAVE-END]

  const isCreateMode = !id;
  const lineRows = linesToTable(
    (data?.lines || []).map((line) => ({
      productId: line.productId,
      name: line.name ?? String(line.productId),
      qty: line.qty,
      price: line.price,
    }))
  );

  return (
    <div style={{ display: "grid", gap: 16 }}>
        {isCreateMode ? (
          <>
            <ReturnEditor
              onSubmit={(payload) => {
                if (saving) return;
                const missingProduct = payload.lines.find((line) => !line.productId);
                if (missingProduct) {
                  window.alert(
                    "Selecciona un producto válido para cada línea antes de generar la devolución.",
                  );
                  return;
                }
                onCreate({
                  reason: payload.reason as ReturnDoc["reason"],
                  note: payload.note,
                  lines: payload.lines.map((line) => ({
                    productId: line.productId!,
                    name: line.name,
                    qty: line.qty,
                    price: line.price,
                    imei: line.imei,
                    restock: line.restock,
                  })),
                  ticketNumber: payload.lines[0]?.ticket,
                });
              }}
            />
          {data && (
            <div style={{ display: "grid", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h2 style={{ margin: 0 }}>Devolución #{data.number}</h2>
                <span style={{ color: "#9ca3af" }}>{formatDate(data.date)}</span>
              </div>
              <div style={{ display: "grid", gap: 4, color: "#9ca3af" }}>
                <span>
                  Motivo: <strong>{reasonLabels[data.reason] ?? data.reason}</strong>
                </span>
                <span>Crédito: <strong>{formatCurrency(data.totalCredit)}</strong></span>
              </div>
              <Table cols={lineColumns} rows={lineRows} />
            </div>
          )}
        </>
      ) : (
        <div style={{ display: "grid", gap: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ margin: 0 }}>Devolución #{data?.number ?? "—"}</h2>
            <span style={{ color: "#9ca3af" }}>
              {data ? formatDate(data.date) : loading ? "Cargando…" : "—"}
            </span>
          </div>
          <div style={{ display: "grid", gap: 4, color: "#9ca3af" }}>
            <span>
              Motivo: <strong>{data ? reasonLabels[data.reason] ?? data.reason : "—"}</strong>
            </span>
            <span>Crédito: <strong>{formatCurrency(data?.totalCredit)}</strong></span>
          </div>
          <Table cols={lineColumns} rows={lineRows} />
        </div>
      )}
    </div>
  );
}
