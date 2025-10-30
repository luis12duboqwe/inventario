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
    <div style={{ width: 680, padding: 16, background: "#fff", color: "#111", fontFamily: "system-ui" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 18 }}>{business?.name ?? "SOFTMOBILE"}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontWeight: 700 }}>Cotización</div>
          <div>Número: {doc?.number ?? "—"}</div>
          <div>Fecha: {doc?.date ? new Date(doc.date).toLocaleString() : "—"}</div>
          <div>Cliente: {doc?.customer ?? "—"}</div>
        </div>
      </div>
      <hr />
      <table style={{ width: "100%", fontSize: 14 }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left" }}>Producto</th>
            <th style={{ textAlign: "center" }}>Cant</th>
            <th style={{ textAlign: "right" }}>Precio</th>
            <th style={{ textAlign: "right" }}>Importe</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, index) => (
            <tr key={index}>
              <td>{line.name}</td>
              <td style={{ textAlign: "center" }}>{line.qty}</td>
              <td style={{ textAlign: "right" }}>{line.price}</td>
              <td style={{ textAlign: "right" }}>{line.qty * line.price}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <hr />
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <div>
          Sub-total: <b>{subtotal}</b>
        </div>
      </div>
      {!!doc?.note && (
        <div style={{ marginTop: 8 }}>
          <b>Notas:</b> {doc.note}
        </div>
      )}
    </div>
  );
}
