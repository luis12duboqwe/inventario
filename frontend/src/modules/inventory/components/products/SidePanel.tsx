import React from "react";
import type { ProductRow } from "./Table";

type Props = {
  row?: ProductRow | null;
  onClose?: () => void;
};

export default function SidePanel({ row, onClose }: Props) {
  if (!row) return null;
  const fields = [
    ["SKU", row.sku],
    ["Nombre", row.name],
    ["Marca", row.brand || "-"],
    ["Categoría", row.category || "-"],
    ["Sucursal", row.store || "-"],
    ["Stock", String(row.stock)],
    ["Precio", String(row.price)],
    ["Estado", row.status || "-"],
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
        <h3 style={{ margin: 0 }}>Detalle producto</h3>
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
