import React, { useCallback, useMemo } from "react";
import { Row } from "../Row";

type Column = { key: string; label: string; align?: "left" | "right" | "center" };
type DataRowValue = React.ReactNode | string | number | boolean | null | undefined;
type DataRow = Record<string, DataRowValue>;

type Props = {
  cols: Column[];
  rows: DataRow[];
  onRowClick?: (row: DataRow) => void;
};

function renderCellValue(value: DataRowValue): React.ReactNode {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "boolean") {
    return value ? "Sí" : "No";
  }
  if (React.isValidElement(value)) {
    return value;
  }
  return String(value);
}

export default function Table({ cols, rows, onRowClick }: Props) {
  const data = useMemo(() => (Array.isArray(rows) ? rows : []), [rows]);

  const headerCells = useMemo(
    () => cols.map((column) => <strong key={column.key}>{column.label}</strong>),
    [cols],
  );

  const mappedRows = useMemo(
    () =>
      data.map((row, index) => ({
        key:
          typeof row.id === "string"
            ? row.id
            : typeof row.id === "number"
              ? row.id
              : index,
        row,
        cells: cols.map((column) => (
          <span
            key={column.key}
            style={{
              display: "block",
              textAlign: column.align ?? "left",
            }}
          >
            {renderCellValue(row[column.key])}
          </span>
        )),
      })),
    [cols, data],
  );

  const handleClick = useCallback(
    (row: DataRow) => {
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
