import { useMemo } from "react";

import ScrollableTable from "../../../components/ScrollableTable";
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

  return (
    <ScrollableTable
      items={devices}
      itemKey={(device) => device.id}
      renderHead={() => (
        <>
          <th scope="col">SKU</th>
          <th scope="col">Nombre</th>
          <th scope="col">Modelo</th>
          <th scope="col">Estado</th>
          <th scope="col">Identificadores</th>
          <th scope="col">Cantidad</th>
          <th scope="col">Precio unitario</th>
          <th scope="col">Valor total</th>
        </>
      )}
      renderRow={(device) => (
        <tr className={highlightedDeviceIds?.has(device.id) ? "inventory-row low-stock" : "inventory-row"}>
          <td data-label="SKU">{device.sku}</td>
          <td data-label="Nombre">{device.name}</td>
          <td data-label="Modelo">{device.modelo ?? "—"}</td>
          <td data-label="Estado">
            <span className={`status-chip ${estadoTone(device.estado_comercial)}`}>
              {estadoLabels[device.estado_comercial]}
            </span>
          </td>
          <td data-label="Identificadores">
            <div className="identifier-stack">
              {device.imei ? <span>IMEI: {device.imei}</span> : null}
              {device.serial ? <span>Serie: {device.serial}</span> : null}
              {!device.imei && !device.serial ? <span className="muted-text">—</span> : null}
            </div>
          </td>
          <td data-label="Cantidad">{device.quantity}</td>
          <td data-label="Precio unitario">{currencyFormatter.format(device.unit_price)}</td>
          <td data-label="Valor total">{currencyFormatter.format(device.inventory_value)}</td>
        </tr>
      )}
      emptyMessage={emptyMessage ?? "No hay dispositivos registrados para esta sucursal."}
      title="Inventario corporativo"
      ariaLabel="Tabla de inventario corporativo"
    />
  );
}

export default InventoryTable;
