import React from "react";

export type POSTaxRow = {
  label: string;
  amount: number;
};

export type POSTaxesPanelProps = {
  rows?: POSTaxRow[];
};

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function TaxesPanel({ rows }: POSTaxesPanelProps) {
  const data = Array.isArray(rows) ? rows : [];

  return (
    <div style={{ padding: 8, borderRadius: 8, border: "1px solid rgba(255, 255, 255, 0.08)", display: "grid", gap: 6 }}>
      <span style={{ fontSize: 12, color: "#94a3b8" }}>Impuestos</span>
      {data.length === 0 ? (
        <span style={{ color: "#9ca3af" }}>—</span>
      ) : (
        <div style={{ display: "grid", gap: 4 }}>
          {data.map((row, index) => (
            <div key={`${row.label}-${index}`} style={{ display: "flex", justifyContent: "space-between" }}>
              <span>{row.label}</span>
              <span>{currency.format(row.amount)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default TaxesPanel;
