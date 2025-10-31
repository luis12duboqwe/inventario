import type { MouseEventHandler } from "react";

export type AdjustmentRow = {
  id: string;
  date: string;
  number?: string;
  warehouse?: string;
  items: number;
  delta: number;
  reason: string;
  user?: string;
};

type Props = {
  rows?: AdjustmentRow[];
  loading?: boolean;
  onRowClick?: (row: AdjustmentRow) => void;
};

function Table({ rows, loading, onRowClick }: Props) {
  const data = Array.isArray(rows) ? rows : [];

  if (loading) {
    return <div className="table-placeholder">Cargando…</div>;
  }

  if (!data.length) {
    return <div className="table-placeholder muted">Sin ajustes</div>;
  }

  const handleClick = (row: AdjustmentRow): MouseEventHandler<HTMLTableRowElement> => () => {
    onRowClick?.(row);
  };

  return (
    <div className="table-container">
      <table className="inventory-table">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>#AJ</th>
            <th>Almacén</th>
            <th className="text-center">Ítems</th>
            <th className="text-right">Δ Cant.</th>
            <th>Motivo</th>
            <th>Usuario</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.id} onClick={handleClick(row)} className={onRowClick ? "clickable" : undefined}>
              <td>{new Date(row.date).toLocaleString()}</td>
              <td>{row.number ?? "—"}</td>
              <td>{row.warehouse ?? "—"}</td>
              <td className="text-center">{row.items}</td>
              <td className="text-right">{Intl.NumberFormat().format(row.delta)}</td>
              <td>{row.reason}</td>
              <td>{row.user ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Table;
