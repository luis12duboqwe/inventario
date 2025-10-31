import React from "react";

type Receipt = {
  id: string;
  date: string;
  user?: string;
  lines: number;
  qty: number;
  note?: string;
};

type Props = {
  items?: Receipt[];
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

export default function ReceiptsTable({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div style={{ padding: 12, color: "#9ca3af" }}>Sin recepciones</div>;
  }

  return (
    <div style={wrapperStyle}>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={headerCellStyle}>Fecha</th>
            <th style={headerCellStyle}>Usuario</th>
            <th style={{ ...headerCellStyle, textAlign: "center" }}>Líneas</th>
            <th style={{ ...headerCellStyle, textAlign: "center" }}>Cant.</th>
            <th style={headerCellStyle}>Notas</th>
          </tr>
        </thead>
        <tbody>
          {data.map((receipt) => (
            <tr key={receipt.id}>
              <td style={bodyCellStyle}>{new Date(receipt.date).toLocaleString()}</td>
              <td style={bodyCellStyle}>{receipt.user || "—"}</td>
              <td style={{ ...bodyCellStyle, textAlign: "center" }}>{receipt.lines}</td>
              <td style={{ ...bodyCellStyle, textAlign: "center" }}>{receipt.qty}</td>
              <td style={bodyCellStyle}>{receipt.note || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
