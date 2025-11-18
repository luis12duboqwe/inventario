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
    return <div style={{ padding: 12 }}>Cargando…</div>;
  }

  if (!hasRows) {
    return <div style={{ padding: 12, color: "#9ca3af" }}>Sin movimientos</div>;
  }

  return (
    <div style={{ overflow: "auto", borderRadius: 12, border: "1px solid rgba(148, 163, 184, 0.16)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "rgba(15, 23, 42, 0.6)" }}>
            <th style={{ padding: 10, textAlign: "left" }}>Fecha</th>
            <th style={{ padding: 10, textAlign: "left" }}>Tipo</th>
            <th style={{ padding: 10, textAlign: "left" }}>Pedido</th>
            <th style={{ padding: 10, textAlign: "left" }}>Cliente</th>
            <th style={{ padding: 10, textAlign: "left" }}>Método</th>
            <th style={{ padding: 10, textAlign: "right" }}>Monto</th>
          </tr>
        </thead>
        <tbody>
          {rows?.map((row) => (
            <tr
              key={row.id}
              onClick={() => (onRowClick ? onRowClick(row) : undefined)}
              style={{ cursor: onRowClick ? "pointer" : "default", borderTop: "1px solid rgba(148, 163, 184, 0.08)" }}
            >
              <td style={{ padding: 10 }}>{dateFormatter.format(new Date(row.date))}</td>
              <td style={{ padding: 10 }}>{row.type}</td>
              <td style={{ padding: 10 }}>{row.orderNumber ?? "—"}</td>
              <td style={{ padding: 10 }}>{row.customer ?? "—"}</td>
              <td style={{ padding: 10 }}>{row.method ?? "—"}</td>
              <td style={{ padding: 10, textAlign: "right" }}>{currency.format(row.amount ?? 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export type { PaymentRow, PaymentsTableProps };
export default PaymentsTable;
