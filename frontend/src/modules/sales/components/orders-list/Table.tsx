import React from "react";
import { Skeleton } from "@components/ui/Skeleton";

import ChannelBadge from "./ChannelBadge";
import PaymentStatusBadge from "./PaymentStatusBadge";
import StatusBadge from "./StatusBadge";

export type OrderRow = {
  id: string;
  date: string;
  number?: string;
  customer?: string;
  itemsCount: number;
  total: number;
  paid: number;
  status: "DRAFT" | "OPEN" | "COMPLETED" | "CANCELLED";
  paymentStatus: "UNPAID" | "PARTIAL" | "PAID" | "REFUNDED";
  channel: "POS" | "WEB" | "MANUAL";
};

export type OrdersTableProps = {
  rows?: OrderRow[];
  loading?: boolean;
  selectedIds?: string[];
  onToggleSelect?: (id: string) => void;
  onToggleSelectAll?: () => void;
  onRowClick?: (row: OrderRow) => void;
};

const numberFormatter = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function Table({
  rows,
  loading,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onRowClick,
}: OrdersTableProps) {
  const data = Array.isArray(rows) ? rows : [];
  const selected = Array.isArray(selectedIds) ? selectedIds : [];
  const allSelected = data.length > 0 && data.every((row) => selected.includes(row.id));

  if (loading) {
    return <Skeleton lines={5} />;
  }

  if (data.length === 0) {
    return <div className="orders-list-table__empty">Sin resultados</div>;
  }

  return (
    <div className="orders-list-table-container">
      <table className="orders-list-table">
        <thead>
          <tr className="orders-list-table__header-row">
            <th className="orders-list-table__th--checkbox">
              <input type="checkbox" checked={allSelected} onChange={() => onToggleSelectAll?.()} />
            </th>
            <th className="orders-list-table__th">Fecha</th>
            <th className="orders-list-table__th">#</th>
            <th className="orders-list-table__th">Cliente</th>
            <th className="orders-list-table__th--center">Items</th>
            <th className="orders-list-table__th--right">Total</th>
            <th className="orders-list-table__th--right">Pagado</th>
            <th className="orders-list-table__th">Pago</th>
            <th className="orders-list-table__th">Estado</th>
            <th className="orders-list-table__th">Canal</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row)}
              className={onRowClick ? "orders-list-table__row--clickable" : ""}
            >
              <td
                className="orders-list-table__td--center"
                onClick={(event) => event.stopPropagation()}
              >
                <input
                  type="checkbox"
                  checked={selected.includes(row.id)}
                  onChange={(event) => {
                    event.stopPropagation();
                    onToggleSelect?.(row.id);
                  }}
                />
              </td>
              <td className="orders-list-table__td">{row.date}</td>
              <td className="orders-list-table__td">{row.number ?? "-"}</td>
              <td className="orders-list-table__td">{row.customer ?? "—"}</td>
              <td className="orders-list-table__td--center">{row.itemsCount}</td>
              <td className="orders-list-table__td--right">{numberFormatter.format(row.total)}</td>
              <td className="orders-list-table__td--right">{numberFormatter.format(row.paid)}</td>
              <td className="orders-list-table__td">
                <PaymentStatusBadge value={row.paymentStatus} />
              </td>
              <td className="orders-list-table__td">
                <StatusBadge value={row.status} />
              </td>
              <td className="orders-list-table__td">
                <ChannelBadge value={row.channel} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Table;
