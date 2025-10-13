import { useMemo } from "react";

import { Device } from "../api";

type Props = {
  devices: Device[];
};

function InventoryTable({ devices }: Props) {
  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }),
    []
  );

  if (devices.length === 0) {
    return <p>No hay dispositivos registrados para esta sucursal.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>SKU</th>
          <th>Nombre</th>
          <th>Cantidad</th>
          <th>Precio unitario</th>
          <th>Valor total</th>
        </tr>
      </thead>
      <tbody>
        {devices.map((device) => (
          <tr key={device.id}>
            <td>{device.sku}</td>
            <td>{device.name}</td>
            <td>{device.quantity}</td>
            <td>{currencyFormatter.format(device.unit_price)}</td>
            <td>{currencyFormatter.format(device.inventory_value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default InventoryTable;
