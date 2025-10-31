export type TransferItemLine = {
  id: string;
  sku?: string;
  name: string;
  qty: number;
  imeis?: string[];
  picked?: number;
  packed?: number;
  shipped?: number;
  received?: number;
};

type Props = {
  items?: TransferItemLine[];
};

function ItemsTable({ items }: Props) {
  const list = Array.isArray(items) ? items : [];

  if (!list.length) {
    return <div className="table-placeholder muted">Sin ítems</div>;
  }

  return (
    <div className="table-container">
      <table className="inventory-table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Producto</th>
            <th className="text-center">Solicitada</th>
            <th className="text-center">Pick</th>
            <th className="text-center">Pack</th>
            <th className="text-center">Envío</th>
            <th className="text-center">Recibida</th>
            <th>IMEIs</th>
          </tr>
        </thead>
        <tbody>
          {list.map((item) => (
            <tr key={item.id}>
              <td>{item.sku ?? "—"}</td>
              <td>{item.name}</td>
              <td className="text-center">{item.qty}</td>
              <td className="text-center">{item.picked ?? 0}</td>
              <td className="text-center">{item.packed ?? 0}</td>
              <td className="text-center">{item.shipped ?? 0}</td>
              <td className="text-center">{item.received ?? 0}</td>
              <td className="text-truncate">{(item.imeis ?? []).join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ItemsTable;
