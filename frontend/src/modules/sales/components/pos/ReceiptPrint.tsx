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
    <div className="pos-receipt-print">
      <div className="pos-receipt-header">{business?.name ?? "SOFTMOBILE"}</div>
      <div className="pos-receipt-address">{business?.address ?? ""}</div>
      <hr className="pos-receipt-divider" />
      <div className="pos-receipt-info">Número: {doc?.number ?? "—"}</div>
      <div className="pos-receipt-info">
        Fecha: {doc?.date ? new Date(doc.date).toLocaleString() : "—"}
      </div>
      <div className="pos-receipt-info">Cliente: {doc?.customer ?? "Mostrador"}</div>
      <hr className="pos-receipt-divider" />
      <table className="pos-receipt-table">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Cant</th>
            <th>Precio</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={index}>
              <td>{item.name}</td>
              <td>{item.qty}</td>
              <td>{item.price}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <hr className="pos-receipt-divider" />
      <div className="pos-receipt-summary-row">
        <span>Sub</span>
        <span>{doc?.sub ?? 0}</span>
      </div>
      <div className="pos-receipt-summary-row">
        <span>Desc</span>
        <span>-{doc?.disc ?? 0}</span>
      </div>
      <div className="pos-receipt-summary-row">
        <span>Imp</span>
        <span>{doc?.tax ?? 0}</span>
      </div>
      <div className="pos-receipt-total-row">
        <span>Total</span>
        <span>{doc?.total ?? 0}</span>
      </div>
    </div>
  );
}
