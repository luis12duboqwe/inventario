import React from "react";

export type POSTaxRow = {
  label: string;
  amount: number;
};

export type POSTaxesPanelProps = {
  rows?: POSTaxRow[];
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function TaxesPanel({ rows }: POSTaxesPanelProps) {
  const data = Array.isArray(rows) ? rows : [];

  return (
    <div className="pos-taxes-panel">
      <span className="pos-taxes-title">Impuestos</span>
      {data.length === 0 ? (
        <span className="pos-taxes-empty">—</span>
      ) : (
        <div className="pos-taxes-list">
          {data.map((row, index) => (
            <div key={`${row.label}-${index}`} className="pos-taxes-row">
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
