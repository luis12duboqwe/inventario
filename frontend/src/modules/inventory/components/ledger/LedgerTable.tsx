type LedgerRow = {
  id: string;
  date: string;
  type: "SALE" | "PURCHASE" | "ADJUSTMENT" | "TRANSFER_OUT" | "TRANSFER_IN" | "COUNT" | string;
  ref?: string;
  qty: number;
  balance: number;
  note?: string;
};

type Props = {
  rows?: LedgerRow[];
};

function LedgerTable({ rows }: Props) {
  const list = Array.isArray(rows) ? rows : [];

  if (!list.length) {
    return <div className="table-placeholder muted">Sin movimientos</div>;
  }

  return (
    <div className="table-container">
      <table className="inventory-table">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Tipo</th>
            <th>Referencia</th>
            <th className="text-right">Cantidad</th>
            <th className="text-right">Balance</th>
            <th>Notas</th>
          </tr>
        </thead>
        <tbody>
          {list.map((row) => (
            <tr key={row.id}>
              <td>{new Date(row.date).toLocaleString()}</td>
              <td>{row.type}</td>
              <td>{row.ref ?? "—"}</td>
              <td className="text-right">{row.qty}</td>
              <td className="text-right">{row.balance}</td>
              <td>{row.note ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export type { LedgerRow };
export default LedgerTable;
