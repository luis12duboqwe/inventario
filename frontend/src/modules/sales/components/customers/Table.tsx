import React, { useCallback, useMemo } from "react";
import { Row } from "../Row";

type CustomerRow = {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  tier?: string;
  lastSale?: string;
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
          <span key={column.key} style={{ display: "block", textAlign: column.key === "tier" ? "center" : "left" }}>
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
    <div style={{ overflow: "hidden", borderRadius: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
      <div role="table" style={{ width: "100%", fontSize: 14 }}>
        <div role="row" style={{ background: "rgba(255,255,255,0.03)", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
          <Row cells={headerCells} />
        </div>
        <div>
          {mappedRows.length ? (
            mappedRows.map(({ id, cells, row }) => (
              <div
                key={id}
                role="row"
                onClick={() => handleRowClick(row)}
                style={{ cursor: onRowClick ? "pointer" : "default", borderBottom: "1px solid rgba(255,255,255,0.04)" }}
              >
                <Row cells={cells} />
              </div>
            ))
          ) : (
            <div style={{ padding: 12, color: "#9ca3af" }}>Sin clientes</div>
          )}
        </div>
      </div>
    </div>
  );
}
