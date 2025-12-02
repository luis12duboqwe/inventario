import React from "react";

type ReturnLine = {
  name: string;
  qty: number;
  price: number;
  imei?: string;
};

type ReturnDoc = {
  number?: string;
  date?: string;
  reason?: string;
  lines?: ReturnLine[];
};

type BusinessInfo = {
  name?: string;
};

type Props = {
  business?: BusinessInfo;
  doc?: ReturnDoc;
};

export default function PrintReturnNote({ business, doc }: Props) {
  const lines = Array.isArray(doc?.lines) ? doc?.lines : [];
  const total = lines.reduce((acc, line) => acc + line.qty * line.price, 0);

  return (
    <div className="print-return-note">
      <div className="print-return-note-header">
        <div>
          <div className="print-return-note-business-name">{business?.name ?? "SOFTMOBILE"}</div>
        </div>
        <div className="print-return-note-meta">
          <div className="print-return-note-title">Nota de devolución</div>
          <div>Número: {doc?.number ?? "—"}</div>
          <div>Fecha: {doc?.date ? new Date(doc.date).toLocaleString() : "—"}</div>
          <div>Motivo: {doc?.reason ?? "—"}</div>
        </div>
      </div>
      <hr />
      <table className="print-return-note-table">
        <thead>
          <tr>
            <th>Producto</th>
            <th className="center">Cant</th>
            <th>IMEI</th>
            <th className="right">Importe</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, index) => (
            <tr key={index}>
              <td>{line.name}</td>
              <td className="center">{line.qty}</td>
              <td>{line.imei ?? "—"}</td>
              <td className="right">{line.qty * line.price}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <hr />
      <div className="print-return-note-total">
        <div>
          Total crédito: <b>{total}</b>
        </div>
      </div>
    </div>
  );
}
