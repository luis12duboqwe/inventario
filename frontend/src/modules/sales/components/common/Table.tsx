import React from "react";

type Column = { key: string; label: string; align?: "left" | "right" | "center" };
type Row = Record<string, unknown>;

type Props = {
  cols: Column[];
  rows: Row[];
  onRowClick?: (row: Row) => void;
};

export default function Table({ cols, rows, onRowClick }: Props) {
  const data = Array.isArray(rows) ? rows : [];
  return (
    <div
      style={{
        overflow: "auto",
        borderRadius: 12,
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.03)" }}>
            {cols.map((column) => (
              <th
                key={column.key}
                style={{ textAlign: column.align ?? "left", padding: 10 }}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length ? (
            data.map((row, index) => (
              <tr
                key={index}
                onClick={() => onRowClick?.(row)}
                style={{ cursor: onRowClick ? "pointer" : "default" }}
              >
                {cols.map((column) => (
                  <td
                    key={column.key}
                    style={{ textAlign: column.align ?? "left", padding: 10 }}
                  >
                    {row[column.key] ?? "—"}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td style={{ padding: 12, color: "#9ca3af" }}>Sin resultados</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
