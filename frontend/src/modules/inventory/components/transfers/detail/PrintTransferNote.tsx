type TransferDocument = {
  number?: string;
  date?: string;
  from?: string;
  to?: string;
  lines?: Array<{ sku?: string; name: string; qty: number }>;
};

type BusinessInfo = {
  name?: string;
  address?: string;
  phone?: string;
};

type Props = {
  business?: BusinessInfo;
  doc?: TransferDocument;
};

function PrintTransferNote({ business, doc }: Props) {
  const lines = Array.isArray(doc?.lines) ? doc?.lines ?? [] : [];

  return (
    <div className="print-card">
      <header className="print-card__header">
        <div>
          <strong>{business?.name ?? "SOFTMOBILE"}</strong>
          {business?.address ? <div>{business.address}</div> : null}
          {business?.phone ? <div>{business.phone}</div> : null}
        </div>
        <div className="print-card__meta">
          <h2>Nota de transferencia</h2>
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
              <dt>Origen</dt>
              <dd>{doc?.from ?? "—"}</dd>
            </div>
            <div>
              <dt>Destino</dt>
              <dd>{doc?.to ?? "—"}</dd>
            </div>
          </dl>
        </div>
      </header>
      <table className="print-card__table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Producto</th>
            <th className="text-right">Cant.</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, index) => (
            <tr key={line.sku ?? index}>
              <td>{line.sku ?? "—"}</td>
              <td>{line.name}</td>
              <td className="text-right">{line.qty}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default PrintTransferNote;
