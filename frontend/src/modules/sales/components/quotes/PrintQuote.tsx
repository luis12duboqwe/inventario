import React from "react";

type QuoteLine = {
  name: string;
  qty: number;
  price: number;
};

type QuoteDoc = {
  number?: string;
  date?: string;
  customer?: string;
  note?: string;
  lines?: QuoteLine[];
};

type BusinessInfo = {
  name?: string;
};

type Props = {
  business?: BusinessInfo;
  doc?: QuoteDoc;
};

export default function PrintQuote({ business, doc }: Props) {
  const lines = Array.isArray(doc?.lines) ? doc?.lines : [];
  const subtotal = lines.reduce((acc, line) => acc + line.qty * line.price, 0);

  return (
    <div className="quotes-print-container">
      <div className="quotes-print-header">
        <div>
          <div className="quotes-print-business-name">{business?.name ?? "SOFTMOBILE"}</div>
        </div>
        <div className="quotes-print-info">
          <div className="quotes-print-title">Cotización</div>
          <div>Número: {doc?.number ?? "—"}</div>
          <div>Fecha: {doc?.date ? new Date(doc.date).toLocaleString() : "—"}</div>
          <div>Cliente: {doc?.customer ?? "—"}</div>
        </div>
      </div>
      <hr />
      <table className="quotes-print-table">
        <thead>
          <tr>
            <th className="quotes-print-th">Producto</th>
            <th className="quotes-print-th quotes-print-th--center">Cant</th>
            <th className="quotes-print-th quotes-print-th--right">Precio</th>
            <th className="quotes-print-th quotes-print-th--right">Importe</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, index) => (
            <tr key={index}>
              <td>{line.name}</td>
              <td className="quotes-print-td--center">{line.qty}</td>
              <td className="quotes-print-td--right">{line.price}</td>
              <td className="quotes-print-td--right">{line.qty * line.price}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <hr />
      <div className="quotes-print-footer">
        <div>
          Sub-total: <b>{subtotal}</b>
        </div>
      </div>
      {!!doc?.note && (
        <div className="quotes-print-notes">
          <b>Notas:</b> {doc.note}
        </div>
      )}
    </div>
  );
}
