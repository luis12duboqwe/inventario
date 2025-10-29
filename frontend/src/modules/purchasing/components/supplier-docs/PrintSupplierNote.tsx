import React from "react";

type NoteLine = {
  name: string;
  qty: number;
};

type NoteDoc = {
  number?: string;
  date?: string;
  supplier?: string;
  lines?: NoteLine[];
};

type Business = {
  name?: string;
  address?: string;
  phone?: string;
};

type Props = {
  business?: Business;
  doc?: NoteDoc;
};

export default function PrintSupplierNote({ business, doc }: Props) {
  const lines = Array.isArray(doc?.lines) ? doc?.lines : [];

  return (
    <div style={{ width: 680, padding: 16, background: "#fff", color: "#111", fontFamily: "system-ui" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 18 }}>{business?.name || "SOFTMOBILE"}</div>
          <div>{business?.address || ""}</div>
          <div>{business?.phone || ""}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontWeight: 700 }}>Nota a proveedor</div>
          <div>Número: {doc?.number || "—"}</div>
          <div>Fecha: {doc?.date ? new Date(doc.date).toLocaleString() : "—"}</div>
          <div>Proveedor: {doc?.supplier || "—"}</div>
        </div>
      </div>
      <hr />
      <table style={{ width: "100%", fontSize: 14 }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left" }}>Descripción</th>
            <th style={{ textAlign: "right" }}>Cant.</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, index) => (
            <tr key={`${line.name}-${index}`}>
              <td>{line.name}</td>
              <td style={{ textAlign: "right" }}>{line.qty}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
