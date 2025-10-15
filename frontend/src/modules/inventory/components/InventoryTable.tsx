import { useMemo } from "react";

import { Device } from "../../../api";

type Props = {
  devices: Device[];
  highlightedDeviceIds?: Set<number>;
  emptyMessage?: string;
};

const estadoLabels: Record<Device["estado_comercial"] | undefined, string> = {
  nuevo: "Nuevo",
  A: "Grado A",
  B: "Grado B",
  C: "Grado C",
  undefined: "No definido",
};

const estadoTone = (estado: Device["estado_comercial"] | undefined): "success" | "info" | "warning" | "danger" => {
  switch (estado) {
    case "A":
      return "info";
    case "B":
      return "warning";
    case "C":
      return "danger";
    default:
      return "success";
  }
};

function InventoryTable({ devices, highlightedDeviceIds, emptyMessage }: Props) {
  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }),
    []
  );

  if (devices.length === 0) {
    return <p>{emptyMessage ?? "No hay dispositivos registrados para esta sucursal."}</p>;
  }

  return (
    <table className="inventory-table">
      <thead>
        <tr>
          <th>SKU</th>
          <th>Nombre</th>
          <th>Modelo</th>
          <th>Estado</th>
          <th>Identificadores</th>
          <th>Cantidad</th>
          <th>Precio unitario</th>
          <th>Valor total</th>
        </tr>
      </thead>
      <tbody>
        {devices.map((device) => (
          <tr
            key={device.id}
            className={highlightedDeviceIds?.has(device.id) ? "inventory-row low-stock" : "inventory-row"}
          >
            <td>{device.sku}</td>
            <td>{device.name}</td>
            <td>{device.modelo ?? "—"}</td>
            <td>
              <span className={`status-chip ${estadoTone(device.estado_comercial)}`}>
                {estadoLabels[device.estado_comercial]}
              </span>
            </td>
            <td>
              <div className="identifier-stack">
                {device.imei ? <span>IMEI: {device.imei}</span> : null}
                {device.serial ? <span>Serie: {device.serial}</span> : null}
                {!device.imei && !device.serial ? <span className="muted-text">—</span> : null}
              </div>
            </td>
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
