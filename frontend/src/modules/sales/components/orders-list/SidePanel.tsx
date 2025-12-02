import React from "react";

import ChannelBadge from "./ChannelBadge";
import PaymentStatusBadge from "./PaymentStatusBadge";
import StatusBadge from "./StatusBadge";
import type { OrderRow } from "./Table";

export type OrdersSidePanelProps = {
  row?: OrderRow | null;
  onClose?: () => void;
};

const numberFormatter = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

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
    <aside className="orders-list-side-panel">
      <div className="orders-list-side-panel-header">
        <h3 className="orders-list-side-panel-title">Resumen pedido</h3>
        <button onClick={onClose} className="orders-list-side-panel-close-btn">
          Cerrar
        </button>
      </div>
      <div className="orders-list-side-panel-badges">
        <PaymentStatusBadge value={row.paymentStatus} />
        <StatusBadge value={row.status} />
        <ChannelBadge value={row.channel} />
      </div>
      <div className="orders-list-side-panel-fields">
        {fields.map(([label, value]) => (
          <div key={label} className="orders-list-side-panel-field-row">
            <span className="orders-list-side-panel-field-label">{label}</span>
            <span>{value}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}

export default SidePanel;
