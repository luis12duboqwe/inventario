import React from "react";

export type OrderPayment = {
  id: string;
  method: "CASH" | "CARD" | "MIXED" | string;
  reference?: string;
  amount: number;
  date: string;
  note?: string;
};

export type OrderPaymentsTableProps = {
  items?: OrderPayment[];
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function PaymentsTable({ items }: OrderPaymentsTableProps) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div className="order-payments-empty">Sin pagos</div>;
  }

  return (
    <div className="order-payments-container">
      <table className="order-payments-table">
        <thead>
          <tr className="order-payments-header-row">
            <th className="order-payments-th-left">Método</th>
            <th className="order-payments-th-left">Referencia</th>
            <th className="order-payments-th-right">Monto</th>
            <th className="order-payments-th-left">Fecha</th>
            <th className="order-payments-th-left">Notas</th>
          </tr>
        </thead>
        <tbody>
          {data.map((payment) => (
            <tr key={payment.id}>
              <td className="order-payments-td">{payment.method}</td>
              <td className="order-payments-td">{payment.reference ?? "—"}</td>
              <td className="order-payments-td-right">{currency.format(payment.amount)}</td>
              <td className="order-payments-td">{new Date(payment.date).toLocaleString()}</td>
              <td className="order-payments-td">{payment.note ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default PaymentsTable;
