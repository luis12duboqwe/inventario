type DiscrepancyRow = {
  id: string;
  sku?: string;
  name: string;
  expected: number;
  counted: number;
  delta: number;
};

type Props = {
  rows?: DiscrepancyRow[];
};

function DiscrepanciesTable({ rows }: Props) {
  const list = Array.isArray(rows) ? rows : [];

  if (!list.length) {
    return <div className="table-placeholder muted">Sin diferencias</div>;
  }

  return (
    <div className="table-container">
      <table className="inventory-table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Producto</th>
            <th className="text-center">Esperado</th>
            <th className="text-center">Contado</th>
            <th className="text-center">Δ</th>
          </tr>
        </thead>
        <tbody>
          {list.map((row) => (
            <tr key={row.id}>
              <td>{row.sku ?? "—"}</td>
              <td>{row.name}</td>
              <td className="text-center">{row.expected}</td>
              <td className="text-center">{row.counted}</td>
              <td className={`text-center ${row.delta < 0 ? "text-danger" : row.delta > 0 ? "text-success" : ""}`}>
                {row.delta}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export type { DiscrepancyRow };
export default DiscrepanciesTable;
