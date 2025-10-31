import React from "react";

type Invoice = {
  id: string;
  number?: string;
  date?: string;
  amount: number;
  url?: string;
};

type Props = {
  items?: Invoice[];
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

export default function InvoicesTable({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div style={{ padding: 12, color: "#9ca3af" }}>Sin facturas</div>;
  }

  return (
    <div style={wrapperStyle}>
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={headerCellStyle}>Número</th>
            <th style={headerCellStyle}>Fecha</th>
            <th style={{ ...headerCellStyle, textAlign: "right" }}>Monto</th>
            <th style={headerCellStyle}>Archivo</th>
          </tr>
        </thead>
        <tbody>
          {data.map((invoice) => (
            <tr key={invoice.id}>
              <td style={bodyCellStyle}>{invoice.number || "—"}</td>
              <td style={bodyCellStyle}>
                {invoice.date ? new Date(invoice.date).toLocaleDateString() : "—"}
              </td>
              <td style={{ ...bodyCellStyle, textAlign: "right" }}>
                {Intl.NumberFormat().format(invoice.amount)}
              </td>
              <td style={bodyCellStyle}>
                {invoice.url ? (
                  <a href={invoice.url} target="_blank" rel="noreferrer">
                    Ver
                  </a>
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
