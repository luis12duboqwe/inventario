import React, { useCallback, useMemo } from "react";
import { Row } from "../Row";

type Column = { key: string; label: string; align?: "left" | "right" | "center" };
type Row = Record<string, unknown>;

type Props = {
  cols: Column[];
  rows: Row[];
  onRowClick?: (row: Row) => void;
};

export default function Table({ cols, rows, onRowClick }: Props) {
  const data = useMemo(() => (Array.isArray(rows) ? rows : []), [rows]);

  const headerCells = useMemo(
    () => cols.map((column) => <strong key={column.key}>{column.label}</strong>),
    [cols],
  );

  const mappedRows = useMemo(
    () =>
      data.map((row, index) => ({
        key: (row?.id as string | number | undefined) ?? index,
        row,
        cells: cols.map((column) => (
          <span
            key={column.key}
            style={{
              display: "block",
              textAlign: column.align ?? "left",
            }}
          >
            {row[column.key] ?? "—"}
          </span>
        )),
      })),
    [cols, data],
  );

  const handleClick = useCallback(
    (row: Row) => {
      onRowClick?.(row);
    },
    [onRowClick],
  );

  return (
    <div
      style={{
        overflow: "hidden",
        borderRadius: 12,
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <div role="table" style={{ width: "100%", fontSize: 14 }}>
        <div role="row" style={{ background: "rgba(255,255,255,0.03)", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
          <Row cells={headerCells} />
        </div>
        <div>
          {mappedRows.length ? (
            mappedRows.map(({ key, cells, row }) => (
              <div
                key={key}
                role="row"
                onClick={() => handleClick(row)}
                style={{ cursor: onRowClick ? "pointer" : "default", borderBottom: "1px solid rgba(255,255,255,0.04)" }}
              >
                <Row cells={cells} />
              </div>
            ))
          ) : (
            <div style={{ padding: 12, color: "#9ca3af" }}>Sin resultados</div>
          )}
        </div>
      </div>
    </div>
  );
}
