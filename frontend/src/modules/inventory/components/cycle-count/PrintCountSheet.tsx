type CountItem = {
  sku?: string;
  name: string;
  expected?: number;
};

type CountDocument = {
  number?: string;
  date?: string;
  warehouse?: string;
  items?: CountItem[];
};

type BusinessInfo = {
  name?: string;
};

type Props = {
  business?: BusinessInfo;
  doc?: CountDocument;
};

function PrintCountSheet({ business, doc }: Props) {
  const items = Array.isArray(doc?.items) ? doc?.items ?? [] : [];

  return (
    <div className="print-card">
      <header className="print-card__header">
        <div>
          <strong>{business?.name ?? "SOFTMOBILE"}</strong>
        </div>
        <div className="print-card__meta">
          <h2>Hoja de conteo</h2>
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
          </dl>
        </div>
      </header>
      <table className="print-card__table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Producto</th>
            <th className="text-center">Esperado</th>
            <th className="text-center">Contado</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr key={item.sku ?? index}>
              <td>{item.sku ?? "—"}</td>
              <td>{item.name}</td>
              <td className="text-center">{item.expected ?? ""}</td>
              <td className="text-center"></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default PrintCountSheet;
