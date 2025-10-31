import React from "react";

import StatusBadge from "./StatusBadge";
import type { OrderRow } from "./Table";

type Props = {
  row?: OrderRow | null;
  onClose?: () => void;
};

function SidePanel({ row, onClose }: Props) {
  if (!row) {
    return null;
  }

  const fields: [string, string][] = [
    ["Fecha", row.date],
    ["Factura #", row.number || "-"],
    ["Cliente", row.customer],
    ["Items", String(row.itemsCount)],
    ["Total", Intl.NumberFormat().format(row.total)],
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
        borderLeft: "1px solid rgba(255, 255, 255, 0.08)",
        padding: 16,
        overflow: "auto",
        zIndex: 40,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Resumen orden</h3>
        <button onClick={onClose} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Cerrar
        </button>
      </div>
      <div style={{ marginBottom: 8 }}>
        <StatusBadge value={row.status} />
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        {fields.map(([label, value]) => (
          <div
            key={label}
            style={{
              display: "flex",
              justifyContent: "space-between",
              borderBottom: "1px dashed rgba(255, 255, 255, 0.08)",
              padding: "6px 0",
            }}
          >
            <span style={{ color: "#94a3b8" }}>{label}</span>
            <span>{value}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}

export default SidePanel;
