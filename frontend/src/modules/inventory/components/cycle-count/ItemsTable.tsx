import type { ChangeEvent } from "react";

type Row = {
  id: string;
  sku?: string;
  name: string;
  expected: number;
  counted: number;
};

type Props = {
  rows?: Row[];
  onChangeCount?: (id: string, value: number) => void;
};

function ItemsTable({ rows, onChangeCount }: Props) {
  const list = Array.isArray(rows) ? rows : [];

  const handleChange = (id: string) => (event: ChangeEvent<HTMLInputElement>) => {
    onChangeCount?.(id, Number(event.target.value || 0));
  };

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
              <td className="text-center">
                <input type="number" min={0} value={row.counted} onChange={handleChange(row.id)} />
              </td>
              <td className="text-center">{row.counted - row.expected}</td>
            </tr>
          ))}
          {list.length === 0 ? (
            <tr>
              <td colSpan={5} className="text-center muted">
                Sin líneas de conteo
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

export type { Row as CycleCountRow };
export default ItemsTable;
