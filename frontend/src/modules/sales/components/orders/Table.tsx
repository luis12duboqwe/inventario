import React from "react";

import StatusBadge from "./StatusBadge";

export type OrderRow = {
  id: string;
  number?: string;
  date: string;
  customer: string;
  itemsCount: number;
  total: number;
  status: "DRAFT" | "OPEN" | "PAID" | "CANCELLED" | "REFUNDED";
};

type Props = {
  rows?: OrderRow[];
  loading?: boolean;
  selectedIds?: string[];
  onToggleSelect?: (id: string) => void;
  onToggleSelectAll?: () => void;
  onRowClick?: (row: OrderRow) => void;
};

function Table({
  rows,
  loading,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onRowClick,
}: Props) {
  const data = Array.isArray(rows) ? rows : [];
  const selected = Array.isArray(selectedIds) ? selectedIds : [];
  const allSelected = data.length > 0 && data.every((row) => selected.includes(row.id));

  if (loading) {
    return <div className="orders-table-loading">Cargando…</div>;
  }

  if (!data.length) {
    return <div className="orders-table-empty">Sin resultados</div>;
  }

  return (
    <div className="orders-table-container">
      <table className="orders-table">
        <thead>
          <tr className="orders-table-header-row">
            <th className="orders-table-th--checkbox">
              <input type="checkbox" checked={allSelected} onChange={onToggleSelectAll} />
            </th>
            <th className="orders-table-th">Fecha</th>
            <th className="orders-table-th">#</th>
            <th className="orders-table-th">Cliente</th>
            <th className="orders-table-th orders-table-th--center">Items</th>
            <th className="orders-table-th orders-table-th--right">Total</th>
            <th className="orders-table-th">Estado</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row)}
              className={onRowClick ? "orders-table-row--clickable" : ""}
            >
              <td
                className="orders-table-td orders-table-td--center"
                onClick={(event) => event.stopPropagation()}
              >
                <input
                  type="checkbox"
                  checked={selected.includes(row.id)}
                  onChange={() => onToggleSelect?.(row.id)}
                />
              </td>
              <td className="orders-table-td">{row.date}</td>
              <td className="orders-table-td">{row.number || "-"}</td>
              <td className="orders-table-td">{row.customer}</td>
              <td className="orders-table-td orders-table-td--center">{row.itemsCount}</td>
              <td className="orders-table-td orders-table-td--right">
                {Intl.NumberFormat().format(row.total)}
              </td>
              <td className="orders-table-td">
                <StatusBadge value={row.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Table;
