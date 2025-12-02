import React from "react";

type PaymentRow = {
  id: string;
  type: "PAYMENT" | "REFUND" | "CREDIT_NOTE";
  orderNumber?: string;
  customer?: string;
  method?: string;
  amount: number;
  date: string;
};

type PaymentsTableProps = {
  rows?: PaymentRow[];
  loading?: boolean;
  onRowClick?: (row: PaymentRow) => void;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });
const dateFormatter = new Intl.DateTimeFormat("es-HN", { dateStyle: "short", timeStyle: "short" });

function PaymentsTable({ rows, loading, onRowClick }: PaymentsTableProps) {
  const hasRows = Array.isArray(rows) && rows.length > 0;

  if (loading) {
    return <div className="payments-table-loading">Cargando…</div>;
  }

  if (!hasRows) {
    return <div className="payments-table-empty">Sin movimientos</div>;
  }

  return (
    <div className="payments-table-container">
      <table className="payments-table">
        <thead>
          <tr className="payments-table-header">
            <th className="payments-table-th">Fecha</th>
            <th className="payments-table-th">Tipo</th>
            <th className="payments-table-th">Pedido</th>
            <th className="payments-table-th">Cliente</th>
            <th className="payments-table-th">Método</th>
            <th className="payments-table-th-right">Monto</th>
          </tr>
        </thead>
        <tbody>
          {rows?.map((row) => (
            <tr
              key={row.id}
              onClick={() => (onRowClick ? onRowClick(row) : undefined)}
              className={onRowClick ? "payments-table-row-clickable" : "payments-table-row"}
            >
              <td className="payments-table-td">{dateFormatter.format(new Date(row.date))}</td>
              <td className="payments-table-td">{row.type}</td>
              <td className="payments-table-td">{row.orderNumber ?? "—"}</td>
              <td className="payments-table-td">{row.customer ?? "—"}</td>
              <td className="payments-table-td">{row.method ?? "—"}</td>
              <td className="payments-table-td-right">{currency.format(row.amount ?? 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export type { PaymentRow, PaymentsTableProps };
export default PaymentsTable;
