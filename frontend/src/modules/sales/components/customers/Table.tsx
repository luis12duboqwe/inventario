import React from "react";

type Row = {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  tier?: string;
  lastSale?: string;
};

type Props = {
  rows: Row[];
  onRowClick?: (row: Row) => void;
};

export default function Table({ rows, onRowClick }: Props) {
  const columns = [
    { key: "name", label: "Cliente" },
    { key: "phone", label: "Teléfono" },
    { key: "email", label: "Email" },
    { key: "tier", label: "Tier" },
    { key: "lastSale", label: "Última compra" },
  ];

  const data = Array.isArray(rows) ? rows : [];

  return (
    <div style={{ overflow: "auto", borderRadius: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.03)" }}>
            {columns.map((column) => (
              <th key={column.key} style={{ textAlign: "left", padding: 10 }}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length ? (
            data.map((row) => (
              <tr
                key={row.id}
                onClick={() => onRowClick?.(row)}
                style={{ cursor: onRowClick ? "pointer" : "default" }}
              >
                {columns.map((column) => (
                  <td key={column.key} style={{ padding: 10 }}>
                    {(row as Record<string, unknown>)[column.key] ?? "—"}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td style={{ padding: 12, color: "#9ca3af" }}>Sin clientes</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
