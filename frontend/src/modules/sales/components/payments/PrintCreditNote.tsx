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
    <div className="print-credit-note">
      <div className="print-credit-note-header">
        <div>
          <div className="print-credit-note-business-name">{business?.name ?? "SOFTMOBILE"}</div>
          {business?.address ? (
            <div className="print-credit-note-text-sm">{business.address}</div>
          ) : null}
          {business?.phone ? (
            <div className="print-credit-note-text-sm">Tel. {business.phone}</div>
          ) : null}
          {business?.taxId ? (
            <div className="print-credit-note-text-sm">RFC: {business.taxId}</div>
          ) : null}
        </div>
        <div className="print-credit-note-meta">
          <div className="print-credit-note-title">NOTA DE CRÉDITO</div>
          <div className="print-credit-note-text-sm">Número: {creditNote?.number ?? "—"}</div>
          <div className="print-credit-note-text-sm">
            Fecha: {creditNote?.date ? dateFormatter.format(new Date(creditNote.date)) : "—"}
          </div>
          <div className="print-credit-note-text-sm">Cliente: {creditNote?.customer ?? "—"}</div>
        </div>
      </div>

      <hr className="print-credit-note-divider" />

      <table className="print-credit-note-table">
        <thead>
          <tr>
            <th className="print-credit-note-th">Descripción</th>
            <th className="print-credit-note-th-right">Cant.</th>
            <th className="print-credit-note-th-right">Monto</th>
          </tr>
        </thead>
        <tbody>
          {items.length > 0 ? (
            items.map((item, index) => (
              <tr key={`${item.name}-${index}`}>
                <td className="print-credit-note-td">{item.name}</td>
                <td className="print-credit-note-td-right">{item.qty}</td>
                <td className="print-credit-note-td-right">{currency.format(item.amount)}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={3} className="print-credit-note-empty">
                Sin conceptos cargados
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="print-credit-note-total">
        Total: {currency.format(Math.max(0, creditNote?.total ?? 0))}
      </div>

      <div className="print-credit-note-footer">
        Esta nota de crédito puede aplicarse a compras futuras o solicitarse como reembolso de
        acuerdo con las políticas de la empresa.
      </div>
    </div>
  );
}

export type { BusinessInfo, CreditNoteItem, CreditNotePrintable, PrintCreditNoteProps };
export default PrintCreditNote;
