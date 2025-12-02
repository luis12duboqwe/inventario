import React, { useCallback, useMemo } from "react";
import { Row } from "../Row";

export type CustomerRow = {
  id: string;
  name: string;
  phone?: string | undefined;
  email?: string | undefined;
  tier?: string | undefined;
  lastSale?: string | undefined;
};

type Props = {
  rows: CustomerRow[];
  onRowClick?: (row: CustomerRow) => void;
};

const renderCellValue = (value: string | undefined): React.ReactNode => {
  if (!value) {
    return "—";
  }
  return value;
};

export default function Table({ rows, onRowClick }: Props) {
  const columns = useMemo(
    () => [
      { key: "name" as const, label: "Cliente" },
      { key: "phone" as const, label: "Teléfono" },
      { key: "email" as const, label: "Email" },
      { key: "tier" as const, label: "Tier" },
      { key: "lastSale" as const, label: "Última compra" },
    ],
    [],
  );

  const data = useMemo(() => (Array.isArray(rows) ? rows : []), [rows]);

  const headerCells = useMemo(
    () => columns.map((column) => <strong key={column.key}>{column.label}</strong>),
    [columns],
  );

  const mappedRows = useMemo(
    () =>
      data.map((row) => ({
        row,
        id: row.id,
        cells: columns.map((column) => (
          <span
            key={column.key}
            className={`customer-table-cell ${
              column.key === "tier" ? "customer-table-cell-center" : "customer-table-cell-left"
            }`}
          >
            {renderCellValue(row[column.key] as string | undefined)}
          </span>
        )),
      })),
    [columns, data],
  );

  const handleRowClick = useCallback(
    (row: CustomerRow) => {
      onRowClick?.(row);
    },
    [onRowClick],
  );

  return (
    <div className="customer-table-container">
      <div role="table" className="customer-table">
        <div role="row" className="customer-table-header">
          <Row cells={headerCells} />
        </div>
        <div>
          {mappedRows.length ? (
            mappedRows.map(({ id, cells, row }) => (
              <div
                key={id}
                role="row"
                tabIndex={onRowClick ? 0 : undefined}
                onClick={() => handleRowClick(row)}
                onKeyDown={(e) => {
                  if (onRowClick && (e.key === "Enter" || e.key === " ")) {
                    e.preventDefault();
                    handleRowClick(row);
                  }
                }}
                className={`customer-table-row ${onRowClick ? "customer-table-row-clickable" : ""}`}
              >
                <Row cells={cells} />
              </div>
            ))
          ) : (
            <div className="customer-table-empty">Sin clientes</div>
          )}
        </div>
      </div>
    </div>
  );
}
