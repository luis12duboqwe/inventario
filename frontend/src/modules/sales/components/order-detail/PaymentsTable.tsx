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

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function PaymentsTable({ items }: OrderPaymentsTableProps) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div style={{ padding: 12, color: "#9ca3af" }}>Sin pagos</div>;
  }

  return (
    <div style={{ overflow: "auto", borderRadius: 12, border: "1px solid rgba(255, 255, 255, 0.08)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "rgba(255, 255, 255, 0.03)" }}>
            <th style={{ textAlign: "left", padding: 10 }}>Método</th>
            <th style={{ textAlign: "left", padding: 10 }}>Referencia</th>
            <th style={{ textAlign: "right", padding: 10 }}>Monto</th>
            <th style={{ textAlign: "left", padding: 10 }}>Fecha</th>
            <th style={{ textAlign: "left", padding: 10 }}>Notas</th>
          </tr>
        </thead>
        <tbody>
          {data.map((payment) => (
            <tr key={payment.id}>
              <td style={{ padding: 10 }}>{payment.method}</td>
              <td style={{ padding: 10 }}>{payment.reference ?? "—"}</td>
              <td style={{ padding: 10, textAlign: "right" }}>{currency.format(payment.amount)}</td>
              <td style={{ padding: 10 }}>{new Date(payment.date).toLocaleString()}</td>
              <td style={{ padding: 10 }}>{payment.note ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default PaymentsTable;
