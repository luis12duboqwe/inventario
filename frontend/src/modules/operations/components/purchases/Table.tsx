import type { PurchaseRecord } from "../../../../api";

type PurchasesTableProps = {
  records: PurchaseRecord[];
  loading: boolean;
  currencyFormatter: Intl.NumberFormat;
};

const PurchasesTable = ({ records, loading, currencyFormatter }: PurchasesTableProps) => {
  if (loading) {
    return <p className="muted-text">Cargando compras…</p>;
  }

  if (records.length === 0) {
    return <p className="muted-text">No hay compras registradas con los filtros actuales.</p>;
  }

  return (
    <div className="table-responsive">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Proveedor</th>
            <th>Fecha</th>
            <th>Total</th>
            <th>Impuesto</th>
            <th>Pago</th>
            <th>Estado</th>
            <th>Usuario</th>
            <th>Productos</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.id_compra}>
              <td>#{record.id_compra}</td>
              <td>{record.proveedor_nombre}</td>
              <td>{new Date(record.fecha).toLocaleString("es-HN")}</td>
              <td>{currencyFormatter.format(record.total)}</td>
              <td>{currencyFormatter.format(record.impuesto)}</td>
              <td>{record.forma_pago}</td>
              <td>{record.estado}</td>
              <td>{record.usuario_nombre || "—"}</td>
              <td>
                <ul className="compact-list">
                  {record.items.map((item) => (
                    <li key={item.id_detalle}>
                      {(item.producto_nombre || `Producto #${item.producto_id}`) + " · "}
                      {item.cantidad} × {currencyFormatter.format(item.costo_unitario)}
                    </li>
                  ))}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PurchasesTable;
