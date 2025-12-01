import React from "react";

type CreditNoteItem = {
  name: string;
  qty: number;
  amount: number;
};

type CreditNotePrintable = {
  number?: string;
  date?: string;
  customer?: string;
  items?: CreditNoteItem[];
  total?: number;
};

type BusinessInfo = {
  name?: string;
  address?: string;
  phone?: string;
  taxId?: string;
};

type PrintCreditNoteProps = {
  business?: BusinessInfo;
  creditNote?: CreditNotePrintable;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });
const dateFormatter = new Intl.DateTimeFormat("es-HN", { dateStyle: "medium", timeStyle: "short" });

function PrintCreditNote({ business, creditNote }: PrintCreditNoteProps) {
  const items = Array.isArray(creditNote?.items) ? creditNote?.items ?? [] : [];

  return (
    <div style={{ width: 680, margin: "0 auto", padding: 16, background: "#ffffff", color: "#111827", fontFamily: "Inter, system-ui, sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 20 }}>{business?.name ?? "SOFTMOBILE"}</div>
          {business?.address ? <div style={{ fontSize: 12 }}>{business.address}</div> : null}
          {business?.phone ? <div style={{ fontSize: 12 }}>Tel. {business.phone}</div> : null}
          {business?.taxId ? <div style={{ fontSize: 12 }}>RFC: {business.taxId}</div> : null}
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontWeight: 700, fontSize: 16 }}>NOTA DE CRÉDITO</div>
          <div style={{ fontSize: 12 }}>Número: {creditNote?.number ?? "—"}</div>
          <div style={{ fontSize: 12 }}>Fecha: {creditNote?.date ? dateFormatter.format(new Date(creditNote.date)) : "—"}</div>
          <div style={{ fontSize: 12 }}>Cliente: {creditNote?.customer ?? "—"}</div>
        </div>
      </div>

      <hr style={{ margin: "16px 0", borderColor: "#e2e8f0" }} />

      <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", paddingBottom: 8, borderBottom: "1px solid #e2e8f0" }}>Descripción</th>
            <th style={{ textAlign: "right", paddingBottom: 8, borderBottom: "1px solid #e2e8f0" }}>Cant.</th>
            <th style={{ textAlign: "right", paddingBottom: 8, borderBottom: "1px solid #e2e8f0" }}>Monto</th>
          </tr>
        </thead>
        <tbody>
          {items.length > 0 ? (
            items.map((item, index) => (
              <tr key={`${item.name}-${index}`}>
                <td style={{ padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>{item.name}</td>
                <td style={{ padding: "8px 0", textAlign: "right", borderBottom: "1px solid #f1f5f9" }}>{item.qty}</td>
                <td style={{ padding: "8px 0", textAlign: "right", borderBottom: "1px solid #f1f5f9" }}>{currency.format(item.amount)}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={3} style={{ padding: 12, textAlign: "center", color: "#64748b" }}>
                Sin conceptos cargados
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div style={{ textAlign: "right", fontWeight: 700, fontSize: 15, marginTop: 16 }}>
        Total: {currency.format(Math.max(0, creditNote?.total ?? 0))}
      </div>

      <div style={{ marginTop: 16, fontSize: 11, color: "#475569", lineHeight: 1.4 }}>
        Esta nota de crédito puede aplicarse a compras futuras o solicitarse como reembolso de acuerdo con las políticas de la empresa.
      </div>
    </div>
  );
}

export type { BusinessInfo, CreditNoteItem, CreditNotePrintable, PrintCreditNoteProps };
export default PrintCreditNote;
