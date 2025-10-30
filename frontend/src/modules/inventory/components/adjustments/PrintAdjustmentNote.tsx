import type { ReactNode } from "react";

type AdjustmentLine = {
  sku?: string;
  name?: string;
  qty: number;
};

type AdjustmentDocument = {
  number?: string;
  date?: string;
  warehouse?: string;
  reason?: string;
  lines?: AdjustmentLine[];
};

type BusinessInfo = {
  name?: string;
  address?: string;
  phone?: string;
  extra?: ReactNode;
};

type Props = {
  business?: BusinessInfo;
  doc?: AdjustmentDocument;
};

function PrintAdjustmentNote({ business, doc }: Props) {
  const lines = Array.isArray(doc?.lines) ? doc?.lines ?? [] : [];

  return (
    <div className="print-card">
      <header className="print-card__header">
        <div>
          <strong>{business?.name ?? "SOFTMOBILE"}</strong>
          {business?.address ? <div>{business.address}</div> : null}
          {business?.phone ? <div>{business.phone}</div> : null}
          {business?.extra}
        </div>
        <div className="print-card__meta">
          <h2>Ajuste de inventario</h2>
          <dl>
            <div>
              <dt>Número</dt>
              <dd>{doc?.number ?? "—"}</dd>
            </div>
            <div>
              <dt>Fecha</dt>
              <dd>{doc?.date ? new Date(doc.date).toLocaleString() : "—"}</dd>
            </div>
            <div>
              <dt>Almacén</dt>
              <dd>{doc?.warehouse ?? "—"}</dd>
            </div>
            <div>
              <dt>Motivo</dt>
              <dd>{doc?.reason ?? "—"}</dd>
            </div>
          </dl>
        </div>
      </header>
      <table className="print-card__table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Producto</th>
            <th className="text-right">Δ Cant.</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, index) => (
            <tr key={line.sku ?? index}>
              <td>{line.sku ?? "—"}</td>
              <td>{line.name ?? "—"}</td>
              <td className="text-right">{line.qty}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default PrintAdjustmentNote;
