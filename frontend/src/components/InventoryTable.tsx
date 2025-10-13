import { Device } from "../api";

type Props = {
  devices: Device[];
};

function InventoryTable({ devices }: Props) {
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
        </tr>
      </thead>
      <tbody>
        {devices.map((device) => (
          <tr key={device.id}>
            <td>{device.sku}</td>
            <td>{device.name}</td>
            <td>{device.quantity}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default InventoryTable;
