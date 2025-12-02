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
    <aside className="orders-side-panel">
      <div className="orders-side-panel-header">
        <h3 className="orders-side-panel-title">Resumen orden</h3>
        <button onClick={onClose} className="orders-side-panel-close-btn">
          Cerrar
        </button>
      </div>
      <div className="orders-side-panel-status">
        <StatusBadge value={row.status} />
      </div>
      <div className="orders-side-panel-fields">
        {fields.map(([label, value]) => (
          <div key={label} className="orders-side-panel-field-row">
            <span className="orders-side-panel-field-label">{label}</span>
            <span>{value}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}

export default SidePanel;
