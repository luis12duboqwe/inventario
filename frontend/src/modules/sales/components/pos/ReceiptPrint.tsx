import React from "react";

type ReceiptItem = {
  name: string;
  qty: number;
  price: number;
};

type ReceiptDoc = {
  number?: string;
  date?: string;
  customer?: string;
  items?: ReceiptItem[];
  sub?: number;
  disc?: number;
  tax?: number;
  total?: number;
};

type BusinessInfo = {
  name?: string;
  address?: string;
};

type Props = {
  business?: BusinessInfo;
  doc?: ReceiptDoc;
};

export default function ReceiptPrint({ business, doc }: Props) {
  const items = Array.isArray(doc?.items) ? doc?.items : [];
  return (
    <div style={{ width: 380, padding: 12, background: "#fff", color: "#111", fontFamily: "system-ui" }}>
      <div style={{ textAlign: "center", fontWeight: 700 }}>{business?.name ?? "SOFTMOBILE"}</div>
      <div style={{ textAlign: "center", fontSize: 12 }}>{business?.address ?? ""}</div>
      <hr />
      <div>Número: {doc?.number ?? "—"}</div>
      <div>Fecha: {doc?.date ? new Date(doc.date).toLocaleString() : "—"}</div>
      <div>Cliente: {doc?.customer ?? "Mostrador"}</div>
      <hr />
      <table style={{ width: "100%", fontSize: 12 }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left" }}>Producto</th>
            <th style={{ textAlign: "center" }}>Cant</th>
            <th style={{ textAlign: "right" }}>Precio</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={index}>
              <td>{item.name}</td>
              <td style={{ textAlign: "center" }}>{item.qty}</td>
              <td style={{ textAlign: "right" }}>{item.price}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <hr />
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span>Sub</span>
        <span>{doc?.sub ?? 0}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span>Desc</span>
        <span>-{doc?.disc ?? 0}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span>Imp</span>
        <span>{doc?.tax ?? 0}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
        <span>Total</span>
        <span>{doc?.total ?? 0}</span>
      </div>
    </div>
  );
}
