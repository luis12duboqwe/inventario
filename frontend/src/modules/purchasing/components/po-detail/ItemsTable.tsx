import React from "react";

type Item = {
  id: string;
  sku?: string;
  name: string;
  qty: number;
  received: number;
  unitCost: number;
  subtotal: number;
};

type Props = {
  items?: Item[];
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

export default function ItemsTable({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div style={{ padding: 12, color: "#9ca3af" }}>Sin items</div>;
  }

  return (
    <div style={wrapperStyle}>
      <table style={tableStyle}>
        <thead>
          <tr style={{ background: "rgba(255, 255, 255, 0.03)" }}>
            <th style={headerCellStyle}>SKU</th>
            <th style={headerCellStyle}>Producto</th>
            <th style={{ ...headerCellStyle, textAlign: "center" }}>Pedida</th>
            <th style={{ ...headerCellStyle, textAlign: "center" }}>Recibida</th>
            <th style={{ ...headerCellStyle, textAlign: "right" }}>Costo</th>
            <th style={{ ...headerCellStyle, textAlign: "right" }}>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr key={item.id}>
              <td style={bodyCellStyle}>{item.sku || "—"}</td>
              <td style={bodyCellStyle}>{item.name}</td>
              <td style={{ ...bodyCellStyle, textAlign: "center" }}>{item.qty}</td>
              <td style={{ ...bodyCellStyle, textAlign: "center" }}>{item.received}</td>
              <td style={{ ...bodyCellStyle, textAlign: "right" }}>
                {Intl.NumberFormat().format(item.unitCost)}
              </td>
              <td style={{ ...bodyCellStyle, textAlign: "right" }}>
                {Intl.NumberFormat().format(item.subtotal)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
