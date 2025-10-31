import React from "react";
import type { MovementRow } from "./Table";

type Props = {
  row?: MovementRow | null;
  onClose?: () => void;
};

export default function SidePanel({ row, onClose }: Props) {
  if (!row) return null;
  const fields = [
    ["Fecha", row.date],
    ["Tipo", row.type],
    ["Producto", row.product],
    ["SKU", row.sku || "-"],
    ["Cantidad", String(row.qty)],
    ["De", row.fromStore || "-"],
    ["A", row.toStore || "-"],
    ["Referencia", row.reference || "-"],
    ["Usuario", row.user || "-"],
    ["Nota", row.note || "-"],
  ];
  return (
    <aside
      style={{
        position: "fixed",
        right: 0,
        top: 0,
        bottom: 0,
        width: 420,
        background: "#0b1220",
        borderLeft: "1px solid rgba(255,255,255,0.08)",
        padding: 16,
        overflow: "auto",
        zIndex: 40,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Detalle movimiento</h3>
        <button onClick={onClose} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Cerrar
        </button>
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        {fields.map(([k, v]) => (
          <div
            key={k}
            style={{
              display: "flex",
              justifyContent: "space-between",
              borderBottom: "1px dashed rgba(255,255,255,0.08)",
              padding: "6px 0",
            }}
          >
            <span style={{ color: "#94a3b8" }}>{k}</span>
            <span>{v as string}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
