import React from "react";

import ChannelBadge from "./ChannelBadge";
import PaymentStatusBadge from "./PaymentStatusBadge";
import StatusBadge from "./StatusBadge";
import type { OrderRow } from "./Table";

export type OrdersSidePanelProps = {
  row?: OrderRow | null;
  onClose?: () => void;
};

const numberFormatter = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function SidePanel({ row, onClose }: OrdersSidePanelProps) {
  if (!row) {
    return null;
  }

  const fields: Array<[string, string]> = [
    ["Fecha", row.date],
    ["# Pedido", row.number ?? "-"],
    ["Cliente", row.customer ?? "—"],
    ["Items", String(row.itemsCount)],
    ["Total", numberFormatter.format(row.total)],
    ["Pagado", numberFormatter.format(row.paid)],
    ["Canal", row.channel],
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
        zIndex: 58,
        display: "grid",
        gap: 12,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>Resumen pedido</h3>
        <button onClick={onClose} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Cerrar
        </button>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <PaymentStatusBadge value={row.paymentStatus} />
        <StatusBadge value={row.status} />
        <ChannelBadge value={row.channel} />
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
