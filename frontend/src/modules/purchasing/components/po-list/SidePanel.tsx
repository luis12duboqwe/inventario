import React from "react";

type Row = {
  id: string;
  date: string;
  number?: string;
  supplier?: string;
  itemsCount: number;
  total: number;
  received: number;
  status: string;
  statusLabel?: string;
};

type Props = {
  row?: Row | null;
  onClose?: () => void;
};

const containerStyle: React.CSSProperties = {
  position: "fixed",
  right: 0,
  top: 0,
  bottom: 0,
  width: 420,
  background: "#0b1220",
  borderLeft: "1px solid rgba(255, 255, 255, 0.08)",
  padding: 16,
  overflow: "auto",
  boxShadow: "-6px 0 12px rgba(15, 23, 42, 0.4)",
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 8,
};

const closeButtonStyle: React.CSSProperties = {
  padding: "6px 10px",
  borderRadius: 8,
  background: "rgba(51, 65, 85, 0.6)",
  color: "#e5e7eb",
  border: "1px solid rgba(148, 163, 184, 0.4)",
};

const currencyFormatter = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
});

export default function SidePanel({ row, onClose }: Props) {
  if (!row) {
    return null;
  }

  const fields: [string, string][] = [
    ["Fecha", row.date],
    ["#PO", row.number || "—"],
    ["Proveedor", row.supplier || "—"],
    ["Items", String(row.itemsCount)],
    ["Total", currencyFormatter.format(row.total)],
    ["Recibido", currencyFormatter.format(row.received)],
    ["Estado", row.statusLabel || row.status],
  ];

  return (
    <aside style={containerStyle}>
      <div style={headerStyle}>
        <h3 style={{ margin: 0 }}>Resumen PO</h3>
        <button type="button" onClick={onClose} style={closeButtonStyle}>
          Cerrar
        </button>
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
