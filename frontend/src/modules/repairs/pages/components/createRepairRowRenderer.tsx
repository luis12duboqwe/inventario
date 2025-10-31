import type { ReactNode } from "react";

import type { Device, RepairOrder } from "../../../../api";

import {
  repairStatusLabels,
  repairStatusOptions,
} from "./repairOrdersBoardConstants";

type RepairRowRendererDependencies = {
  devicesById: Map<number, Device>;
  getVisual: (order: RepairOrder) => { icon: string; imageUrl?: string };
  handleVisualEdit: (order: RepairOrder) => void;
  handleStatusChange: (order: RepairOrder, status: RepairOrder["status"]) => void;
  handleDownload: (order: RepairOrder) => void;
  handleDelete: (order: RepairOrder) => void;
  handleClose: (order: RepairOrder) => Promise<boolean | void> | void; // [PACK37-frontend]
  onShowBudget?: (order: RepairOrder) => void;
  onShowParts?: (order: RepairOrder) => void;
};

const createRepairRowRenderer = ({
  devicesById,
  getVisual,
  handleVisualEdit,
  handleStatusChange,
  handleDownload,
  handleDelete,
  handleClose,
  onShowBudget,
  onShowParts,
}: RepairRowRendererDependencies) => {
  return (order: RepairOrder): ReactNode => {
    const updatedAt = new Date(order.updated_at).toLocaleString("es-MX");
    const total = Number(order.total_cost ?? 0).toLocaleString("es-MX", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    const visual = getVisual(order);

    return (
      <tr>
        <td data-label="Folio">#{order.id}</td>
        <td data-label="Cliente">{order.customer_name ?? "Mostrador"}</td>
        <td data-label="Técnico">{order.technician_name}</td>
        <td data-label="Diagnóstico">
          <div className="repair-visual">
            {visual.imageUrl ? (
              <img
                loading="lazy"
                decoding="async"
                src={visual.imageUrl}
                alt={`Dispositivo asociado a la reparación #${order.id}`}
                className="repair-visual__image"
              />
            ) : (
              <span className="repair-visual__icon" aria-hidden="true">
                {visual.icon}
              </span>
            )}
            <div className="repair-visual__details">
              <div>{order.damage_type}</div>
              {order.device_description ? (
                <div className="muted-text">{order.device_description}</div>
              ) : null}
              {order.parts.length > 0 ? (
                <ul className="muted-text">
                  {order.parts.map((part) => {
                    const device = part.device_id ? devicesById.get(part.device_id) : undefined;
                    const label = part.part_name
                      ? part.part_name
                      : device
                      ? `${device.sku} · ${device.name}`
                      : part.device_id
                      ? `Dispositivo #${part.device_id}`
                      : "Repuesto externo";
                    return (
                      <li key={`${order.id}-${part.id}`}>
                        {part.quantity} × {label} — {part.source === "EXTERNAL" ? "Compra externa" : "Inventario"} (
                        {part.unit_cost.toLocaleString("es-MX", {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                        )
                      </li>
                    );
                  })}
                </ul>
              ) : null}
            </div>
          </div>
          <button type="button" className="btn btn--ghost" onClick={() => handleVisualEdit(order)}>
            Definir visual
          </button>
        </td>
        <td data-label="Estado">
          <select
            value={order.status}
            onChange={(event) => handleStatusChange(order, event.target.value as RepairOrder["status"])}
          >
            {repairStatusOptions.map((status) => (
              <option key={status} value={status}>
                {repairStatusLabels[status]}
              </option>
            ))}
          </select>
        </td>
        <td data-label="Total">${total}</td>
        <td data-label="Actualizado">{updatedAt}</td>
        <td data-label="Inventario">{order.inventory_adjusted ? "Sí" : "Pendiente"}</td>
        <td data-label="Acciones">
          <div className="actions-row">
            {onShowBudget ? (
              <button type="button" className="btn btn--ghost" onClick={() => onShowBudget(order)}>
                Presupuesto
              </button>
            ) : null}
            {onShowParts ? (
              <button type="button" className="btn btn--ghost" onClick={() => onShowParts(order)}>
                Repuestos
              </button>
            ) : null}
            {order.status !== "ENTREGADO" && order.status !== "CANCELADO" ? (
              <button type="button" className="btn btn--ghost" onClick={() => void handleClose(order)}>
                Cerrar y PDF
              </button>
            ) : null}
            <button type="button" className="btn btn--ghost" onClick={() => handleDownload(order)}>
              PDF
            </button>
            <button type="button" className="btn btn--ghost" onClick={() => handleDelete(order)}>
              Eliminar
            </button>
          </div>
        </td>
      </tr>
    );
  };
};

export type { RepairRowRendererDependencies };
export { createRepairRowRenderer };
