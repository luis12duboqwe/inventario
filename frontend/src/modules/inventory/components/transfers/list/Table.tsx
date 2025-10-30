export type TransferRow = {
  id: string;
  date: string;
  number?: string;
  from?: string;
  to?: string;
  items: number;
  status: string;
};

type Props = {
  rows?: TransferRow[];
  loading?: boolean;
  onRowClick?: (row: TransferRow) => void;
};

function Table({ rows, loading, onRowClick }: Props) {
  const list = Array.isArray(rows) ? rows : [];

  if (loading) {
    return <div className="table-placeholder">Cargando…</div>;
  }

  if (!list.length) {
    return <div className="table-placeholder muted">Sin transferencias</div>;
  }

  return (
    <div className="table-container">
      <table className="inventory-table">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>#TRF</th>
            <th>Origen</th>
            <th>Destino</th>
            <th className="text-center">Ítems</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {list.map((row) => (
            <tr key={row.id} className={onRowClick ? "clickable" : undefined} onClick={() => onRowClick?.(row)}>
              <td>{new Date(row.date).toLocaleString()}</td>
              <td>{row.number ?? "—"}</td>
              <td>{row.from ?? "—"}</td>
              <td>{row.to ?? "—"}</td>
              <td className="text-center">{row.items}</td>
              <td>{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Table;
