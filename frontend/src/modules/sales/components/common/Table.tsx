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
        key: typeof row.id === "string" ? row.id : typeof row.id === "number" ? row.id : index,
        row,
        cells: cols.map((column) => (
          <span
            key={column.key}
            className={`sales-table-cell sales-table-cell--${column.align ?? "left"}`}
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
    <div className="sales-table-container">
      <div role="table" className="sales-table">
        <div role="row" className="sales-table-header">
          <Row cells={headerCells} />
        </div>
        <div>
          {mappedRows.length ? (
            mappedRows.map(({ key, cells, row }) => (
              <div
                key={key}
                role="row"
                tabIndex={onRowClick ? 0 : undefined}
                onClick={() => handleClick(row)}
                onKeyDown={(e) => {
                  if (onRowClick && (e.key === "Enter" || e.key === " ")) {
                    e.preventDefault();
                    handleClick(row);
                  }
                }}
                className={onRowClick ? "sales-table-row-clickable" : "sales-table-row"}
              >
                <Row cells={cells} />
              </div>
            ))
          ) : (
            <div className="sales-table-empty">Sin resultados</div>
          )}
        </div>
      </div>
    </div>
  );
}
