import React from "react";

type PurchaseStatus = "DRAFT" | "SENT" | "PARTIAL" | "RECEIVED" | "CANCELLED";

type Row = {
  id: string;
  date: string;
  number?: string;
  supplier?: string;
  itemsCount: number;
  total: number;
  received: number;
  status: PurchaseStatus;
};

type Props = {
  rows?: Row[];
  loading?: boolean;
  onRowClick?: (row: Row) => void;
};

const wrapperStyle: React.CSSProperties = {
  overflow: "auto",
  borderRadius: 12,
  border: "1px solid rgba(255, 255, 255, 0.08)",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 14,
};

const headerCellStyle: React.CSSProperties = {
  padding: 10,
  background: "rgba(255, 255, 255, 0.03)",
  textAlign: "left",
  color: "#cbd5f5",
};

const bodyCellStyle: React.CSSProperties = {
  padding: 10,
  borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
};

export default function Table({ rows, loading, onRowClick }: Props) {
  const data = Array.isArray(rows) ? rows : [];

  if (loading) {
    return <div style={{ padding: 12 }}>Cargando…</div>;
  }

  if (data.length === 0) {
    return <div style={{ padding: 12, color: "#9ca3af" }}>Sin compras</div>;
  }

  return (
    <div style={wrapperStyle}>
      <table style={tableStyle}>
        <thead>
          <tr style={{ background: "rgba(255, 255, 255, 0.03)" }}>
            <th style={headerCellStyle}>Fecha</th>
            <th style={headerCellStyle}>#PO</th>
            <th style={headerCellStyle}>Proveedor</th>
            <th style={{ ...headerCellStyle, textAlign: "center" }}>Items</th>
            <th style={{ ...headerCellStyle, textAlign: "right" }}>Total</th>
            <th style={{ ...headerCellStyle, textAlign: "right" }}>Recibido</th>
            <th style={headerCellStyle}>Estado</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row)}
              style={{ cursor: onRowClick ? "pointer" : "default" }}
            >
              <td style={bodyCellStyle}>{row.date}</td>
              <td style={bodyCellStyle}>{row.number || "—"}</td>
              <td style={bodyCellStyle}>{row.supplier || "—"}</td>
              <td style={{ ...bodyCellStyle, textAlign: "center" }}>{row.itemsCount}</td>
              <td style={{ ...bodyCellStyle, textAlign: "right" }}>
                {Intl.NumberFormat().format(row.total)}
              </td>
              <td style={{ ...bodyCellStyle, textAlign: "right" }}>
                {Intl.NumberFormat().format(row.received)}
              </td>
              <td style={bodyCellStyle}>{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
